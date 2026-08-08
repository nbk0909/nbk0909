"""تحديد معدّل الطلبات.

الغرض الأساسي حماية نقطة الدخول من التخمين الآلي، ونقطة البحث من الاستنزاف
(البحث في السجل المدني عملية مكلفة، وسحب السجل كاملاً عبر استعلامات متتابعة
تسريب بيانات وإن كان كل استعلام منفرداً مشروعاً).
"""

from __future__ import annotations

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings

logger = logging.getLogger(__name__)


def rate_limit_key(request: Request) -> str:
    """مفتاح التحديد: المستخدم إن كان معروفاً، وإلا عنوان الشبكة.

    الاعتماد على العنوان وحده يعاقب كل من خلف بوّابة مشتركة بخطأ مستخدم
    واحد؛ والاعتماد على المستخدم وحده لا يحمي نقطة الدخول لأن المهاجم
    لم يُصادَق بعد. فيُجمع الاثنان: كلٌّ حسب ما هو متاح.
    """
    user = getattr(request.state, "current_user", None)
    if user is not None:
        return f"user:{user.id}"

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=[f"{settings.RATE_LIMIT_DEFAULT_PER_MINUTE}/minute"],
    # التخزين في الذاكرة يكفي لنسخة واحدة من التطبيق. عند التوسّع إلى عدة
    # نسخ يجب توجيهه إلى Redis وإلا صار الحد فعلياً مضروباً في عدد النسخ.
    storage_uri="memory://",
    strategy="fixed-window",
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """يُرجع رسالة عربية عند تجاوز الحد."""
    logger.warning(
        "تجاوز حد الطلبات: %s على المسار %s", rate_limit_key(request), request.url.path
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "نجاح": False,
            "الرسالة": "تجاوزت الحد المسموح من الطلبات. أعد المحاولة بعد قليل",
        },
        headers={"Retry-After": "60"},
    )


# حدود جاهزة تُستعمل كمُزيّنات على المسارات
LOGIN_LIMIT = f"{settings.RATE_LIMIT_LOGIN_PER_MINUTE}/minute"
SEARCH_LIMIT = f"{settings.RATE_LIMIT_SEARCH_PER_MINUTE}/minute"
