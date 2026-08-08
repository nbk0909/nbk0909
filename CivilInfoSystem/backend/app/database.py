"""الاتصال بقاعدة البيانات وإدارة الجلسات.

طبقة تجريد تسمح بالتبديل بين PostgreSQL و SQLite عبر متغيّر البيئة
DATABASE_URL وحده، دون تعديل أي كود آخر.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# اصطلاح تسمية القيود — يجعل ترحيلات Alembic مستقرة وقابلة للتراجع
# -----------------------------------------------------------------------------
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """الصنف الأساس لكل نماذج SQLAlchemy."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# -----------------------------------------------------------------------------
# بناء المحرّك حسب نوع قاعدة البيانات
# -----------------------------------------------------------------------------

def _build_engine() -> Engine:
    """ينشئ محرّك SQLAlchemy بخيارات مناسبة لكل من SQLite و PostgreSQL."""
    common: dict[str, Any] = {
        "echo": settings.DB_ECHO,
        "future": True,
        # يتحقق من صلاحية الاتصال قبل استخدامه (يمنع أخطاء الاتصالات الميتة)
        "pool_pre_ping": True,
    }

    if settings.is_sqlite:
        # SQLite للتطوير المحلي فقط
        return create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if ":memory:" in settings.DATABASE_URL else None,
            **common,
        )

    # PostgreSQL للإنتاج
    return create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        **common,
    )


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


# -----------------------------------------------------------------------------
# تفعيل خصائص SQLite الناقصة افتراضياً
# -----------------------------------------------------------------------------

if settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        """يفعّل المفاتيح الأجنبية ووضع WAL في SQLite.

        SQLite يتجاهل المفاتيح الأجنبية افتراضياً، وهو ما يكسر سلامة
        البيانات المرجعية إن لم يُفعَّل صراحةً مع كل اتصال.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    # SQLite لا يملك دالة normalize_arabic، فنسجّلها من بايثون
    @event.listens_for(engine, "connect")
    def _register_arabic_normalizer(dbapi_connection, _connection_record) -> None:
        from app.utils.arabic import normalize_arabic

        dbapi_connection.create_function("normalize_arabic", 1, normalize_arabic)


# -----------------------------------------------------------------------------
# تبعية FastAPI للحصول على جلسة قاعدة بيانات
# -----------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """تبعية FastAPI: تفتح جلسة، وتضمن إغلاقها والتراجع عند الخطأ.

    الاستخدام:
        @router.get("/persons")
        def list_persons(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def utcnow() -> datetime:
    """الوقت الحالي بتوقيت UTC مع منطقة زمنية صريحة."""
    return datetime.now(timezone.utc)


def check_connection() -> bool:
    """يفحص الاتصال بقاعدة البيانات — يُستخدم في نقطة /health."""
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        # لا نُسرّب تفاصيل الاتصال في السجلات
        logger.error("فشل الاتصال بقاعدة البيانات: %s", type(exc).__name__)
        return False


def mask_database_url(url: str) -> str:
    """يخفي كلمة المرور من رابط قاعدة البيانات قبل عرضه في السجلات."""
    return re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:***@", url)


def check_arabic_search_support() -> tuple[bool, str]:
    """يتحقق من أن البحث التقريبي يعمل على النص العربي.

    امتداد pg_trgm يقسّم النص إلى ثلاثيات حروف اعتماداً على تصنيف الحروف
    في لغة قاعدة البيانات (lc_ctype). إن أُنشئت القاعدة بلغة C أو POSIX
    فلن يُعدّ أي حرف عربي حرفاً أبجدياً، وسيولّد الامتداد صفر ثلاثيات،
    فيُرجع البحث التقريبي عن الأسماء لا شيء — دون أي رسالة خطأ.

    هذا الفحص يكشف الحالة عند الإقلاع بدل أن تُكتشف كشكوى من مستخدم
    يبحث عن اسم موجود ولا يجده.

    يُرجع: (هل الدعم سليم، رسالة توضيحية)
    """
    from sqlalchemy import text

    if settings.is_sqlite:
        # في SQLite يجري البحث التقريبي في طبقة بايثون، فلا يتأثر باللغة
        return True, "SQLite — البحث التقريبي يُنفَّذ في طبقة التطبيق"

    try:
        with engine.connect() as conn:
            has_trgm = conn.execute(
                text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'pg_trgm'")
            ).scalar()

            if not has_trgm:
                return False, "امتداد pg_trgm غير مثبّت"

            trigram_count = conn.execute(
                text("SELECT array_length(show_trgm('احمد'), 1)")
            ).scalar()

            if not trigram_count:
                ctype = conn.execute(
                    text(
                        "SELECT datctype FROM pg_database "
                        "WHERE datname = current_database()"
                    )
                ).scalar()
                return False, (
                    f"البحث التقريبي عن الأسماء العربية معطّل: لغة قاعدة البيانات "
                    f"({ctype}) لا تصنّف الحروف العربية كحروف أبجدية. "
                    f"أعد إنشاء القاعدة بلغة UTF-8 مثل C.UTF-8"
                )

            return True, f"البحث التقريبي يعمل ({trigram_count} ثلاثيات للاختبار)"

    except Exception as exc:  # noqa: BLE001
        return False, f"تعذّر الفحص: {type(exc).__name__}"
