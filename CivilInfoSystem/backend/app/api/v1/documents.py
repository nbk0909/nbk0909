"""مسارات الوثائق والمعاملات والتقسيمات الإدارية."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession, RequirePermission
from app.models import (
    AuditAction,
    District,
    Document,
    DocumentStatus,
    DocumentType,
    Governorate,
    Person,
    RequestStatus,
    ServiceRequest,
    User,
)
from app.schemas.common import Page
from app.schemas.document import (
    DocumentCreate,
    DocumentRead,
    DocumentStatusUpdate,
    DocumentWithPerson,
    GovernorateRead,
    ServiceRequestCreate,
    ServiceRequestDecision,
    ServiceRequestRead,
)
from app.services import audit
from app.utils.dates import utcnow

router = APIRouter()


def _not_found(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"نجاح": False, "الرسالة": message},
    )


def _conflict(message: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"نجاح": False, "الرسالة": message, "الرمز": code},
    )


# ---------------------------------------------------------------------------
# الوثائق
# ---------------------------------------------------------------------------

@router.post(
    "/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="إصدار وثيقة",
    tags=["الوثائق"],
)
async def issue_document(
    request: Request,
    payload: DocumentCreate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("documents.create"))],
) -> DocumentRead:
    """يُصدر وثيقة جديدة.

    الشخص لا يحمل أكثر من وثيقة سارية من النوع نفسه: إصدار بديل يستوجب
    تغيير حالة القديمة أولاً، وإلا سرت بطاقتان وطنيتان معاً.
    """
    person = db.scalar(
        select(Person).where(
            Person.id == payload.person_id, Person.deleted_at.is_(None)
        )
    )
    if person is None:
        raise _not_found("سجل الشخص غير موجود")

    duplicate_number = db.scalar(
        select(Document).where(
            Document.document_type == payload.document_type,
            Document.document_number == payload.document_number,
            Document.deleted_at.is_(None),
        )
    )
    if duplicate_number is not None:
        raise _conflict("رقم الوثيقة مستعمل مسبقاً", "duplicate_number")

    active = db.scalar(
        select(Document).where(
            Document.person_id == person.id,
            Document.document_type == payload.document_type,
            Document.status == DocumentStatus.VALID,
            Document.deleted_at.is_(None),
        )
    )
    if active is not None:
        raise _conflict(
            f"للشخص وثيقة سارية من هذا النوع برقم {active.document_number}. "
            f"غيّر حالتها أولاً",
            "active_document_exists",
        )

    document = Document(
        **payload.model_dump(), created_by=user.id, updated_by=user.id
    )
    db.add(document)

    audit.record(
        db,
        action=AuditAction.CREATE,
        resource_type="documents",
        resource_id=person.id,
        user=user,
        new_values={
            "document_type": payload.document_type.value,
            "document_number": payload.document_number,
        },
        request=request,
    )

    db.commit()
    db.refresh(document)
    return DocumentRead.model_validate(document)


@router.get(
    "/persons/{person_id}/documents",
    response_model=list[DocumentRead],
    summary="وثائق شخص",
    tags=["الوثائق"],
)
async def person_documents(
    person_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("documents.read"))],
    valid_only: bool = Query(False, description="الوثائق السارية فقط"),
) -> list[DocumentRead]:
    """يُرجع وثائق الشخص."""
    stmt = select(Document).where(
        Document.person_id == person_id, Document.deleted_at.is_(None)
    )
    if valid_only:
        stmt = stmt.where(Document.status == DocumentStatus.VALID)

    documents = db.scalars(stmt.order_by(Document.issue_date.desc())).all()
    return [DocumentRead.model_validate(d) for d in documents]


@router.patch(
    "/documents/{document_id}/status",
    response_model=DocumentRead,
    summary="تغيير حالة وثيقة",
    tags=["الوثائق"],
)
async def update_document_status(
    request: Request,
    document_id: uuid.UUID,
    payload: DocumentStatusUpdate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("documents.update"))],
) -> DocumentRead:
    """يغيّر حالة الوثيقة (فقدان، إلغاء، انتهاء)."""
    document = db.scalar(
        select(Document).where(
            Document.id == document_id, Document.deleted_at.is_(None)
        )
    )
    if document is None:
        raise _not_found("الوثيقة غير موجودة")

    old_status = document.status
    document.status = payload.status
    document.updated_by = user.id
    if payload.notes:
        document.notes = payload.notes

    audit.record(
        db,
        action=AuditAction.UPDATE,
        resource_type="documents",
        resource_id=document.id,
        user=user,
        old_values={"status": old_status.value},
        new_values={"status": payload.status.value, "notes": payload.notes},
        request=request,
    )

    db.commit()
    db.refresh(document)
    return DocumentRead.model_validate(document)


@router.get(
    "/documents/expiring",
    response_model=Page[DocumentWithPerson],
    summary="الوثائق التي توشك على الانتهاء",
    tags=["الوثائق"],
)
async def expiring_documents(
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("documents.read"))],
    days: int = Query(90, ge=1, le=365, description="خلال كم يوماً"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[DocumentWithPerson]:
    """يُرجع الوثائق السارية التي تنتهي خلال المدة المحدّدة."""
    horizon = date.today() + timedelta(days=days)

    stmt = (
        select(Document)
        .options(selectinload(Document.person))
        .where(
            Document.deleted_at.is_(None),
            Document.status == DocumentStatus.VALID,
            Document.expiry_date.is_not(None),
            Document.expiry_date >= date.today(),
            Document.expiry_date <= horizon,
        )
    )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    documents = db.scalars(
        stmt.order_by(Document.expiry_date)
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()

    return Page[DocumentWithPerson](
        items=[DocumentWithPerson.model_validate(d) for d in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# المعاملات
# ---------------------------------------------------------------------------

@router.post(
    "/requests",
    response_model=ServiceRequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="تقديم معاملة",
    tags=["المعاملات"],
)
async def submit_request(
    request: Request,
    payload: ServiceRequestCreate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("requests.create"))],
) -> ServiceRequestRead:
    """يقدّم معاملة جديدة ويولّد لها رقماً مرجعياً."""
    person = db.scalar(
        select(Person).where(
            Person.id == payload.person_id, Person.deleted_at.is_(None)
        )
    )
    if person is None:
        raise _not_found("سجل الشخص غير موجود")

    year = date.today().year
    count = db.scalar(
        select(func.count(ServiceRequest.id)).where(
            ServiceRequest.reference_number.like(f"REQ-{year}-%")
        )
    ) or 0

    service_request = ServiceRequest(
        reference_number=f"REQ-{year}-{count + 1:06d}",
        submitted_by=user.id,
        **payload.model_dump(),
    )
    db.add(service_request)

    audit.record(
        db,
        action=AuditAction.CREATE,
        resource_type="service_requests",
        resource_id=person.id,
        user=user,
        new_values={
            "reference_number": service_request.reference_number,
            "request_type": payload.request_type.value,
        },
        request=request,
    )

    db.commit()
    db.refresh(service_request)
    return ServiceRequestRead.model_validate(service_request)


@router.get(
    "/requests",
    response_model=Page[ServiceRequestRead],
    summary="قائمة المعاملات",
    tags=["المعاملات"],
)
async def list_requests(
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("requests.read"))],
    request_status: RequestStatus | None = Query(None, alias="status"),
    person_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ServiceRequestRead]:
    """يُرجع المعاملات مع إمكانية التصفية بالحالة أو الشخص."""
    stmt = (
        select(ServiceRequest)
        .options(selectinload(ServiceRequest.person))
        .where(ServiceRequest.deleted_at.is_(None))
    )

    if request_status is not None:
        stmt = stmt.where(ServiceRequest.status == request_status)
    if person_id is not None:
        stmt = stmt.where(ServiceRequest.person_id == person_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    records = db.scalars(
        stmt.order_by(ServiceRequest.submitted_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()

    return Page[ServiceRequestRead](
        items=[ServiceRequestRead.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/requests/{request_id}/decision",
    response_model=ServiceRequestRead,
    summary="اتخاذ قرار في معاملة",
    tags=["المعاملات"],
)
async def decide_request(
    http_request: Request,
    request_id: uuid.UUID,
    payload: ServiceRequestDecision,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("requests.approve"))],
) -> ServiceRequestRead:
    """يعتمد المعاملة أو يرفضها. الرفض يستوجب ذكر السبب."""
    service_request = db.scalar(
        select(ServiceRequest).where(
            ServiceRequest.id == request_id, ServiceRequest.deleted_at.is_(None)
        )
    )
    if service_request is None:
        raise _not_found("المعاملة غير موجودة")

    if service_request.is_closed:
        raise _conflict(
            f"المعاملة منتهية مسبقاً بحالة «{service_request.status.value}»",
            "request_closed",
        )

    old_status = service_request.status
    service_request.status = payload.status
    service_request.rejection_reason = payload.rejection_reason
    service_request.decision_at = utcnow()
    service_request.decision_by = user.id

    if service_request.reviewed_at is None:
        service_request.reviewed_at = utcnow()
        service_request.reviewed_by = user.id

    audit.record(
        db,
        action=AuditAction.APPROVE,
        resource_type="service_requests",
        resource_id=service_request.id,
        user=user,
        old_values={"status": old_status.value},
        new_values={
            "status": payload.status.value,
            "rejection_reason": payload.rejection_reason,
        },
        request=http_request,
    )

    db.commit()
    db.refresh(service_request)
    return ServiceRequestRead.model_validate(service_request)


# ---------------------------------------------------------------------------
# التقسيمات الإدارية
# ---------------------------------------------------------------------------

@router.get(
    "/locations/governorates",
    response_model=list[GovernorateRead],
    summary="المحافظات والأقضية والنواحي",
    tags=["التقسيمات الإدارية"],
)
async def list_governorates(
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.read"))],
    with_districts: bool = Query(True, description="تضمين الأقضية والنواحي"),
) -> list[GovernorateRead]:
    """يُرجع شجرة التقسيمات الإدارية — تُستعمل في قوائم النماذج."""
    stmt = select(Governorate).where(Governorate.deleted_at.is_(None))

    if with_districts:
        stmt = stmt.options(
            selectinload(Governorate.districts).selectinload(District.subdistricts)
        )

    governorates = db.scalars(stmt.order_by(Governorate.code)).all()
    return [GovernorateRead.model_validate(g) for g in governorates]
