"""خدمة المصادقة: الدخول، تدوير الرموز، قفل الحساب، المصادقة الثنائية."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.core.encryption import decrypt_field, encrypt_field, hash_token
from app.core.security import (
    check_password_policy,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.core.tokens import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.totp import verify_totp
from app.models import AuditAction, RefreshToken, User
from app.services import audit
from app.utils.dates import ensure_utc

logger = logging.getLogger(__name__)

# تجزئة وهمية تُقارن بها كلمة المرور عند عدم وجود المستخدم، لتستغرق
# المحاولة الفاشلة الزمن نفسه سواء كان الاسم موجوداً أم لا. بدونها يستطيع
# المهاجم استنتاج أسماء المستخدمين الصحيحة من فارق زمن الاستجابة وحده.
_DUMMY_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEe.9pWa5YyIzGDPYxOEsAe6dJDXPq4Vf6."


class AuthError(Exception):
    """فشل المصادقة — الرسالة موجّهة للمستخدم النهائي."""

    def __init__(self, message: str, *, code: str = "auth_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass
class TokenPair:
    """رمزا الوصول والتحديث مع بيانات الجلسة."""

    access_token: str
    refresh_token: str
    expires_at: datetime
    user: User
    must_change_password: bool


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# قفل الحساب
# ---------------------------------------------------------------------------

def _register_failed_attempt(db: Session, user: User) -> None:
    """يزيد عدّاد المحاولات الفاشلة ويقفل الحساب عند بلوغ الحد."""
    user.failed_login_attempts += 1

    if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = _now() + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
        logger.warning(
            "قُفل الحساب %s بعد %d محاولات فاشلة",
            user.username,
            user.failed_login_attempts,
        )


def _clear_failed_attempts(user: User) -> None:
    """يصفّر العدّاد بعد دخول ناجح."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = _now()


# ---------------------------------------------------------------------------
# الدخول
# ---------------------------------------------------------------------------

def authenticate(
    db: Session,
    *,
    username: str,
    password: str,
    totp_code: str | None = None,
    request: Request | None = None,
) -> TokenPair:
    """يتحقق من بيانات الدخول ويُصدر رمزَي الوصول والتحديث.

    كل مسارات الفشل تُرجع الرسالة العامة نفسها: كشف السبب الدقيق
    ("المستخدم غير موجود" مقابل "كلمة المرور خاطئة") يمنح المهاجم وسيلة
    لحصر أسماء المستخدمين الصحيحة.
    """
    generic_error = AuthError("اسم المستخدم أو كلمة المرور غير صحيحة")

    user = db.scalar(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )

    # مقارنة وهمية تُوحّد زمن الاستجابة حين لا يوجد المستخدم
    if user is None:
        verify_password(password, _DUMMY_HASH)
        audit.record(
            db,
            action=AuditAction.FAILED_ATTEMPT,
            resource_type="users",
            username=username,
            request=request,
            succeeded=False,
            error_message="اسم مستخدم غير موجود",
        )
        db.commit()
        raise generic_error

    # الحساب المقفل: تُرفض المحاولة دون فحص كلمة المرور
    if user.is_locked:
        remaining = int((ensure_utc(user.locked_until) - _now()).total_seconds() / 60) + 1
        audit.record(
            db,
            action=AuditAction.FAILED_ATTEMPT,
            resource_type="users",
            resource_id=user.id,
            user=user,
            request=request,
            succeeded=False,
            error_message="محاولة دخول على حساب مقفل",
        )
        db.commit()
        raise AuthError(
            f"الحساب مقفل مؤقتاً بسبب محاولات دخول متكررة. "
            f"أعد المحاولة بعد {remaining} دقيقة",
            code="account_locked",
        )

    if not user.is_active:
        audit.record(
            db,
            action=AuditAction.FAILED_ATTEMPT,
            resource_type="users",
            resource_id=user.id,
            user=user,
            request=request,
            succeeded=False,
            error_message="محاولة دخول على حساب معطّل",
        )
        db.commit()
        raise AuthError("الحساب معطّل. راجع مدير النظام", code="account_disabled")

    if not verify_password(password, user.password_hash):
        _register_failed_attempt(db, user)
        audit.record(
            db,
            action=AuditAction.FAILED_ATTEMPT,
            resource_type="users",
            resource_id=user.id,
            user=user,
            request=request,
            succeeded=False,
            error_message="كلمة مرور خاطئة",
        )
        db.commit()
        raise generic_error

    # المصادقة الثنائية
    if user.totp_enabled:
        if not totp_code:
            raise AuthError("مطلوب رمز المصادقة الثنائية", code="totp_required")

        secret = decrypt_field(user.totp_secret_encrypted)
        if not secret or not verify_totp(secret, totp_code):
            _register_failed_attempt(db, user)
            audit.record(
                db,
                action=AuditAction.FAILED_ATTEMPT,
                resource_type="users",
                resource_id=user.id,
                user=user,
                request=request,
                succeeded=False,
                error_message="رمز مصادقة ثنائية خاطئ",
            )
            db.commit()
            raise AuthError("رمز المصادقة الثنائية غير صحيح", code="totp_invalid")

    # نجح الدخول
    _clear_failed_attempts(user)

    # ترقية التجزئة إن كانت بمعايير أقدم — دون إزعاج المستخدم
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    pair = _issue_token_pair(db, user, request=request)

    audit.record(
        db,
        action=AuditAction.LOGIN,
        resource_type="users",
        resource_id=user.id,
        user=user,
        request=request,
    )
    db.commit()

    return pair


