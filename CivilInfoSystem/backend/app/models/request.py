"""نماذج المعاملات وطلبات الخدمة ومرفقاتها."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    enum_column,
)
from app.models.enums import RequestStatus, RequestType
from app.models.person import Person
from app.models.types import GUID


class ServiceRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """معاملة أو طلب خدمة مع مسار الموافقات."""

    __tablename__ = "service_requests"
    __table_args__ = (
        CheckConstraint("fee_amount >= 0", name="fee_positive"),
        # الرفض يستوجب ذكر السبب — قيد يحمي جودة السجل الإداري
        CheckConstraint(
            "status <> 'مرفوض' OR rejection_reason IS NOT NULL",
            name="rejection_reason",
        ),
    )

    reference_number: Mapped[str] = mapped_column(
        String(25), nullable=False, unique=True, index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    request_type: Mapped[RequestType] = enum_column(RequestType, nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RequestStatus] = enum_column(
        RequestStatus, nullable=False, default=RequestStatus.SUBMITTED, index=True
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    fee_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    person: Mapped[Person] = relationship()
    attachments: Mapped[list[RequestAttachment]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )

    @property
    def is_closed(self) -> bool:
        """هل انتهت المعاملة (قُبلت أو رُفضت أو أُلغيت)؟"""
        return self.status in (
            RequestStatus.APPROVED,
            RequestStatus.REJECTED,
            RequestStatus.CANCELLED,
        )

    def __repr__(self) -> str:
        return f"<ServiceRequest {self.reference_number} {self.status.value}>"


class RequestAttachment(Base, UUIDPrimaryKeyMixin):
    """مرفق مرفوع مع معاملة."""

    __tablename__ = "request_attachments"

    request_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))

    request: Mapped[ServiceRequest] = relationship(back_populates="attachments")

    def __repr__(self) -> str:
        return f"<RequestAttachment {self.file_name}>"
