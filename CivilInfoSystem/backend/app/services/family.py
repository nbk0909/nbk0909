"""خدمة العلاقات الأُسرية وشجرة العائلة وكشف التعارضات المنطقية."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict

from fastapi import Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    INVERSE_RELATION,
    AuditAction,
    FamilyRelation,
    Gender,
    Person,
    RelationType,
    User,
)
from app.services import audit

logger = logging.getLogger(__name__)

# الحد الأدنى المعقول لفارق العمر بين الوالد وولده
MIN_PARENT_AGE_YEARS = 14

PARENT_RELATIONS = (RelationType.FATHER, RelationType.MOTHER)
CHILD_RELATIONS = (RelationType.SON, RelationType.DAUGHTER)
SPOUSE_RELATIONS = (RelationType.HUSBAND, RelationType.WIFE)
SIBLING_RELATIONS = (RelationType.BROTHER, RelationType.SISTER)


class FamilyError(Exception):
    """خطأ في عملية على العلاقات الأُسرية."""

    def __init__(self, message: str, *, code: str = "family_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


# ---------------------------------------------------------------------------
# قراءة العلاقات
# ---------------------------------------------------------------------------

def get_relations(
    db: Session,
    person_id: uuid.UUID,
    *,
    types: tuple[RelationType, ...] | None = None,
    active_only: bool = True,
) -> list[FamilyRelation]:
    """يجلب علاقات شخص، اختيارياً من أنواع محدّدة."""
    stmt = (
        select(FamilyRelation)
        .options(selectinload(FamilyRelation.related_person))
        .where(
            FamilyRelation.person_id == person_id,
            FamilyRelation.deleted_at.is_(None),
        )
    )

    if types:
        stmt = stmt.where(FamilyRelation.relation_type.in_(types))
    if active_only:
        stmt = stmt.where(FamilyRelation.is_active.is_(True))

    return list(db.scalars(stmt).all())


def _related_persons(
    db: Session, person_id: uuid.UUID, types: tuple[RelationType, ...]
) -> list[Person]:
    """يُرجع أشخاص العلاقات من الأنواع المطلوبة."""
    relations = get_relations(db, person_id, types=types)
    return [r.related_person for r in relations if r.related_person.deleted_at is None]


# ---------------------------------------------------------------------------
# إنشاء العلاقات
# ---------------------------------------------------------------------------

def add_relation(
    db: Session,
    *,
    person: Person,
    related_person: Person,
    relation_type: RelationType,
    start_date=None,
    user: User,
    request: Request | None = None,
) -> FamilyRelation:
    """يضيف علاقة أُسرية مع نظيرتها العكسية.

    تُخزَّن العلاقة باتجاهين حتى يكون استعلام أقارب أي شخص بحثاً في عمود
    واحد مفهرس. ويُتحقق من التعارضات المنطقية قبل الحفظ لا بعده.
    """
    if person.id == related_person.id:
        raise FamilyError("لا يمكن ربط الشخص بنفسه", code="self_relation")

    problems = validate_new_relation(db, person, related_person, relation_type)
    if problems:
        raise FamilyError(" • ".join(problems), code="inconsistent_relation")

    existing = db.scalar(
        select(FamilyRelation).where(
            FamilyRelation.person_id == person.id,
            FamilyRelation.related_person_id == related_person.id,
            FamilyRelation.relation_type == relation_type,
            FamilyRelation.deleted_at.is_(None),
        )
    )
    if existing is not None:
        raise FamilyError("العلاقة مسجَّلة مسبقاً", code="duplicate_relation")

    relation = FamilyRelation(
        person_id=person.id,
        related_person_id=related_person.id,
        relation_type=relation_type,
        start_date=start_date,
        is_active=True,
        created_by=user.id,
    )
    db.add(relation)

    # العلاقة العكسية: «س أبٌ لـ ص» يقابلها «ص ابنٌ لـ س»
    inverse = INVERSE_RELATION.get((relation_type, person.gender))
    if inverse is not None:
        already = db.scalar(
            select(FamilyRelation).where(
                FamilyRelation.person_id == related_person.id,
                FamilyRelation.related_person_id == person.id,
                FamilyRelation.relation_type == inverse,
                FamilyRelation.deleted_at.is_(None),
            )
        )
        if already is None:
            db.add(
                FamilyRelation(
                    person_id=related_person.id,
                    related_person_id=person.id,
                    relation_type=inverse,
                    start_date=start_date,
                    is_active=True,
                    created_by=user.id,
                )
            )

    audit.record(
        db,
        action=AuditAction.CREATE,
        resource_type="family_relations",
        resource_id=person.id,
        user=user,
        new_values={
            "relation_type": relation_type.value,
            "related_person": related_person.national_id,
        },
        request=request,
    )

    db.commit()
    db.refresh(relation)
    return relation


def remove_relation(
    db: Session,
    *,
    relation: FamilyRelation,
    user: User,
    request: Request | None = None,
) -> None:
    """يُنهي علاقة أُسرية مع نظيرتها العكسية (حذف منطقي)."""
    from app.utils.dates import utcnow

    now = utcnow()
    relation.deleted_at = now
    relation.is_active = False

    mirror = db.scalar(
        select(FamilyRelation).where(
            FamilyRelation.person_id == relation.related_person_id,
            FamilyRelation.related_person_id == relation.person_id,
            FamilyRelation.deleted_at.is_(None),
        )
    )
    if mirror is not None:
        mirror.deleted_at = now
        mirror.is_active = False

    audit.record(
        db,
        action=AuditAction.DELETE,
        resource_type="family_relations",
        resource_id=relation.id,
        user=user,
        old_values={"relation_type": relation.relation_type.value},
        request=request,
    )

    db.commit()


# ---------------------------------------------------------------------------
# التحقق من تماسك العلاقات
# ---------------------------------------------------------------------------

def validate_new_relation(
    db: Session,
    person: Person,
    related: Person,
    relation_type: RelationType,
) -> list[str]:
    """يفحص علاقة قبل إنشائها ويُرجع قائمة المشاكل المنطقية."""
    problems: list[str] = []

    # 1) الجنس يجب أن يوافق نوع العلاقة
    expected_gender = {
        RelationType.FATHER: Gender.MALE,
        RelationType.MOTHER: Gender.FEMALE,
        RelationType.SON: Gender.MALE,
        RelationType.DAUGHTER: Gender.FEMALE,
        RelationType.HUSBAND: Gender.MALE,
        RelationType.WIFE: Gender.FEMALE,
        RelationType.BROTHER: Gender.MALE,
        RelationType.SISTER: Gender.FEMALE,
    }.get(relation_type)

    if expected_gender and related.gender != expected_gender:
        problems.append(
            f"العلاقة «{relation_type.value}» لا توافق جنس الشخص "
            f"({related.gender.value})"
        )

    # 2) الوالد يجب أن يكون أكبر من ولده بفارق معقول
    if relation_type in PARENT_RELATIONS:
        gap = (person.birth_date - related.birth_date).days / 365.25
        if gap < MIN_PARENT_AGE_YEARS:
            problems.append(
                f"فارق العمر بين الوالد وولده ({gap:.0f} سنة) أقل من "
                f"{MIN_PARENT_AGE_YEARS} سنة"
            )

    if relation_type in CHILD_RELATIONS:
        gap = (related.birth_date - person.birth_date).days / 365.25
        if gap < MIN_PARENT_AGE_YEARS:
            problems.append(
                f"فارق العمر بين الوالد وولده ({gap:.0f} سنة) أقل من "
                f"{MIN_PARENT_AGE_YEARS} سنة"
            )

    # 3) الشخص لا يكون أباً لجدّه — فحص الدور
    if relation_type in PARENT_RELATIONS + CHILD_RELATIONS:
        ancestor_id, descendant_id = (
            (related.id, person.id)
            if relation_type in PARENT_RELATIONS
            else (person.id, related.id)
        )
        if _is_descendant(db, ancestor_of=descendant_id, candidate=ancestor_id):
            problems.append(
                "هذه العلاقة تُنشئ دوراً في شجرة العائلة "
                "(الشخص يصبح سلفاً وخلفاً لنفسه)"
            )

    # 4) أب واحد وأم واحدة لكل شخص
    if relation_type in PARENT_RELATIONS:
        existing = _related_persons(db, person.id, (relation_type,))
        if existing and existing[0].id != related.id:
            label = "أب" if relation_type == RelationType.FATHER else "أم"
            problems.append(f"للشخص {label} مسجَّل مسبقاً: {existing[0].full_name}")

    return problems


def _is_descendant(
    db: Session, *, ancestor_of: uuid.UUID, candidate: uuid.UUID, depth: int = 0
) -> bool:
    """هل candidate من نسل ancestor_of؟ يُستعمل لكشف الدورات."""
    if depth > 10:  # حاجز أمان ضد الدورات القائمة أصلاً في البيانات
        return False

    children = get_relations(db, ancestor_of, types=CHILD_RELATIONS)
    for relation in children:
        if relation.related_person_id == candidate:
            return True
        if _is_descendant(
            db,
            ancestor_of=relation.related_person_id,
            candidate=candidate,
            depth=depth + 1,
        ):
            return True

    return False


def check_consistency(db: Session, person_id: uuid.UUID) -> list[dict]:
    """يفحص علاقات شخص ويُرجع قائمة التعارضات المكتشَفة."""
    conflicts: list[dict] = []
    person = db.get(Person, person_id)

    if person is None:
        return conflicts

    relations = get_relations(db, person_id, active_only=False)

    # تعدّد الآباء أو الأمهات
    by_type: dict[RelationType, list[Person]] = defaultdict(list)
    for relation in relations:
        if relation.deleted_at is None:
            by_type[relation.relation_type].append(relation.related_person)

    for parent_type, label in (
        (RelationType.FATHER, "أب"),
        (RelationType.MOTHER, "أم"),
    ):
        parents = by_type.get(parent_type, [])
        if len(parents) > 1:
            conflicts.append(
                {
                    "نوع_التعارض": "تعدّد الوالدين",
                    "الوصف": f"للشخص أكثر من {label} مسجَّل ({len(parents)})",
                    "الأشخاص": [p.full_name for p in parents],
                }
            )

    # فوارق عمرية غير منطقية
    for parent in by_type.get(RelationType.FATHER, []) + by_type.get(
        RelationType.MOTHER, []
    ):
        gap = (person.birth_date - parent.birth_date).days / 365.25
        if gap < MIN_PARENT_AGE_YEARS:
            conflicts.append(
                {
                    "نوع_التعارض": "فارق عمري غير منطقي",
                    "الوصف": (
                        f"فارق العمر مع الوالد {gap:.0f} سنة، "
                        f"وهو أقل من {MIN_PARENT_AGE_YEARS}"
                    ),
                    "الأشخاص": [person.full_name, parent.full_name],
                }
            )

    # جنس لا يوافق نوع العلاقة
    gender_map = {
        RelationType.FATHER: Gender.MALE,
        RelationType.MOTHER: Gender.FEMALE,
        RelationType.SON: Gender.MALE,
        RelationType.DAUGHTER: Gender.FEMALE,
        RelationType.HUSBAND: Gender.MALE,
        RelationType.WIFE: Gender.FEMALE,
        RelationType.BROTHER: Gender.MALE,
        RelationType.SISTER: Gender.FEMALE,
    }
    for relation in relations:
        if relation.deleted_at is not None:
            continue
        expected = gender_map.get(relation.relation_type)
        if expected and relation.related_person.gender != expected:
            conflicts.append(
                {
                    "نوع_التعارض": "جنس لا يوافق العلاقة",
                    "الوصف": (
                        f"مسجَّل كـ«{relation.relation_type.value}» "
                        f"وجنسه {relation.related_person.gender.value}"
                    ),
                    "الأشخاص": [relation.related_person.full_name],
                }
            )

    # علاقة زوجية نشطة مع متوفى
    from app.models import LifeStatus

    for spouse in by_type.get(RelationType.HUSBAND, []) + by_type.get(
        RelationType.WIFE, []
    ):
        active = any(
            r.related_person_id == spouse.id
            and r.is_active
            and r.relation_type in SPOUSE_RELATIONS
            for r in relations
        )
        if active and spouse.life_status == LifeStatus.DECEASED:
            conflicts.append(
                {
                    "نوع_التعارض": "زوجية نشطة مع متوفى",
                    "الوصف": "العلاقة الزوجية ما زالت نشطة رغم وفاة الطرف الآخر",
                    "الأشخاص": [spouse.full_name],
                }
            )

    return conflicts


# ---------------------------------------------------------------------------
# شجرة العائلة
# ---------------------------------------------------------------------------

def build_family_tree(db: Session, person: Person) -> dict:
    """يبني شجرة عائلة الشخص حتى ثلاثة أجيال حوله.

    جيل فوق (الوالدان والأجداد)، وجيل الشخص (الإخوة والأزواج)، وجيلان
    تحت (الأبناء والأحفاد).
    """
    father = _related_persons(db, person.id, (RelationType.FATHER,))
    mother = _related_persons(db, person.id, (RelationType.MOTHER,))
    children = _related_persons(db, person.id, CHILD_RELATIONS)

    grandparents: list[dict] = []
    for parent in father + mother:
        for grandparent in _related_persons(db, parent.id, PARENT_RELATIONS):
            grandparents.append(
                {"person": grandparent, "relation": RelationType.FATHER}
            )

    grandchildren: list[dict] = []
    for child in children:
        for grandchild in _related_persons(db, child.id, CHILD_RELATIONS):
            grandchildren.append(
                {
                    "person": grandchild,
                    "relation": RelationType.SON
                    if grandchild.gender == Gender.MALE
                    else RelationType.DAUGHTER,
                }
            )

    def node(p: Person, rel: RelationType | None) -> dict:
        return {"person": p, "relation": rel, "children": []}

    return {
        "person": person,
        "father": node(father[0], RelationType.FATHER) if father else None,
        "mother": node(mother[0], RelationType.MOTHER) if mother else None,
        "grandparents": [node(g["person"], g["relation"]) for g in grandparents],
        "spouses": [
            node(s, RelationType.HUSBAND if s.gender == Gender.MALE else RelationType.WIFE)
            for s in _related_persons(db, person.id, SPOUSE_RELATIONS)
        ],
        "siblings": [
            node(s, RelationType.BROTHER if s.gender == Gender.MALE else RelationType.SISTER)
            for s in _related_persons(db, person.id, SIBLING_RELATIONS)
        ],
        "children": [
            node(c, RelationType.SON if c.gender == Gender.MALE else RelationType.DAUGHTER)
            for c in children
        ],
        "grandchildren": [node(g["person"], g["relation"]) for g in grandchildren],
    }
