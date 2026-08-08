"""البحث المتقدم في السجل المدني.

ثلاث طبقات بحث تُجرَّب بالترتيب:
  1. مطابقة تامة على الرقم الوطني أو رقم الوثيقة — أسرع وأدقّ.
  2. مطابقة على الاسم المُطبَّع (تتجاهل التشكيل وصور الألف والتاء المربوطة).
  3. بحث تقريبي بثلاثيات الحروف — يلتقط الأخطاء الإملائية وتبديل الحروف.

الطبقة الثالثة تعتمد على امتداد pg_trgm في PostgreSQL، ولا تتوفّر في
SQLite، فتُنفَّذ هناك في طبقة بايثون على مجموعة مرشّحة محدودة.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, Gender, LifeStatus, Person
from app.utils.arabic import normalize_arabic

logger = logging.getLogger(__name__)

# عتبة التشابه في البحث التقريبي. القيمة الافتراضية في pg_trgm هي 0.3،
# وخفضناها قليلاً لأن الأسماء العربية الرباعية طويلة، فخطأ حرف واحد فيها
# يخفض درجة التشابه أكثر مما يخفضها في نص قصير.
SIMILARITY_THRESHOLD = 0.25

# سقف المرشّحين في البحث التقريبي داخل SQLite — يمنع تحميل الجدول كاملاً
SQLITE_FUZZY_CANDIDATE_LIMIT = 2000


@dataclass
class SearchCriteria:
    """معايير البحث. الحقول الفارغة تُتجاهل."""

    query: str | None = None               # نص حر: اسم أو رقم
    national_id: str | None = None
    document_number: str | None = None
    first_name: str | None = None
    father_name: str | None = None
    family_name: str | None = None
    mother_name: str | None = None
    birth_date: date | None = None
    birth_date_from: date | None = None
    birth_date_to: date | None = None
    gender: Gender | None = None
    life_status: LifeStatus | None = None
    governorate_id: int | None = None
    fuzzy: bool = True                     # السماح بالبحث التقريبي عند عدم وجود نتائج

    def is_empty(self) -> bool:
        """هل كل المعايير فارغة؟ البحث بلا معايير يعيد السجل كاملاً."""
        return not any(
            [
                self.query,
                self.national_id,
                self.document_number,
                self.first_name,
                self.father_name,
                self.family_name,
                self.mother_name,
                self.birth_date,
                self.birth_date_from,
                self.birth_date_to,
                self.gender,
                self.life_status,
                self.governorate_id,
            ]
        )


@dataclass
class SearchOutcome:
    """نتيجة بحث مع بيان الطريقة التي أنتجتها."""

    persons: list[Person]
    total: int
    method: str            # exact | normalized | fuzzy
    similarities: dict[str, float]


# ---------------------------------------------------------------------------
# أدوات
# ---------------------------------------------------------------------------

def _looks_like_national_id(text: str) -> bool:
    """هل يبدو النص رقماً وطنياً (12 خانة رقمية)؟"""
    return text.isdigit() and len(text) == 12


def _base_query() -> Select:
    """أساس كل استعلامات البحث: السجلات غير المحذوفة منطقياً."""
    return select(Person).where(Person.deleted_at.is_(None))


def _apply_filters(stmt: Select, criteria: SearchCriteria) -> Select:
    """يطبّق المرشّحات البنيوية (التواريخ، الجنس، الحالة، المحافظة)."""
    if criteria.gender is not None:
        stmt = stmt.where(Person.gender == criteria.gender)

    if criteria.life_status is not None:
        stmt = stmt.where(Person.life_status == criteria.life_status)

    if criteria.governorate_id is not None:
        stmt = stmt.where(Person.birth_governorate_id == criteria.governorate_id)

    if criteria.birth_date is not None:
        stmt = stmt.where(Person.birth_date == criteria.birth_date)
    else:
        if criteria.birth_date_from is not None:
            stmt = stmt.where(Person.birth_date >= criteria.birth_date_from)
        if criteria.birth_date_to is not None:
            stmt = stmt.where(Person.birth_date <= criteria.birth_date_to)

    return stmt


def _apply_name_filters(stmt: Select, criteria: SearchCriteria) -> Select:
    """يطبّق مرشّحات الأسماء على القيم المُطبَّعة.

    التطبيع يجري على الطرفين — المُدخل والعمود — فيتساوى «إبراهيم» و«ابراهيم»
    و«إبْراهيم» في نتيجة البحث.
    """
    parts = [
        (criteria.first_name, Person.first_name),
        (criteria.father_name, Person.father_name),
        (criteria.family_name, Person.family_name),
        (criteria.mother_name, Person.mother_full_name),
    ]

    for value, column in parts:
        if not value:
            continue
        normalized = normalize_arabic(value)
        stmt = stmt.where(
            func.normalize_arabic(column).like(f"%{normalized}%")
        )

    return stmt


# ---------------------------------------------------------------------------
# طبقات البحث
# ---------------------------------------------------------------------------

def _search_exact(db: Session, criteria: SearchCriteria) -> list[Person] | None:
    """مطابقة تامة على الرقم الوطني أو رقم الوثيقة.

    يُرجع None إن لم يكن هناك معيار مطابقة تامة، لتُجرَّب الطبقة التالية.
    """
    national_id = criteria.national_id
    if not national_id and criteria.query and _looks_like_national_id(criteria.query.strip()):
        national_id = criteria.query.strip()

    if national_id:
        person = db.scalar(
            _base_query().where(Person.national_id == national_id)
        )
        return [person] if person else []

    document_number = criteria.document_number
    if not document_number and criteria.query:
        candidate = criteria.query.strip()
        # أرقام الوثائق تخلط الحروف بالأرقام ولا تشبه الأسماء
        if candidate and any(c.isdigit() for c in candidate) and " " not in candidate:
            document_number = candidate

    if document_number:
        persons = db.scalars(
            _base_query()
            .join(Document, Document.person_id == Person.id)
            .where(
                Document.document_number == document_number,
                Document.deleted_at.is_(None),
            )
            .distinct()
        ).all()
        if persons:
            return list(persons)
        # رقم الوثيقة صريح ولم يُطابق: لا معنى لمتابعة البحث بالاسم
        if criteria.document_number:
            return []

    return None


def _search_normalized(
    db: Session, criteria: SearchCriteria, *, limit: int, offset: int
) -> tuple[list[Person], int]:
    """بحث بالاسم المُطبَّع مع بقية المرشّحات."""
    stmt = _apply_filters(_base_query(), criteria)
    stmt = _apply_name_filters(stmt, criteria)

    if criteria.query:
        normalized = normalize_arabic(criteria.query)
        if normalized:
            stmt = stmt.where(
                or_(
                    Person.full_name_normalized.like(f"%{normalized}%"),
                    func.normalize_arabic(Person.mother_full_name).like(
                        f"%{normalized}%"
                    ),
                )
            )

    total = db.scalar(
        select(func.count()).select_from(stmt.subquery())
    ) or 0

    persons = db.scalars(
        stmt.order_by(Person.family_name, Person.first_name)
        .limit(limit)
        .offset(offset)
    ).all()

    return list(persons), total


def _search_fuzzy_postgres(
    db: Session, criteria: SearchCriteria, *, limit: int, offset: int
) -> tuple[list[Person], int, dict[str, float]]:
    """بحث تقريبي بثلاثيات الحروف — يعتمد على فهرس GIN فيبقى سريعاً."""
    normalized = normalize_arabic(criteria.query or "")
    if not normalized:
        return [], 0, {}

    similarity = func.similarity(Person.full_name_normalized, normalized)

    stmt = _apply_filters(_base_query(), criteria).where(
        similarity > SIMILARITY_THRESHOLD
    )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    rows = db.execute(
        stmt.add_columns(similarity.label("score"))
        .order_by(similarity.desc(), Person.family_name)
        .limit(limit)
        .offset(offset)
    ).all()

    persons = [row[0] for row in rows]
    scores = {str(row[0].id): round(float(row[1]), 3) for row in rows}

    return persons, total, scores


def _search_fuzzy_python(
    db: Session, criteria: SearchCriteria, *, limit: int, offset: int
) -> tuple[list[Person], int, dict[str, float]]:
    """بحث تقريبي في طبقة بايثون — بديل SQLite حيث لا يتوفّر pg_trgm.

    يُحسب التشابه على مجموعة مرشّحة محدودة لا على الجدول كاملاً، فالكلفة
    مقبولة في بيئة التطوير وحدها. الإنتاج يستعمل المسار الأول.
    """
    from difflib import SequenceMatcher

    normalized = normalize_arabic(criteria.query or "")
    if not normalized:
        return [], 0, {}

    candidates = db.scalars(
        _apply_filters(_base_query(), criteria).limit(SQLITE_FUZZY_CANDIDATE_LIMIT)
    ).all()

    scored: list[tuple[Person, float]] = []
    for person in candidates:
        score = SequenceMatcher(
            None, normalized, person.full_name_normalized or ""
        ).ratio()
        if score > SIMILARITY_THRESHOLD:
            scored.append((person, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    window = scored[offset : offset + limit]

    return (
        [p for p, _ in window],
        len(scored),
        {str(p.id): round(s, 3) for p, s in window},
    )


# ---------------------------------------------------------------------------
# الواجهة العامة
# ---------------------------------------------------------------------------

def search_persons(
    db: Session,
    criteria: SearchCriteria,
    *,
    limit: int = 20,
    offset: int = 0,
) -> SearchOutcome:
    """يبحث عن الأشخاص وفق المعايير المعطاة.

    يجرّب المطابقة التامة أولاً، ثم المطابقة على الاسم المُطبَّع، ثم البحث
    التقريبي عند غياب النتائج — فلا يُدفع ثمن البحث التقريبي إلا عند الحاجة.
    """
    # 1) مطابقة تامة
    exact = _search_exact(db, criteria)
    if exact is not None:
        return SearchOutcome(
            persons=exact, total=len(exact), method="exact", similarities={}
        )

    # 2) مطابقة على الاسم المُطبَّع
    persons, total = _search_normalized(db, criteria, limit=limit, offset=offset)
    if persons or not criteria.fuzzy or not criteria.query:
        return SearchOutcome(
            persons=persons, total=total, method="normalized", similarities={}
        )

    # 3) بحث تقريبي — الملاذ الأخير
    if settings.is_sqlite:
        persons, total, scores = _search_fuzzy_python(
            db, criteria, limit=limit, offset=offset
        )
    else:
        persons, total, scores = _search_fuzzy_postgres(
            db, criteria, limit=limit, offset=offset
        )

    return SearchOutcome(
        persons=persons, total=total, method="fuzzy", similarities=scores
    )


def find_by_national_id(db: Session, national_id: str) -> Person | None:
    """بحث مباشر بالرقم الوطني."""
    return db.scalar(_base_query().where(Person.national_id == national_id))


def suggest_names(db: Session, prefix: str, *, limit: int = 10) -> list[str]:
    """يقترح أسماء تبدأ بالبادئة المعطاة — للإكمال التلقائي في الواجهة."""
    normalized = normalize_arabic(prefix)
    if not normalized or len(normalized) < 2:
        return []

    rows = db.scalars(
        select(Person.first_name)
        .where(
            Person.deleted_at.is_(None),
            func.normalize_arabic(Person.first_name).like(f"{normalized}%"),
        )
        .distinct()
        .limit(limit)
    ).all()

    return sorted(set(rows))
