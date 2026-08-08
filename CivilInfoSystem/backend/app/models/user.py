"""نماذج المستخدمين والأدوار والصلاحيات (RBAC)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Table,
    Column,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import GUID, IPAddress

# ---------------------------------------------------------------------------
# جداول الربط
# ---------------------------------------------------------------------------

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("granted_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True),
    Column("assigned_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("assigned_by", GUID(), ForeignKey("users.id"), nullable=True),
)


# ---------------------------------------------------------------------------
# الأدوار والصلاحيات
# ---------------------------------------------------------------------------

class Permission(Base):
    """صلاحية دقيقة على مورد معيّن (مثال: persons.create)."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions, back_populates="permissions"
    )

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class Role(Base, TimestampMixin, SoftDeleteMixin):
    """دور وظيفي يجمع مجموعة صلاحيات."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    description_ar: Mapped[str | None] = mapped_column(String(500))
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )
    # جدول user_roles يشير إلى users بمفتاحين (user_id و assigned_by)،
    # فيلزم تحديد شرط الوصل صراحةً على الطرفين
    users: Mapped[list[User]] = relationship(
        secondary=user_roles,
        back_populates="roles",
        primaryjoin="Role.id == user_roles.c.role_id",
        secondaryjoin="User.id == user_roles.c.user_id",
    )

    def __repr__(self) -> str:
        return f"<Role {self.code}>"


# ---------------------------------------------------------------------------
# المستخدمون
# ---------------------------------------------------------------------------

class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """مستخدم النظام."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("failed_login_attempts >= 0", name="failed_attempts"),
    )

    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))

    # نطاق عمل الموظف — يقيّد ما يراه من سجلات
    governorate_id: Mapped[int | None] = mapped_column(ForeignKey("governorates.id"))

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # المصادقة الثنائية — السر مُشفَّر في قاعدة البيانات
    totp_secret_encrypted: Mapped[str | None] = mapped_column(String(500))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # حماية من محاولات الدخول المتكررة
    failed_login_attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
        primaryjoin="User.id == user_roles.c.user_id",
        secondaryjoin="Role.id == user_roles.c.role_id",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------

    @property
    def is_locked(self) -> bool:
        """هل الحساب مقفل حالياً بسبب محاولات دخول فاشلة؟"""
        if self.locked_until is None:
            return False
        return self.locked_until > datetime.now(self.locked_until.tzinfo)

    def has_permission(self, permission_code: str) -> bool:
        """يتحقق من امتلاك المستخدم صلاحية معيّنة عبر أي من أدواره."""
        return any(
            perm.code == permission_code
            for role in self.roles
            if role.deleted_at is None
            for perm in role.permissions
        )

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class RefreshToken(Base, UUIDPrimaryKeyMixin):
    """رمز تحديث الجلسة — يُخزَّن مُجزّأً لا نصاً صريحاً."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip_address: Mapped[str | None] = mapped_column(IPAddress())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        if self.revoked_at is not None:
            return False
        return self.expires_at > datetime.now(self.expires_at.tzinfo)
