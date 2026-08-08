"""خدمة الأشخاص: الإنشاء والتعديل والحذف المنطقي وإدارة العناوين."""

from __future__ import annotations

import logging
import uuid
from datetime import date

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Address, AuditAction, LifeStatus, Person, User
from app.services import audit
from app.utils.dates import utcnow

logger = logging.getLogger(__name__)


class PersonError(Exception):
    """خطأ في عملية على سجل شخص."""

    def __init__(self, message: str, *, code: str = "person_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


# ---------------------------------------------------------------------------
# القراءة
# ---------------------------------------------------------------------------

def get_person(db: Session, person_id: uuid.UUID) -> Person:
    """يجلب شخصاً أو يرفع خطأً إن لم يوجد أو كان محذوفاً منطقياً."""
    person = db.scalar(
        select(Person)
        .options(selectinload(Person.addresses))
        .where(Person.id == person_id, Person.deleted_at.is_(None))
    )

    if person is None:
        raise PersonError("السجل غير موجود", code="not_found")

    return person


def get_by_national_id(db: Session, national_id: str) -> Person:
    """يجلب شخصاً بالرقم الوطني."""
    person = db.scalar(
        select(Person).where(
            Person.national_id == national_id, Person.deleted_at.is_(None)
        )
    )

    if person is None:
        raise PersonError("لا يوجد سجل بهذا الرقم الوطني", code="not_found")

    return person


# ---------------------------------------------------------------------------
# الإنشاء
# ---------------------------------------------------------------------------

def create_person(
    db: Session,
    *,
    data: dict,
    address: dict | None = None,
    user: User,
    request: Request | None = None,
) -> Person:
    """ينشئ سجل شخص جديداً مع عنوانه الاختياري."""
    national_id = data["national_id"]

    existing = db.scalar(select(Person).where(Person.national_id == national_id))
    if existing is not None:
        # السجل المحذوف منطقياً ما زال يحجز الرقم الوطني — وهذا مقصود:
        # الرقم لا يُعاد استعماله لشخص آخر.
        raise PersonError(
            "الرقم الوطني مسجَّل مسبقاً لشخص آخر", code="duplicate_national_id"
        )

    person = Person(**data, created_by=user.id, updated_by=user.id)
    db.add(person)
    db.flush()

    if address:
        db.add(
            Address(
                person_id=person.id,
                is_current=True,
                created_by=user.id,
                **address,
            )
        )

    audit.record(
        db,
        action=AuditAction.CREATE,
        resource_type="persons",
        resource_id=person.id,
        user=user,
        new_values={
            "national_id": person.national_id,
            "full_name": person.full_name,
            "birth_date": person.birth_date,
        },
        request=request,
    )

    db.commit()
    db.refresh(person)
    return person


# ---------------------------------------------------------------------------
# التعديل
# ---------------------------------------------------------------------------

def update_person(
    db: Session,
    *,
    person: Person,
    changes: dict,
    user: User,
    request: Request | None = None,
) -> Person:
    """يعدّل بيانات شخص ويقيّد ما تغيّر فعلياً في سجل التدقيق."""
    if person.life_status == LifeStatus.DECEASED:
        # سجل المتوفى يُصحَّح بمعاملة معتمَدة لا بتعديل مباشر
        raise PersonError(
            "لا يمكن تعديل سجل شخص متوفى مباشرةً. قدّم معاملة تصحيح",
            code="deceased_record",
        )

    applied = {k: v for k, v in changes.items() if v is not None}
    for field, value in applied.items():
        setattr(person, field, value)

    person.updated_by = user.id

    entry = audit.record_change(
        db,
        instance=person,
        action=AuditAction.UPDATE,
        user=user,
        request=request,
    )

    if entry is None:
        # لم يتغيّر شيء فعلياً — لا داعي لقيد تدقيق فارغ
        db.rollback()
        return person

    db.commit()
    db.refresh(person)
    return person


def change_address(
    db: Session,
    *,
    person: Person,
    address: dict,
    user: User,
    request: Request | None = None,
) -> Address:
    """يسجّل انتقال الشخص إلى عنوان جديد.

    العنوان السابق لا يُحذف بل يُغلق بتاريخ انتهاء، فيبقى سجل التنقّلات
    كاملاً — وهو مطلوب في السجل المدني لإثبات محل الإقامة في فترة سابقة.
    """
    valid_from = address.get("valid_from") or date.today()

    current = person.current_address
    if current is not None:
        if valid_from < current.valid_from:
            raise PersonError(
                "تاريخ العنوان الجديد يسبق تاريخ العنوان الحالي",
                code="invalid_address_date",
            )
        current.is_current = False
        current.valid_to = valid_from
        current.updated_by = user.id

    new_address = Address(
        person_id=person.id, is_current=True, created_by=user.id, **address
    )
    db.add(new_address)

    audit.record(
        db,
        action=AuditAction.UPDATE,
        resource_type="addresses",
        resource_id=person.id,
        user=user,
        old_values={"governorate_id": current.governorate_id} if current else None,
        new_values={
            "governorate_id": new_address.governorate_id,
            "quarter": new_address.quarter,
        },
        request=request,
    )

    db.commit()
    db.refresh(new_address)
    return new_address


# ---------------------------------------------------------------------------
# الحذف المنطقي
# ---------------------------------------------------------------------------

def soft_delete_person(
    db: Session,
    *,
    person: Person,
    reason: str,
    user: User,
    request: Request | None = None,
) -> None:
    """يحذف سجل شخص حذفاً منطقياً.

    لا يُحذف أي سجل مدني حذفاً فعلياً. ويُمنع الحذف إن كان السجل مرتبطاً
    بواقعات أو أبناء، لأن حذفه يترك سجلات يتيمة تشير إلى شخص غير موجود.
    """
    if person.deleted_at is not None:
        raise PersonError("السجل محذوف مسبقاً", code="already_deleted")

    blockers = _find_deletion_blockers(db, person)
    if blockers:
        raise PersonError(
            "لا يمكن حذف السجل لارتباطه بـ: " + "، ".join(blockers),
            code="has_dependents",
        )

    person.deleted_at = utcnow()
    person.updated_by = user.id

    audit.record(
        db,
        action=AuditAction.DELETE,
        resource_type="persons",
        resource_id=person.id,
        user=user,
        old_values={"national_id": person.national_id, "full_name": person.full_name},
        new_values={"reason": reason},
        request=request,
    )

    db.commit()


def _find_deletion_blockers(db: Session, person: Person) -> list[str]:
    """يُرجع أسماء الارتباطات التي تمنع حذف السجل."""
    from sqlalchemy import func

    from app.models import BirthRecord, DeathRecord, MarriageContract

    blockers: list[str] = []

    children = db.scalar(
        select(func.count(BirthRecord.id)).where(
            (BirthRecord.father_id == person.id)
            | (BirthRecord.mother_id == person.id),
            BirthRecord.deleted_at.is_(None),
        )
    )
    if children:
        blockers.append(f"{children} واقعة ميلاد كأب أو أم")

    marriages = db.scalar(
        select(func.count(MarriageContract.id)).where(
            (MarriageContract.husband_id == person.id)
            | (MarriageContract.wife_id == person.id),
            MarriageContract.deleted_at.is_(None),
        )
    )
    if marriages:
        blockers.append(f"{marriages} عقد زواج")

    death = db.scalar(
        select(func.count(DeathRecord.id)).where(
            DeathRecord.person_id == person.id, DeathRecord.deleted_at.is_(None)
        )
    )
    if death:
        blockers.append("واقعة وفاة")

    return blockers


def restore_person(
    db: Session,
    *,
    person_id: uuid.UUID,
    user: User,
    request: Request | None = None,
) -> Person:
    """يستعيد سجلاً محذوفاً منطقياً."""
    person = db.get(Person, person_id)

    if person is None:
        raise PersonError("السجل غير موجود", code="not_found")
    if person.deleted_at is None:
        raise PersonError("السجل غير محذوف", code="not_deleted")

    person.deleted_at = None
    person.updated_by = user.id

    audit.record(
        db,
        action=AuditAction.UPDATE,
        resource_type="persons",
        resource_id=person.id,
        user=user,
        new_values={"restored": True},
        request=request,
    )

    db.commit()
    db.refresh(person)
    return person
