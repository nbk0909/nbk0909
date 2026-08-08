"""مخططات Pydantic لواجهات المصادقة."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# الطلبات
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """بيانات تسجيل الدخول."""

    username: str = Field(
        ..., min_length=3, max_length=50, description="اسم المستخدم"
    )
    password: str = Field(..., min_length=1, max_length=128, description="كلمة المرور")
    totp_code: str | None = Field(
        None, max_length=10, description="رمز المصادقة الثنائية إن كانت مفعّلة"
    )

    @field_validator("username")
    @classmethod
    def _strip_username(cls, v: str) -> str:
        return v.strip().lower()


class RefreshRequest(BaseModel):
    """طلب تجديد رمز الوصول."""

    refresh_token: str = Field(..., description="رمز التحديث")


class LogoutRequest(BaseModel):
    """طلب إنهاء الجلسة."""

    refresh_token: str | None = Field(
        None, description="رمز التحديث المراد إبطاله"
    )


class ChangePasswordRequest(BaseModel):
    """طلب تغيير كلمة المرور."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=10, max_length=72)

    @field_validator("new_password")
    @classmethod
    def _check_byte_length(cls, v: str) -> str:
        # bcrypt يقتطع ما بعد 72 بايت، والحرف العربي يشغل بايتين في UTF-8
        # فكلمة مرور عربية من 40 حرفاً تتجاوز الحد فعلياً
        if len(v.encode("utf-8")) > 72:
            raise ValueError("كلمة المرور طويلة جداً (الحد 72 بايت)")
        return v


class TotpConfirmRequest(BaseModel):
    """تأكيد تفعيل المصادقة الثنائية."""

    code: str = Field(..., min_length=6, max_length=10, description="الرمز من التطبيق")


class TotpDisableRequest(BaseModel):
    """تعطيل المصادقة الثنائية."""

    password: str = Field(..., min_length=1, max_length=128)


# ---------------------------------------------------------------------------
# الاستجابات
# ---------------------------------------------------------------------------

class RoleInfo(BaseModel):
    """معلومات دور."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name_ar: str


class UserInfo(BaseModel):
    """بيانات المستخدم المعروضة بعد الدخول."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name_ar: str
    email: str | None = None
    governorate_id: int | None = None
    totp_enabled: bool
    must_change_password: bool
    last_login_at: datetime | None = None
    roles: list[RoleInfo] = []
    permissions: list[str] = []


class TokenResponse(BaseModel):
    """استجابة الدخول أو التجديد."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    must_change_password: bool
    user: UserInfo


class TotpSetupResponse(BaseModel):
    """بيانات بدء تفعيل المصادقة الثنائية."""

    secret: str = Field(..., description="السرّ — يُعرض مرة واحدة فقط")
    qr_code: str = Field(..., description="رمز QR بصيغة data URI")
    instructions: str = "امسح الرمز بتطبيق مصادقة ثم أكّد بالرمز المعروض"


class MessageResponse(BaseModel):
    """استجابة عامة بنجاح العملية."""

    نجاح: bool = True
    الرسالة: str


def build_user_info(user) -> UserInfo:
    """يبني بيانات المستخدم مع أدواره وصلاحياته المسطّحة."""
    active_roles = [r for r in user.roles if r.deleted_at is None]

    return UserInfo(
        id=user.id,
        username=user.username,
        full_name_ar=user.full_name_ar,
        email=user.email,
        governorate_id=user.governorate_id,
        totp_enabled=user.totp_enabled,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        roles=[RoleInfo(code=r.code, name_ar=r.name_ar) for r in active_roles],
        permissions=sorted(
            {perm.code for role in active_roles for perm in role.permissions}
        ),
    )
