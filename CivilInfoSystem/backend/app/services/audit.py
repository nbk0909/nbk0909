"""خدمة سجل التدقيق.

كل عملية تمسّ سجلاً مدنياً تُقيَّد هنا: من قام بها، وماذا غيّر، ومن أي جهاز.
السجل للإلحاق فقط — لا يُعدَّل ولا يُحذف منه شيء.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditLog, User

logger = logging.getLogger(__name__)

# حقول لا تُكتب في سجل التدقيق بأي حال، حتى لو تغيّرت قيمتها.
# تسجيل تجزئة كلمة المرور أو سرّ المصادقة الثنائية في سجل يُقرأ من عشرات
# الموظفين يُبطل الغرض من تشفيرها أصلاً.
REDACTED_FIELDS = frozenset(
    {
        "password",
        "password_hash",
        "new_password",
        "current_password",
        "totp_secret",
        "totp_secret_encrypted",
        "token",
        "token_hash",
        "access_token",
        "refresh_token",
        "fingerprint_path",
    }
)

REDACTED_PLACEHOLDER = "***"


def _sanitize(values: dict[str, Any] | None) -> dict[str, Any] | None:
    """يحجب الحقول الحسّاسة ويحوّل القيم إلى صيغة قابلة للتخزين في JSON."""
    if not values:
        return None

    clean: dict[str, Any] = {}
    for key, value in values.items():
        if key in REDACTED_FIELDS:
            clean[key] = REDACTED_PLACEHOLDER
        elif isinstance(value, (str, int, float, bool, type(None))):
            clean[key] = value
        else:
            # التواريخ والمعرّفات والأنواع المعدودة تُخزَّن كنصوص
            clean[key] = str(value)

    return clean


def _valid_ip(value: str | None) -> str | None:
    """يُرجع العنوان إن كان عنوان IP صالحاً، وإلا None.

    عمود ip_address من نوع INET في PostgreSQL، وهو يرفض أي نص ليس عنواناً.
    وترويسة X-Forwarded-For يتحكّم بها العميل تحكّماً كاملاً، فلو مُرِّرت
    كما هي لأمكن لأي طالب أن يُفشل الإدراج في سجل التدقيق بترويسة مشوّهة —
    فيُسقط قيد تدقيقه ويحصل على خطأ 500 في آن واحد.
    """
    if not value:
        return None

    import ipaddress

    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def client_ip(request: Request | None) -> str | None:
    """يستخرج عنوان العميل، مع مراعاة وجود وسيط عكسي أمام التطبيق."""
    if request is None:
        return None

    # X-Forwarded-For يضعه الوسيط العكسي؛ أول عنوان فيه هو العميل الأصلي.
    # لا يُوثق به إلا خلف وسيط مضبوط — وإلا زوّره العميل بنفسه.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        candidate = _valid_ip(forwarded.split(",")[0])
        if candidate:
            return candidate

    return _valid_ip(request.client.host if request.client else None)


def record(
    db: Session,
    *,
    action: AuditAction,
    resource_type: str,
    resource_id: str | uuid.UUID | None = None,
    user: User | None = None,
    username: str | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    request: Request | None = None,
    succeeded: bool = True,
    error_message: str | None = None,
) -> AuditLog:
    """يقيّد عملية في سجل التدقيق.

    لا تُستدعى commit هنا: القيد يُكتب ضمن معاملة العملية نفسها، فإن فشلت
    العملية وتراجعت تراجع معها قيدها — إلا في حالات الفشل التي نريد
    تسجيلها عمداً (محاولة دخول فاشلة مثلاً) فتُلتزم صراحةً من المُستدعي.
    """
    entry = AuditLog(
        user_id=user.id if user else None,
        username=username or (user.username if user else None),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        old_values=_sanitize(old_values),
        new_values=_sanitize(new_values),
        ip_address=client_ip(request),
        user_agent=(request.headers.get("user-agent") if request else None),
        request_path=(str(request.url.path) if request else None),
        succeeded=succeeded,
        error_message=error_message,
    )

    db.add(entry)
    return entry


def record_change(
    db: Session,
    *,
    instance: Any,
    action: AuditAction,
    user: User | None,
    request: Request | None = None,
    tracked_fields: list[str] | None = None,
) -> AuditLog | None:
    """يقيّد تعديلاً على نموذج مع قيمه قبل وبعد.

    يقرأ القيم السابقة من تاريخ الجلسة (SQLAlchemy history)، فلا حاجة
    لتمريرها يدوياً. يُرجع None إن لم يتغيّر شيء فعلياً.
    """
    from sqlalchemy import inspect

    state = inspect(instance)
    old: dict[str, Any] = {}
    new: dict[str, Any] = {}

    for attr in state.mapper.column_attrs:
        name = attr.key
        if tracked_fields is not None and name not in tracked_fields:
            continue

        history = state.attrs[name].history
        if not history.has_changes():
            continue

        old[name] = history.deleted[0] if history.deleted else None
        new[name] = history.added[0] if history.added else None

    if not new:
        return None

    return record(
        db,
        action=action,
        resource_type=instance.__tablename__,
        resource_id=getattr(instance, "id", None),
        user=user,
        old_values=old,
        new_values=new,
        request=request,
    )