def _issue_token_pair(
    db: Session, user: User, *, request: Request | None = None
) -> TokenPair:
    """يُصدر رمزَي وصول وتحديث ويخزّن رمز التحديث مجزّأً."""
    access_token, expires_at = create_access_token(
        user.id, user.username, generation=user.token_generation
    )
    refresh_raw, refresh_expires = create_refresh_token(user.id, user.username)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_raw),
            expires_at=refresh_expires,
            user_agent=(request.headers.get("user-agent") if request else None),
            ip_address=audit.client_ip(request),
        )
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_raw,
        expires_at=expires_at,
        user=user,
        must_change_password=user.must_change_password,
    )


# ---------------------------------------------------------------------------
# تدوير رمز التحديث
# ---------------------------------------------------------------------------

def refresh_tokens(
    db: Session, *, refresh_token: str, request: Request | None = None
) -> TokenPair:
    """يستبدل رمز تحديث صالح بزوج رموز جديد.

    التدوير إلزامي: الرمز القديم يُبطَل فور استعماله. وإذا قُدّم رمز مُبطَل
    من قبل، فهذا مؤشّر سرقة — لأن الرمز الشرعي استُعمل مرة وأُبطل، فمن يقدّمه
    ثانيةً إمّا نسخة مسروقة أو المستخدم الأصلي بعد سرقة رمزه. في الحالتين
    تُبطَل كل جلسات المستخدم احتياطاً.
    """
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise AuthError(str(exc), code="invalid_refresh") from exc

    token_hash = hash_token(refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    if stored is None:
        raise AuthError("رمز التحديث غير معروف", code="invalid_refresh")

    if stored.revoked_at is not None:
        # إعادة استعمال رمز مُبطَل — تُبطَل كل الجلسات
        revoke_all_sessions(db, stored.user_id)
        audit.record(
            db,
            action=AuditAction.FAILED_ATTEMPT,
            resource_type="refresh_tokens",
            resource_id=stored.id,
            username=payload.username,
            request=request,
            succeeded=False,
            error_message="إعادة استعمال رمز تحديث مُبطَل — أُبطلت كل الجلسات",
        )
        db.commit()
        logger.warning(
            "اكتُشفت إعادة استعمال رمز تحديث للمستخدم %s — أُبطلت كل جلساته",
            payload.username,
        )
        raise AuthError(
            "انتهت صلاحية الجلسة. سجّل الدخول من جديد", code="token_reuse"
        )

    if not stored.is_valid:
        raise AuthError("انتهت صلاحية الجلسة", code="expired_refresh")

    user = db.get(User, stored.user_id)
    if user is None or user.deleted_at is not None or not user.is_active:
        raise AuthError("الحساب غير متاح", code="account_unavailable")

    # إبطال الرمز المستعمل قبل إصدار البديل
    stored.revoked_at = _now()
    pair = _issue_token_pair(db, user, request=request)
    db.commit()

    return pair


# ---------------------------------------------------------------------------
# الخروج
# ---------------------------------------------------------------------------

def logout(
    db: Session,
    *,
    user: User,
    refresh_token: str | None = None,
    request: Request | None = None,
) -> None:
    """ينهي الجلسة الحالية بإبطال رمز التحديث المرافق."""
    if refresh_token:
        stored = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(refresh_token),
                RefreshToken.user_id == user.id,
            )
        )
        if stored and stored.revoked_at is None:
            stored.revoked_at = _now()

    audit.record(
        db,
        action=AuditAction.LOGOUT,
        resource_type="users",
        resource_id=user.id,
        user=user,
        request=request,
    )
    db.commit()


def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> int:
    """يُبطل كل جلسات المستخدم: رموز التحديث ورموز الوصول معاً.

    إبطال رموز التحديث وحدها لا يكفي — رمز الوصول يظل صالحاً حتى انتهاء
    مدته (نصف ساعة افتراضياً) لأنه لا يُراجَع في قاعدة البيانات. ضبط
    زيادة عدّاد token_generation هي ما يُنهي رموز الوصول القائمة فوراً.

    يُرجع عدد رموز التحديث التي أُبطلت.
    """
    # تثبيت أي تعديلات معلّقة على الكائنات قبل التحديث المباشر: عبارات
    # UPDATE تتجاوز الجلسة، فلو بقيت تعديلات في الذاكرة لضاعت عند مزامنة
    # الكائن مع قاعدة البيانات بعد قليل (وهو ما كان يُسقط كلمة المرور
    # الجديدة عند تغييرها، لأن التغيير والإبطال يقعان في العملية نفسها).
    db.flush()

    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    db.execute(
        update(User)
        .where(User.id == user_id)
        .values(token_generation=User.token_generation + 1)
    )

    # الكائن في الجلسة ما زال يحمل الجيل القديم بعد تحديث مباشر بـ UPDATE
    tracked = db.get(User, user_id)
    if tracked is not None:
        db.refresh(tracked, attribute_names=["token_generation"])

    return result.rowcount or 0


