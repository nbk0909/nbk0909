"""نموذج الوثائق والهويات الرسمية."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import (
    AuditMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    enum_column,
)
from app.models.enums import DocumentStatus, DocumentType
from app.models.person import Person
from app.models.types import GUID


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """وثيقة رسمية: بطاقة وطنية، جواز سفر، شهادة جنسية."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("document_type", "document_number", name="uq_document"),
        CheckConstraint(
            "expiry_date IS NULL OR expiry_date > issue_date", name="document_dates"
        ),
        # وثيقة سارية واحدة فقط من كل نوع لكل شخص: إصدار بدل فاقد يستوجب
        # تغيير حالة الوثيقة القديمة أولاً، وإلا سرت بطاقتان وطنيتان معاً.
        Index(
            "uq_active_document_per_type",
            "person_id",
            "document_type",
            unique=True,
            postgresql_where=text("status = 'سارية' AND deleted_at IS NULL"),
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    document_type: Mapped[DocumentType] = enum_column(DocumentType, nullable=False)
    document_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)
    issuing_authority: Mapped[str] = mapped_column(String(200), nullable=False)
    issuing_governorate_id: Mapped[int | None] = mapped_column(
        ForeignKey("governorates.id")
    )
    status: Mapped[DocumentStatus] = enum_column(
        DocumentStatus, nullable=False, default=DocumentStatus.VALID
    )

    # في حالة بدل الفاقد: الوثيقة التي حلّت هذه محلّها
    replaces_document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("documents.id")
    )
    scan_path: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)

    person: Mapped[Person] = relationship(back_populates="documents")
    replaces: Mapped[Document | None] = relationship(remote_side="Document.id")

    @property
    def is_expired(self) -> bool:
        """هل انتهت صلاحية الوثيقة؟"""
        return self.expiry_date is not None and self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> int | None:
        """عدد الأيام المتبقية قبل الانتهاء — سالب إذا انتهت."""
        if self.expiry_date is None:
            return None
        return (self.expiry_date - date.today()).days

    def __repr__(self) -> str:
        return f"<Document {self.document_type.value} {self.document_number}>"
