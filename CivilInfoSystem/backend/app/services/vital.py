"""خدمة الواقعات المدنية: الميلاد، الوفاة، الزواج، الطلاق.

كل واقعة هنا تُغيّر أكثر من جدول، فتُنفَّذ داخل معاملة واحدة: تسجيل الوفاة
مثلاً يُحدِّث حالة الشخص، ويُنهي علاقاته الزوجية، ويُرمِّل الطرف الباقي.
إمّا أن يقع ذلك كلّه أو لا يقع منه شيء.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AuditAction,
    BirthRecord,
    DeathRecord,
    DivorceRecord,
    FamilyRelation,
    Gender,
    LifeStatus,
    MaritalStatus,
    MarriageContract,
    Person,
    RelationType,
    User,
)
from app.services import audit, family
from app.utils.dates import utcnow

logger = logging.getLogger(__name__)

# الحد الأدنى لسن الزواج
MIN_MARRIAGE_AGE = 18


class VitalError(Exception):
    """خطأ في تسجيل واقعة مدنية."""

    def __init__(self, message: str, *, code: str = "vital_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _next_record_number(
    db: Session, model, prefix: str, year: int, column: str = "record_number"
) -> str:
    """يولّد رقم سجل تسلسلياً ضمن السنة.

    عقود الزواج تسمّي عمودها contract_number لا record_number، فيُمرَّر
    اسم العمود بدل افتراضه.
    """
    number_column = getattr(model, column)
    count = db.scalar(
        select(func.count(model.id)).where(number_column.like(f"{prefix}-{year}-%"))
    ) or 0
    return f"{prefix}-{year}-{count + 1:05d}"


# ---------------------------------------------------------------------------
# الميلاد
# ---------------------------------------------------------------------------

def register_birth(
    db: Session,
    *,
    data: dict,
    user: User,
    request: Request | None = None,
) -> BirthRecord:
    """يسجّل واقعة ميلاد ويربط المولود بوالديه."""
    person = db.get(Person, data["person_id"])
    if person is None or person.deleted_at is not None:
        raise VitalError("سجل المولود غير موجود", code="person_not_found")

    existing = db.scalar(
        select(BirthRecord).where(
            BirthRecord.person_id == person.id, BirthRecord.deleted_at.is_(None)
        )
    )
    if existing is not None:
        raise VitalError(
            f"للمولود واقعة ميلاد مسجّلة مسبقاً برقم {existing.record_number}",
            code="duplicate_birth",
        )

    birth_date = data.get("birth_date") or person.birth_date
    if birth_date != person.birth_date:
        raise VitalError(
            "تاريخ الواقعة لا يطابق تاريخ الميلاد في سجل المولود",
            code="date_mismatch",
        )

    father = _load_parent(db, data.get("father_id"), Gender.MALE, "الأب")
    mother = _load_parent(db, data.get("mother_id"), Gender.FEMALE, "الأم")

    for parent, label in ((father, "الأب"), (mother, "الأم")):
        if parent is None:
            continue
        gap = (birth_date - parent.birth_date).days / 365.25
        if gap < family.MIN_PARENT_AGE_YEARS:
            raise VitalError(
                f"فارق العمر بين {label} والمولود ({gap:.0f} سنة) غير منطقي",
                code="invalid_parent_age",
            )
        # الوالد المتوفى قبل الولادة: الأم استحالة، والأب ممكن لكن يستحق تنبيهاً
        if parent.death_record and parent.death_record.death_date < birth_date:
            if parent.gender == Gender.FEMALE:
                raise VitalError(
                    "تاريخ وفاة الأم يسبق تاريخ ولادة المولود",
                    code="mother_deceased_before_birth",
                )
            logger.warning(
                "واقعة ميلاد لأب متوفى قبل تاريخ الولادة: %s", parent.national_id
            )

    record = BirthRecord(
        record_number=data.get("record_number")
        or _next_record_number(db, BirthRecord, "B", birth_date.year),
        created_by=user.id,
        updated_by=user.id,
        **{k: v for k, v in data.items() if k != "record_number"},
    )
    db.add(record)
    db.flush()

    # ربط المولود بوالديه في شجرة العائلة
    for parent, relation in ((father, RelationType.FATHER), (mother, RelationType.MOTHER)):
        if parent is None:
            continue
        _link_parent(db, child=person, parent=parent, relation=relation, user=user)

    audit.record(
        db,
        action=AuditAction.CREATE,
        resource_type="birth_records",
        resource_id=record.id,
        user=user,
        new_values={
            "record_number": record.record_number,
            "person_id": str(person.id),
            "birth_date": birth_date,
        },
        request=request,
    )

    db.commit()
    db.refresh(record)
    return record


def _load_parent(
    db: Session, parent_id: uuid.UUID | None, expected: Gender, label: str
) -> Person | None:
    """يجلب أحد الوالدين ويتحقق من جنسه."""
    if parent_id is None:
        return None

    parent = db.get(Person, parent_id)
    if parent is None or parent.deleted_at is not None:
        raise VitalError(f"سجل {label} غير موجود", code="parent_not_found")

    if parent.gender != expected:
        raise VitalError(
            f"جنس {label} لا يوافق دوره في الواقعة", code="parent_gender_mismatch"
        )

    return parent


def _link_parent(
    db: Session, *, child: Person, parent: Person, relation: RelationType, user: User
) -> None:
    """ينشئ علاقة الأبوّة باتجاهيها إن لم تكن موجودة."""
    existing = db.scalar(
        select(FamilyRelation).where(
            FamilyRelation.person_id == child.id,
            FamilyRelation.related_person_id == parent.id,
            FamilyRelation.relation_type == relation,
            FamilyRelation.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return

    child_relation = (
        RelationType.SON if child.gender == Gender.MALE else RelationType.DAUGHTER
    )

    db.add(
        FamilyRelation(
            person_id=child.id,
            related_person_id=parent.id,
            relation_type=relation,
            start_date=child.birth_date,
            created_by=user.id,
        )
    )
    db.add(
        FamilyRelation(
            person_id=parent.id,
            related_person_id=child.id,
            relation_type=child_relation,
            start_date=child.birth_date,
            created_by=user.id,
        )
    )


# ---------------------------------------------------------------------------
# الوفاة
# ---------------------------------------------------------------------------

def register_death(
    db: Session,
    *,
    data: dict,
    user: User,
    request: Request | None = None,
) -> DeathRecord:
    """يسجّل واقعة وفاة ويطبّق آثارها على السجلات المرتبطة.

    في PostgreSQL تتكفّل مُشغّلات قاعدة البيانات بجزء من الآثار؛ ويُطبَّق
    المنطق هنا أيضاً ليصحّ في SQLite وليبقى الكائن في الجلسة متسقاً.
    العمليات محايدة عند التكرار فلا يضرّ تنفيذها مرتين.
    """
    person = db.get(Person, data["person_id"])
    if person is None or person.deleted_at is not None:
        raise VitalError("سجل المتوفى غير موجود", code="person_not_found")

    if person.life_status == LifeStatus.DECEASED:
        existing = db.scalar(
            select(DeathRecord).where(
                DeathRecord.person_id == person.id, DeathRecord.deleted_at.is_(None)
            )
        )
        raise VitalError(
            f"الشخص مسجَّل متوفى مسبقاً"
            + (f" برقم {existing.record_number}" if existing else ""),
            code="already_deceased",
        )

    death_date = data["death_date"]
    if death_date < person.birth_date:
        raise VitalError(
            "تاريخ الوفاة لا يمكن أن يسبق تاريخ الميلاد", code="death_before_birth"
        )
    if death_date > date.today():
        raise VitalError(
            "تاريخ الوفاة لا يمكن أن يكون في المستقبل", code="future_death"
        )

    record = DeathRecord(
        record_number=data.get("record_number")
        or _next_record_number(db, DeathRecord, "V", death_date.year),
        created_by=user.id,
        updated_by=user.id,
        **{k: v for k, v in data.items() if k != "record_number"},
    )
    db.add(record)

    # الأثر 1: حالة الشخص
    person.life_status = LifeStatus.DECEASED
    person.updated_by = user.id

    # الأثر 2 و3: إنهاء الزوجية وترميل الطرف الباقي
    widowed = _end_marriages_on_death(db, person=person, death_date=death_date, user=user)

    audit.record(
        db,
        action=AuditAction.CREATE,
        resource_type="death_records",
        resource_id=person.id,
        user=user,
        old_values={"life_status": LifeStatus.ALIVE.value},
        new_values={
            "record_number": record.record_number,
            "death_date": death_date,
            "life_status": LifeStatus.DECEASED.value,
            "widowed_spouses": widowed,
        },
        request=request,
    )

    db.commit()
    db.refresh(record)
    return record


def _end_marriages_on_death(
    db: Session, *, person: Person, death_date: date, user: User
) -> int:
    """يُنهي عقود الزواج النشطة ويُرمِّل الأزواج الباقين. يُرجع عددهم."""
    contracts = db.scalars(
        select(MarriageContract).where(
            or_(
                MarriageContract.husband_id == person.id,
                MarriageContract.wife_id == person.id,
            ),
            MarriageContract.is_active.is_(True),
            MarriageContract.deleted_at.is_(None),
        )
    ).all()

    widowed = 0
    for contract in contracts:
        contract.is_active = False

        spouse_id = (
            contract.wife_id
            if contract.husband_id == person.id
            else contract.husband_id
        )
        spouse = db.get(Person, spouse_id)
        if spouse is not None and spouse.life_status == LifeStatus.ALIVE:
            spouse.marital_status = MaritalStatus.WIDOWED
            widowed += 1

    # إنهاء علاقات الزوجية في شجرة العائلة
    relations = db.scalars(
        select(FamilyRelation).where(
            or_(
                FamilyRelation.person_id == person.id,
                FamilyRelation.related_person_id == person.id,
            ),
            FamilyRelation.relation_type.in_(family.SPOUSE_RELATIONS),
            FamilyRelation.is_active.is_(True),
            FamilyRelation.deleted_at.is_(None),
        )
    ).all()

    for relation in relations:
        relation.is_active = False
        relation.end_date = death_date

    return widowed


# ---------------------------------------------------------------------------
# الزواج
# ---------------------------------------------------------------------------

def register_marriage(
    db: Session,
    *,
    data: dict,
    user: User,
    request: Request | None = None,
) -> MarriageContract:
    """يسجّل عقد زواج بعد التحقق من أهلية الطرفين."""
    husband = db.get(Person, data["husband_id"])
    wife = db.get(Person, data["wife_id"])

    for party, label, expected in (
        (husband, "الزوج", Gender.MALE),
        (wife, "الزوجة", Gender.FEMALE),
    ):
        if party is None or party.deleted_at is not None:
            raise VitalError(f"سجل {label} غير موجود", code="party_not_found")
        if party.gender != expected:
            raise VitalError(f"جنس {label} لا يوافق دوره في العقد", code="gender_mismatch")
        if party.life_status == LifeStatus.DECEASED:
            raise VitalError(f"{label} متوفى", code="party_deceased")

    if husband.id == wife.id:
        raise VitalError("لا يمكن عقد زواج الشخص بنفسه", code="self_marriage")

    contract_date = data["contract_date"]

    # السن عند العقد
    for party, label in ((husband, "الزوج"), (wife, "الزوجة")):
        age = (contract_date - party.birth_date).days / 365.25
        if age < MIN_MARRIAGE_AGE:
            raise VitalError(
                f"عمر {label} عند العقد ({age:.0f} سنة) أقل من السن القانونية "
                f"({MIN_MARRIAGE_AGE})",
                code="underage",
            )

    # الزوجة لا تكون مرتبطة بعقد نشط
    active_wife_contract = db.scalar(
        select(MarriageContract).where(
            MarriageContract.wife_id == wife.id,
            MarriageContract.is_active.is_(True),
            MarriageContract.deleted_at.is_(None),
        )
    )
    if active_wife_contract is not None:
        raise VitalError(
            "الزوجة مرتبطة بعقد زواج نشط", code="wife_already_married"
        )

    # قرابة محرِّمة مباشرة
    if _are_close_relatives(db, husband, wife):
        raise VitalError(
            "لا يجوز العقد لوجود قرابة مباشرة بين الطرفين", code="prohibited_relation"
        )

    contract = MarriageContract(
        contract_number=data.get("contract_number")
        or _next_record_number(
            db, MarriageContract, "M", contract_date.year, column="contract_number"
        ),
        created_by=user.id,
        updated_by=user.id,
        **{k: v for k, v in data.items() if k != "contract_number"},
    )
    db.add(contract)
    db.flush()

    husband.marital_status = MaritalStatus.MARRIED
    wife.marital_status = MaritalStatus.MARRIED

    _link_spouses(db, husband=husband, wife=wife, start=contract_date, user=user)

    audit.record(
        db,
        action=AuditAction.CREATE,
        resource_type="marriage_contracts",
        resource_id=contract.id,
        user=user,
        new_values={
            "contract_number": contract.contract_number,
            "husband": husband.national_id,
            "wife": wife.national_id,
            "contract_date": contract_date,
        },
        request=request,
    )

    db.commit()
    db.refresh(contract)
    return contract


def _are_close_relatives(db: Session, a: Person, b: Person) -> bool:
    """هل بين الشخصين قرابة مباشرة تمنع الزواج (أصول، فروع، إخوة)؟"""
    blocking = (
        family.PARENT_RELATIONS + family.CHILD_RELATIONS + family.SIBLING_RELATIONS
    )

    direct = db.scalar(
        select(FamilyRelation).where(
            FamilyRelation.person_id == a.id,
            FamilyRelation.related_person_id == b.id,
            FamilyRelation.relation_type.in_(blocking),
            FamilyRelation.deleted_at.is_(None),
        )
    )
    if direct is not None:
        return True

    # أب مشترك أو أم مشتركة = إخوة وإن لم تُسجَّل علاقة الأخوّة صراحةً
    parents_a = {
        r.related_person_id
        for r in family.get_relations(db, a.id, types=family.PARENT_RELATIONS)
    }
    parents_b = {
        r.related_person_id
        for r in family.get_relations(db, b.id, types=family.PARENT_RELATIONS)
    }

    return bool(parents_a & parents_b)


def _link_spouses(
    db: Session, *, husband: Person, wife: Person, start: date, user: User
) -> None:
    """ينشئ علاقة الزوجية باتجاهيها."""
    for person, related, relation in (
        (husband, wife, RelationType.WIFE),
        (wife, husband, RelationType.HUSBAND),
    ):
        existing = db.scalar(
            select(FamilyRelation).where(
                FamilyRelation.person_id == person.id,
                FamilyRelation.related_person_id == related.id,
                FamilyRelation.relation_type == relation,
                FamilyRelation.deleted_at.is_(None),
            )
        )
        if existing is not None:
            existing.is_active = True
            existing.end_date = None
            continue

        db.add(
            FamilyRelation(
                person_id=person.id,
                related_person_id=related.id,
                relation_type=relation,
                start_date=start,
                created_by=user.id,
            )
        )


# ---------------------------------------------------------------------------
# الطلاق
# ---------------------------------------------------------------------------

def register_divorce(
    db: Session,
    *,
    data: dict,
    user: User,
    request: Request | None = None,
) -> DivorceRecord:
    """يسجّل واقعة طلاق ويُنهي عقد الزواج المرتبط."""
    contract = db.get(MarriageContract, data["marriage_id"])

    if contract is None or contract.deleted_at is not None:
        raise VitalError("عقد الزواج غير موجود", code="contract_not_found")

    if not contract.is_active:
        raise VitalError(
            "عقد الزواج منتهٍ مسبقاً (طلاق أو وفاة)", code="contract_inactive"
        )

    divorce_date = data["divorce_date"]
    if divorce_date < contract.contract_date:
        raise VitalError(
            "تاريخ الطلاق لا يمكن أن يسبق تاريخ عقد الزواج",
            code="divorce_before_marriage",
        )
    if divorce_date > date.today():
        raise VitalError("تاريخ الطلاق لا يمكن أن يكون في المستقبل", code="future_date")

    record = DivorceRecord(
        record_number=data.get("record_number")
        or _next_record_number(db, DivorceRecord, "T", divorce_date.year),
        created_by=user.id,
        updated_by=user.id,
        **{k: v for k, v in data.items() if k != "record_number"},
    )
    db.add(record)

    contract.is_active = False

    husband = db.get(Person, contract.husband_id)
    wife = db.get(Person, contract.wife_id)
    for party in (husband, wife):
        if party is not None and party.life_status == LifeStatus.ALIVE:
            party.marital_status = MaritalStatus.DIVORCED

    # إنهاء علاقة الزوجية في شجرة العائلة
    relations = db.scalars(
        select(FamilyRelation).where(
            or_(
                (FamilyRelation.person_id == contract.husband_id)
                & (FamilyRelation.related_person_id == contract.wife_id),
                (FamilyRelation.person_id == contract.wife_id)
                & (FamilyRelation.related_person_id == contract.husband_id),
            ),
            FamilyRelation.relation_type.in_(family.SPOUSE_RELATIONS),
            FamilyRelation.deleted_at.is_(None),
        )
    ).all()

    for relation in relations:
        relation.is_active = False
        relation.end_date = divorce_date

    audit.record(
        db,
        action=AuditAction.CREATE,
        resource_type="divorce_records",
        resource_id=record.id,
        user=user,
        old_values={"contract_active": True},
        new_values={
            "record_number": record.record_number,
            "marriage_id": str(contract.id),
            "divorce_date": divorce_date,
        },
        request=request,
    )

    db.commit()
    db.refresh(record)
    return record