def purge_expired_tokens(db: Session) -> int:
    """يحذف رموز التحديث المنتهية من قاعدة البيانات.

    هذه ليست سجلات مدنية بل بيانات جلسات، فيصحّ حذفها فعلياً — أثرها
    محفوظ في سجل التدقيق على أي حال.
    """
    from sqlalchemy import delete

    result = db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < _now())
    )
    db.commit()
    return result.rowcount or 0


# ---------------------------------------------------------------------------
# كلمة المرور
# ---------------------------------------------------------------------------

def change_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
    request: Request | None = None,
) -> None:
    """يغيّر كلمة مرور المستخدم بعد التحقق من الحالية."""
    if not verify_password(current_password, user.password_hash):
        audit.record(
            db,
            action=AuditAction.FAILED_ATTEMPT,
            resource_type="users",
            resource_id=user.id,
            user=user,
            request=request,
            succeeded=False,
            error_message="كلمة مرور حالية خاطئة عند محاولة التغيير",
        )
        db.commit()
        raise AuthError("كلمة المرور الحالية غير صحيحة", code="wrong_password")

    if verify_password(new_password, user.password_hash):
        raise AuthError(
            "كلمة المرور الجديدة يجب أن تختلف عن الحالية", code="password_reused"
        )

    problems = check_password_policy(new_password)
    if problems:
        raise AuthError(" • ".join(problems), code="weak_password")

    user.password_hash = hash_password(new_password)
    user.password_changed_at = _now()
    user.must_change_password = False

    # تغيير كلمة المرور يُنهي كل الجلسات الأخرى: لو كان السبب تسريباً،
    # فإبقاء جلسات المهاجم مفتوحة يُفرغ التغيير من معناه.
    revoked = revoke_all_sessions(db, user.id)

    audit.record(
        db,
        action=AuditAction.UPDATE,
        resource_type="users",
        resource_id=user.id,
        user=user,
        new_values={"password_hash": "***", "sessions_revoked": revoked},
        request=request,
    )
    db.commit()


# ---------------------------------------------------------------------------
# المصادقة الثنائية
# ---------------------------------------------------------------------------

def begin_totp_setup(db: Session, *, user: User) -> tuple[str, str]:
    """يبدأ تفعيل المصادقة الثنائية.

    يُرجع: (السرّ، رمز QR كـ data URI). السرّ يُخزَّن مشفّراً لكن التفعيل
    لا يكتمل إلا بعد تأكيد المستخدم برمز صحيح — فلا يُقفل على نفسه خارج
    الحساب إن أخطأ في مسح الرمز.
    """
    from app.core.totp import generate_qr_data_uri, generate_secret

    secret = generate_secret()
    user.totp_secret_encrypted = encrypt_field(secret)
    user.totp_enabled = False
    db.commit()

    return secret, generate_qr_data_uri(secret, user.username)


def confirm_totp_setup(
    db: Session, *, user: User, code: str, request: Request | None = None
) -> None:
    """يؤكّد تفعيل المصادقة الثنائية بعد التحقق من رمز صحيح."""
    secret = decrypt_field(user.totp_secret_encrypted)

    if not secret:
        raise AuthError("لم يبدأ تفعيل المصادقة الثنائية", code="totp_not_started")

    if not verify_totp(secret, code):
        raise AuthError("الرمز غير صحيح. تأكّد من ضبط ساعة جهازك", code="totp_invalid")

    user.totp_enabled = True
    audit.record(
        db,
        action=AuditAction.UPDATE,
        resource_type="users",
        resource_id=user.id,
        user=user,
        new_values={"totp_enabled": True},
        request=request,
    )
    db.commit()


def disable_totp(
    db: Session, *, user: User, password: str, request: Request | None = None
) -> None:
    """يعطّل المصادقة الثنائية — يتطلّب تأكيد كلمة المرور."""
    if not verify_password(password, user.password_hash):
        raise AuthError("كلمة المرور غير صحيحة", code="wrong_password")

    user.totp_enabled = False
    user.totp_secret_encrypted = None

    audit.record(
        db,
        action=AuditAction.UPDATE,
        resource_type="users",
        resource_id=user.id,
        user=user,
        new_values={"totp_enabled": False},
        request=request,
    )
    db.commit()
