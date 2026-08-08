"""الخلطات (Mixins) المشتركة بين النماذج، ودالة بناء أعمدة الأنواع المعدودة."""

from __future__ import annotations

import enum as _enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.enums import ENUM_TYPE_NAMES
from app.models.types import GUID


def enum_column(py_enum: type[_enum.Enum], **kwargs):
    """يبني عمود ENUM يستخدم القيم العربية لا أسماء الأعضاء.

    بدون values_callable يخزّن SQLAlchemy اسم العضو (MALE) بدل قيمته (ذكر)،
    فلا يطابق نوع ENUM المُعرَّف في مخطط PostgreSQL.
    """
    return mapped_column(
        SAEnum(
            py_enum,
            name=ENUM_TYPE_NAMES[py_enum],
            values_callable=lambda members: [m.value for m in members],
            native_enum=True,
            create_type=False,  # الأنواع تُنشأ في الترحيل الأساسي
        ),
        **kwargs,
    )


class TimestampMixin:
    """أعمدة زمن الإنشاء والتعديل — تُدار من قاعدة البيانات."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """الحذف المنطقي — لا تُحذف السجلات المدنية فعلياً أبداً."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class AuditMixin:
    """من أنشأ السجل ومن عدّله."""

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )


class UUIDPrimaryKeyMixin:
    """مفتاح أساسي من نوع UUID.

    تُفضَّل المعرّفات العشوائية على التسلسلية في السجلات المدنية، لأن
    الأرقام المتسلسلة تكشف حجم السجل وتسمح بتخمين معرّفات سجلات أخرى.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
