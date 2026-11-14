"""مسارات الواقعات المدنية: الميلاد، الوفاة، الزواج، الطلاق."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession, RequirePermission, enforce_governorate_scope
from app.models import (
    BirthRecord,
    DeathRecord,
    DivorceRecord,
    MarriageContract,
    User,
)
from app.schemas.common import Page
from app.schemas.vital import (
    BirthRecordCreate,
    BirthRecordRead,
    DeathRecordCreate,
    DeathRecordRead,
    DivorceCreate,
    DivorceRead,
    MarriageCreate,
    MarriageRead,
)
from app.services import vital as vital_service
from app.services.vital import VitalError

router = APIRouter(tags=["الواقعات المدنية"])


def _http_error(exc: VitalError) -> HTTPException:
    """يحوّل خطأ الواقعة إلى استجابة HTTP بالرمز المناسب."""
    conflict_codes = {
        "duplicate_birth",
        "already_deceased",
        "wife_already_married",
        "contract_inactive",
    }
    not_found_codes = {
        "person_not_found",
        "parent_not_found",
        "party_not_found",
        "contract_not_found",
    }

    if exc.code in not_found_codes:
        code = status.HTTP_404_NOT_FOUND
    elif exc.code in conflict_codes:
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_400_BAD_REQUEST

    return HTTPException(
        status_code=code,
        detail={"نجاح": False, "الرسالة": exc.message, "الرمز": exc.code},
    )


# ---------------------------------------------------------------------------
# الميلاد
# ---------------------------------------------------------------------------

@router.post(
    "/births",
    response_model=BirthRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل واقعة ميلاد",
    tags=["واقعات الميلاد"],
)
async def register_birth(
    request: Request,
    payload: BirthRecordCreate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("births.create"))],
) -> BirthRecordRead:
    """يسجّل واقعة ميلاد ويربط المولود بوالديه في شجرة العائلة."""
    enforce_governorate_scope(user, payload.governorate_id)

    try:
        record = vital_service.register_birth(
            db, data=payload.model_dump(), user=user, request=request
        )
    except VitalError as exc:
        raise _http_error(exc) from exc

    return BirthRecordRead.model_validate(record)


@router.get(
    "/births",
    response_model=Page[BirthRecordRead],
    summary="قائمة واقعات الميلاد",
    tags=["واقعات الميلاد"],
)
async def list_births(
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("births.read"))],
    governorate_id: int | None = Query(None),
    year: int | None = Query(None, ge=1900, le=2200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[BirthRecordRead]:
    """يُرجع واقعات الميلاد مع إمكانية التصفية بالمحافظة والسنة."""
    stmt = (
        select(BirthRecord)
        .options(
            selectinload(BirthRecord.person),
            selectinload(BirthRecord.father),
            selectinload(BirthRecord.mother),
        )
        .where(BirthRecord.deleted_at.is_(None))
    )

    if governorate_id is not None:
        stmt = stmt.where(BirthRecord.governorate_id == governorate_id)
    if year is not None:
        stmt = stmt.where(func.extract("year", BirthRecord.birth_date) == year)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    records = db.scalars(
        stmt.order_by(BirthRecord.birth_date.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()

    return Page[BirthRecordRead](
        items=[BirthRecordRead.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/births/{record_id}",
    response_model=BirthRecordRead,
    summary="جلب واقعة ميلاد",
    tags=["واقعات الميلاد"],
)
async def get_birth(
    record_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("births.read"))],
) -> BirthRecordRead:
    """يجلب واقعة ميلاد بمعرّفها."""
    record = db.scalar(
        select(BirthRecord).where(
            BirthRecord.id == record_id, BirthRecord.deleted_at.is_(None)
        )
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"نجاح": False, "الرسالة": "واقعة الميلاد غير موجودة"},
        )

    return BirthRecordRead.model_validate(record)


# ---------------------------------------------------------------------------
# الوفاة
# ---------------------------------------------------------------------------

@router.post(
    "/deaths",
    response_model=DeathRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل واقعة وفاة",
    tags=["واقعات الوفاة"],
)
async def register_death(
    request: Request,
    payload: DeathRecordCreate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("deaths.create"))],
) -> DeathRecordRead:
    """يسجّل واقعة وفاة.

    الواقعة تُحدِّث حالة الشخص إلى «متوفى»، وتُنهي عقود زواجه النشطة،
    وتُرمِّل الطرف الباقي — كل ذلك في معاملة واحدة.
    """
    enforce_governorate_scope(user, payload.governorate_id)

    try:
        record = vital_service.register_death(
            db, data=payload.model_dump(), user=user, request=request
        )
    except VitalError as exc:
        raise _http_error(exc) from exc

    return DeathRecordRead.model_validate(record)


@router.get(
    "/deaths",
    response_model=Page[DeathRecordRead],
    summary="قائمة واقعات الوفاة",
    tags=["واقعات الوفاة"],
)
async def list_deaths(
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("deaths.read"))],
    governorate_id: int | None = Query(None),
    year: int | None = Query(None, ge=1900, le=2200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[DeathRecordRead]:
    """يُرجع واقعات الوفاة مع إمكانية التصفية."""
    stmt = (
        select(DeathRecord)
        .options(selectinload(DeathRecord.person))
        .where(DeathRecord.deleted_at.is_(None))
    )

    if governorate_id is not None:
        stmt = stmt.where(DeathRecord.governorate_id == governorate_id)
    if year is not None:
        stmt = stmt.where(func.extract("year", DeathRecord.death_date) == year)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    records = db.scalars(
        stmt.order_by(DeathRecord.death_date.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()

    return Page[DeathRecordRead](
        items=[DeathRecordRead.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# الزواج
# ---------------------------------------------------------------------------

@router.post(
    "/marriages",
    response_model=MarriageRead,
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل عقد زواج",
    tags=["عقود الزواج"],
)
async def register_marriage(
    request: Request,
    payload: MarriageCreate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("marriages.create"))],
) -> MarriageRead:
    """يسجّل عقد زواج بعد التحقق من السن والحالة الاجتماعية والقرابة."""
    enforce_governorate_scope(user, payload.governorate_id)

    try:
        contract = vital_service.register_marriage(
            db, data=payload.model_dump(), user=user, request=request
        )
    except VitalError as exc:
        raise _http_error(exc) from exc

    return MarriageRead.model_validate(contract)


@router.get(
    "/marriages",
    response_model=Page[MarriageRead],
    summary="قائمة عقود الزواج",
    tags=["عقود الزواج"],
)
async def list_marriages(
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("marriages.read"))],
    person_id: uuid.UUID | None = Query(None, description="عقود شخص معيّن"),
    active_only: bool = Query(False, description="العقود النشطة فقط"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[MarriageRead]:
    """يُرجع عقود الزواج."""
    stmt = (
        select(MarriageContract)
        .options(
            selectinload(MarriageContract.husband),
            selectinload(MarriageContract.wife),
        )
        .where(MarriageContract.deleted_at.is_(None))
    )

    if person_id is not None:
        stmt = stmt.where(
            or_(
                MarriageContract.husband_id == person_id,
                MarriageContract.wife_id == person_id,
            )
        )
    if active_only:
        stmt = stmt.where(MarriageContract.is_active.is_(True))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    records = db.scalars(
        stmt.order_by(MarriageContract.contract_date.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()

    return Page[MarriageRead](
        items=[MarriageRead.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# الطلاق
# ---------------------------------------------------------------------------

@router.post(
    "/divorces",
    response_model=DivorceRead,
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل واقعة طلاق",
    tags=["واقعات الطلاق"],
)
async def register_divorce(
    request: Request,
    payload: DivorceCreate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("divorces.create"))],
) -> DivorceRead:
    """يسجّل واقعة طلاق ويُنهي عقد الزواج المرتبط."""
    try:
        record = vital_service.register_divorce(
            db, data=payload.model_dump(), user=user, request=request
        )
    except VitalError as exc:
        raise _http_error(exc) from exc

    return DivorceRead.model_validate(record)


@router.get(
    "/divorces",
    response_model=Page[DivorceRead],
    summary="قائمة واقعات الطلاق",
    tags=["واقعات الطلاق"],
)
async def list_divorces(
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("divorces.read"))],
    year: int | None = Query(None, ge=1900, le=2200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[DivorceRead]:
    """يُرجع واقعات الطلاق."""
    stmt = (
        select(DivorceRecord)
        .options(
            selectinload(DivorceRecord.marriage).selectinload(
                MarriageContract.husband
            ),
            selectinload(DivorceRecord.marriage).selectinload(MarriageContract.wife),
        )
        .where(DivorceRecord.deleted_at.is_(None))
    )

    if year is not None:
        stmt = stmt.where(func.extract("year", DivorceRecord.divorce_date) == year)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    records = db.scalars(
        stmt.order_by(DivorceRecord.divorce_date.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()

    return Page[DivorceRead](
        items=[DivorceRead.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )
