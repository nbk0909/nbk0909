"""مخططات الوثائق والمعاملات والتقسيمات الإدارية."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.enums import (
    DocumentStatus,
    DocumentType,
    RequestStatus,
    RequestType,
)
from app.schemas.person import PersonSummary


# ---------------------------------------------------------------------------
# الوثائق
# ---------------------------------------------------------------------------

class DocumentCreate(BaseModel):
    """إصدار وثيقة جديدة."""

    person_id: uuid.UUID = Field(..., description="صاحب الوثيقة")
    document_type: DocumentType = Field(..., description="نوع الوثيقة")
    document_number: str = Field(..., min_length=3, max_length=30)
    issue_date: date = Field(..., description="تاريخ الإصدار")
    expiry_date: date | None = Field(None, description="تاريخ الانتهاء")
    issuing_authority: str = Field(..., min_length=3, max_length=200)
    issuing_governorate_id: int | None = None
    replaces_document_id: uuid.UUID | None = Field(
        None, description="الوثيقة التي تحلّ هذه محلّها (بدل فاقد)"
    )
    notes: str | None = None

    @model_validator(mode="after")
    def _check_dates(self):
        if self.issue_date > date.today():
            raise ValueError("تاريخ الإصدار لا يمكن أن يكون في المستقبل")
        if self.expiry_date and self.expiry_date <= self.issue_date:
            raise ValueError("تاريخ الانتهاء يجب أن يكون بعد تاريخ الإصدار")
        return self


class DocumentRead(BaseModel):
    """وثيقة معروضة."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: DocumentType
    document_number: str
    issue_date: date
    expiry_date: date | None = None
    issuing_authority: str
    status: DocumentStatus
    notes: str | None = None

    @computed_field
    @property
    def is_expired(self) -> bool:
        """هل انتهت صلاحية الوثيقة؟"""
        return self.expiry_date is not None and self.expiry_date < date.today()

    @computed_field
    @property
    def days_until_expiry(self) -> int | None:
        """الأيام المتبقية — سالبة إن انتهت."""
        if self.expiry_date is None:
            return None
        return (self.expiry_date - date.today()).days


class DocumentWithPerson(DocumentRead):
    """وثيقة مع بيانات صاحبها."""

    person: PersonSummary


class DocumentStatusUpdate(BaseModel):
    """تغيير حالة وثيقة (فقدان، إلغاء، انتهاء)."""

    status: DocumentStatus = Field(..., description="الحالة الجديدة")
    notes: str | None = Field(None, description="سبب التغيير")


# ---------------------------------------------------------------------------
# المعاملات
# ---------------------------------------------------------------------------

class ServiceRequestCreate(BaseModel):
    """تقديم معاملة."""

    person_id: uuid.UUID = Field(..., description="مقدّم الطلب")
    request_type: RequestType = Field(..., description="نوع المعاملة")
    subject: str = Field(..., min_length=5, max_length=200, description="الموضوع")
    details: str | None = None
    fee_amount: Decimal = Field(0, ge=0, description="الرسوم")


class ServiceRequestDecision(BaseModel):
    """قرار في معاملة."""

    status: RequestStatus = Field(..., description="القرار")
    rejection_reason: str | None = Field(
        None, description="سبب الرفض — إلزامي عند الرفض"
    )

    @model_validator(mode="after")
    def _reason_required_on_reject(self):
        if self.status == RequestStatus.REJECTED and not self.rejection_reason:
            raise ValueError("سبب الرفض إلزامي عند رفض المعاملة")
        return self


class ServiceRequestRead(BaseModel):
    """معاملة معروضة."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference_number: str
    request_type: RequestType
    subject: str
    details: str | None = None
    status: RequestStatus
    submitted_at: datetime
    reviewed_at: datetime | None = None
    decision_at: datetime | None = None
    rejection_reason: str | None = None
    fee_amount: Decimal
    fee_paid: bool
    person: PersonSummary


# ---------------------------------------------------------------------------
# التقسيمات الإدارية
# ---------------------------------------------------------------------------

class SubdistrictRead(BaseModel):
    """ناحية."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name_ar: str


class DistrictRead(BaseModel):
    """قضاء مع نواحيه."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name_ar: str
    name_en: str | None = None
    subdistricts: list[SubdistrictRead] = Field(default_factory=list)


class GovernorateRead(BaseModel):
    """محافظة مع أقضيتها."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name_ar: str
    name_en: str | None = None
    districts: list[DistrictRead] = Field(default_factory=list)
