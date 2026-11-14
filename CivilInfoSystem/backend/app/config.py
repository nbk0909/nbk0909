"""إعدادات النظام — تُقرأ من متغيّرات البيئة أو من ملف .env

كل الإعدادات الحسّاسة (المفاتيح، كلمات المرور) تأتي من البيئة حصراً،
ولا تُكتب في الكود أبداً.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """إعدادات التطبيق."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # عام
    # ------------------------------------------------------------------
    APP_NAME: str = "نظام المعلومات المدنية الشامل"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------
    # قاعدة البيانات
    # ------------------------------------------------------------------
    # PostgreSQL للإنتاج:  postgresql+psycopg://user:pass@host:5432/civil_db
    # SQLite للتطوير:      sqlite:///./civil_dev.db
    DATABASE_URL: str = "sqlite:///./civil_dev.db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE_SECONDS: int = 1800

    # ------------------------------------------------------------------
    # الأمان والمصادقة
    # ------------------------------------------------------------------
    SECRET_KEY: str = Field(
        default="CHANGE-ME-IN-PRODUCTION-USE-A-LONG-RANDOM-STRING",
        description="مفتاح توقيع رموز JWT — يجب تغييره في الإنتاج",
    )
    # مفتاح مستقل لتشفير الحقول الحسّاسة داخل قاعدة البيانات (Fernet key)
    FIELD_ENCRYPTION_KEY: str = Field(
        default="",
        description="مفتاح تشفير الحقول الحسّاسة — يُولَّد بـ Fernet.generate_key()",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # سياسة كلمات المرور وقفل الحساب
    PASSWORD_MIN_LENGTH: int = 10
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15
    SESSION_IDLE_TIMEOUT_MINUTES: int = 20

    # تحديد معدّل الطلبات
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    RATE_LIMIT_SEARCH_PER_MINUTE: int = 30
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 120

    # ------------------------------------------------------------------
    # الشبكة و CORS
    # ------------------------------------------------------------------
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    ALLOWED_HOSTS: list[str] = ["*"]
    FORCE_HTTPS: bool = False  # فعّله في الإنتاج

    # ------------------------------------------------------------------
    # الملفات المرفوعة
    # ------------------------------------------------------------------
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_UPLOAD_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png", ".pdf"]

    # ------------------------------------------------------------------
    # التوطين
    # ------------------------------------------------------------------
    DEFAULT_LOCALE: str = "ar"
    TIMEZONE: str = "Asia/Baghdad"
    DEFAULT_NUMERALS: Literal["arabic", "latin"] = "latin"

    # ------------------------------------------------------------------
    # النسخ الاحتياطي
    # ------------------------------------------------------------------
    BACKUP_DIR: str = "./backups"
    BACKUP_RETENTION_DAYS: int = 30

    # ------------------------------------------------------------------
    # التحقق من الإعدادات
    # ------------------------------------------------------------------

    @field_validator("SECRET_KEY")
    @classmethod
    def _validate_secret_key(cls, v: str, info) -> str:
        """يمنع تشغيل الإنتاج بالمفتاح الافتراضي."""
        env = (info.data or {}).get("ENVIRONMENT", "development")
        if env == "production" and "CHANGE-ME" in v:
            raise ValueError(
                "يجب ضبط SECRET_KEY بقيمة عشوائية طويلة قبل التشغيل في بيئة الإنتاج"
            )
        if len(v) < 32:
            raise ValueError("طول SECRET_KEY يجب ألا يقل عن 32 حرفاً")
        return v

    @property
    def is_sqlite(self) -> bool:
        """هل قاعدة البيانات الحالية SQLite؟ (يغيّر بعض خيارات المحرّك)"""
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """يُرجع كائن الإعدادات (مُخزَّن مؤقتاً — يُقرأ مرة واحدة فقط)."""
    return Settings()


settings = get_settings()
