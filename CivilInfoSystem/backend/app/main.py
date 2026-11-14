"""نقطة تشغيل نظام المعلومات المدنية الشامل.

التشغيل:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import auth as auth_routes
from app.api.v1 import documents as document_routes
from app.api.v1 import persons as person_routes
from app.api.v1 import vital as vital_routes
from app.config import settings
from app.core.rate_limit import limiter, rate_limit_handler
from app.database import (
    check_arabic_search_support,
    check_connection,
    mask_database_url,
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """دورة حياة التطبيق — فحص الاتصال عند الإقلاع."""
    logger.info("بدء تشغيل %s الإصدار %s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("البيئة: %s", settings.ENVIRONMENT)
    logger.info("قاعدة البيانات: %s", mask_database_url(settings.DATABASE_URL))

    if not check_connection():
        logger.error("تعذّر الاتصال بقاعدة البيانات — تحقق من DATABASE_URL")
    else:
        logger.info("تم الاتصال بقاعدة البيانات بنجاح")

        # عطل صامت لو لم يُفحص: البحث عن الأسماء العربية يُرجع لا شيء
        arabic_ok, arabic_msg = check_arabic_search_support()
        if arabic_ok:
            logger.info("البحث العربي: %s", arabic_msg)
        else:
            logger.warning("⚠️  %s", arabic_msg)

    yield

    logger.info("إيقاف تشغيل النظام")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "واجهة برمجية لإدارة السجل المدني والأحوال الشخصية: "
        "الأشخاص، المواليد، الوفيات، الزواج والطلاق، الوثائق، والمعاملات."
    ),
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# -----------------------------------------------------------------------------
# الوسائط (Middleware)
# -----------------------------------------------------------------------------

# محدِّد معدّل الطلبات — يجب ربطه بحالة التطبيق ليعمل المُزيِّن @limiter.limit
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """يضيف ترويسات الأمان لكل استجابة."""
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )

    if settings.FORCE_HTTPS:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


# -----------------------------------------------------------------------------
# معالجات الأخطاء — رسائل عربية دون تسريب أي بيانات شخصية
# -----------------------------------------------------------------------------

# بادئات إنجليزية يضيفها Pydantic أمام رسائل المُتحقِّقات المخصّصة.
# تُحذف حتى لا تظهر كلمة أجنبية في مقدّمة رسالة عربية موجَّهة للمستخدم.
_PYDANTIC_PREFIXES = ("Value error, ", "Assertion failed, ")

# رسائل Pydantic القياسية مقابل ما يُعرض للمستخدم بالعربية
_STANDARD_MESSAGES = {
    "Field required": "هذا الحقل مطلوب",
    "Input should be a valid date": "أدخل تاريخاً صالحاً",
    "Input should be a valid integer": "أدخل رقماً صحيحاً",
    "Input should be a valid number": "أدخل رقماً صالحاً",
    "Input should be a valid string": "أدخل نصاً صالحاً",
}


def _clean_message(message: str) -> str:
    """يحوّل رسالة التحقق إلى نص عربي خالص."""
    for prefix in _PYDANTIC_PREFIXES:
        if message.startswith(prefix):
            return message[len(prefix):]

    if message in _STANDARD_MESSAGES:
        return _STANDARD_MESSAGES[message]

    # رسائل الطول والحدود تُعاد صياغتها بالعربية
    import re

    match = re.match(r"String should have at least (\d+) characters?", message)
    if match:
        return f"يجب ألا يقل الطول عن {match.group(1)} حرفاً"

    match = re.match(r"String should have at most (\d+) characters?", message)
    if match:
        return f"يجب ألا يزيد الطول عن {match.group(1)} حرفاً"

    match = re.match(r"Input should be greater than or equal to (\S+)", message)
    if match:
        return f"القيمة يجب ألا تقل عن {match.group(1)}"

    match = re.match(r"Input should be less than or equal to (\S+)", message)
    if match:
        return f"القيمة يجب ألا تزيد عن {match.group(1)}"

    return message


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    """يحوّل أخطاء التحقق إلى رسائل عربية مفهومة."""
    from app.schemas.common import field_label

    errors = []
    for err in exc.errors():
        raw_name = ".".join(str(part) for part in err["loc"][1:]) or "غير محدد"
        errors.append(
            {
                # يُعرض اسم الحقل بالعربية للمستخدم، ويُرفق المعرّف البرمجي
                # ليتمكّن العميل من إبراز الحقل الصحيح في النموذج
                "الحقل": field_label(raw_name.split(".")[-1]),
                "المعرّف": raw_name,
                "الرسالة": _clean_message(err["msg"]),
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"نجاح": False, "الرسالة": "بيانات غير صالحة", "الأخطاء": errors},
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(_request: Request, exc: SQLAlchemyError):
    """لا يُعرض نص خطأ قاعدة البيانات للمستخدم — يُسجَّل نوعه فقط."""
    logger.error("خطأ في قاعدة البيانات: %s", type(exc).__name__, exc_info=settings.DEBUG)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"نجاح": False, "الرسالة": "حدث خطأ أثناء معالجة الطلب"},
    )


# -----------------------------------------------------------------------------
# نقاط أساسية
# -----------------------------------------------------------------------------

@app.get("/health", tags=["النظام"], summary="فحص سلامة النظام")
async def health_check() -> dict:
    """يتحقق من أن التطبيق وقاعدة البيانات يعملان."""
    db_ok = check_connection()
    arabic_ok, arabic_msg = check_arabic_search_support() if db_ok else (False, "—")

    return {
        "الحالة": "سليم" if db_ok and arabic_ok else "خلل",
        "قاعدة_البيانات": "متصلة" if db_ok else "غير متصلة",
        "البحث_العربي": arabic_msg,
        "الإصدار": settings.APP_VERSION,
    }


@app.get("/", tags=["النظام"], summary="معلومات النظام")
async def root() -> dict:
    return {
        "النظام": settings.APP_NAME,
        "الإصدار": settings.APP_VERSION,
        "التوثيق": "/docs" if not settings.is_production else "غير متاح في الإنتاج",
    }


# -----------------------------------------------------------------------------
# مسارات الإصدار الأول
# -----------------------------------------------------------------------------

app.include_router(auth_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(person_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(vital_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(document_routes.router, prefix=settings.API_V1_PREFIX)


# -----------------------------------------------------------------------------
# واجهة PWA — تُقدَّم من الخادم نفسه على المسار /app
# -----------------------------------------------------------------------------
# تقديم الواجهة والواجهة البرمجية من أصل واحد يُغني عن إعداد CORS وعن خادم
# ثانٍ في التشغيل البسيط. في النشر عبر Docker يتولّى nginx ذلك.
from pathlib import Path as _Path

from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = _Path(__file__).resolve().parents[2] / "frontend"

if FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
