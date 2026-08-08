"""نموذج سجل التدقيق.

سجل التدقيق للإلحاق فقط (Append-Only): لا يُعدَّل ولا يُحذف منه شيء،
ولذلك لا يحمل أعمدة updated_at أو deleted_at.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import enum_column
from app.models.enums import AuditAction
from app.models.types import GUID, IPAddress, JSONType


class AuditLog(Base):
    """قيد في سجل التدقيق."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True
    )
    # نسخة ثابتة من اسم المستخدم تبقى صالحة حتى لو عُطّل الحساب أو غُيّر اسمه
    username: Mapped[str | None] = mapped_column(String(50))

    action: Mapped[AuditAction] = enum_column(AuditAction, nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(50))

    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSONType())
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONType())

    ip_address: Mapped[str | None] = mapped_column(IPAddress())
    user_agent: Mapped[str | None] = mapped_column(String(300))
    request_path: Mapped[str | None] = mapped_column(String(300))

    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action.value} {self.resource_type}>"
