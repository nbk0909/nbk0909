"""تهيئة بيئة الاختبارات."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# يجب ضبط البيئة قبل استيراد أي وحدة من التطبيق، لأن الإعدادات تُقرأ
# مرة واحدة عند أول استيراد وتُخزَّن مؤقتاً
os.environ.setdefault("SECRET_KEY", "test-secret-key-long-enough-for-validation-purposes")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("MAX_FAILED_LOGIN_ATTEMPTS", "5")
os.environ.setdefault("RATE_LIMIT_LOGIN_PER_MINUTE", "1000")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Governorate, Permission, Role, User
from app.utils.arabic import normalize_arabic


@pytest.fixture(scope="function")
def engine():
    """محرّك اختبار — SQLite في الذاكرة افتراضياً.

    لتشغيل الاختبارات على PostgreSQL (يكشف ما تخفيه SQLite من قيود:
    الأنواع المعدودة، والفهارس الجزئية، والمُشغّلات):

        TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost/test_db \\
            pytest tests/
    """
    test_url = os.environ.get("TEST_DATABASE_URL")

    if test_url:
        eng = create_engine(test_url, poolclass=StaticPool)
        # مخطط نظيف لكل اختبار — أسرع وأضمن من إسقاط 22 جدولاً بالترتيب
        with eng.begin() as conn:
            conn.execute(sa_text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(sa_text("CREATE SCHEMA public"))
            conn.execute(sa_text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
        Base.metadata.create_all(bind=eng)

        # الجداول وحدها لا تكفي: دالة تطبيع النص العربي والمُشغّلات والعروض
        # مكتوبة في sql_objects.sql. بدونها تفشل استعلامات البحث، وتُختبر
        # قاعدة لا تشبه قاعدة الإنتاج.
        sql_objects = (
            Path(__file__).resolve().parents[2] / "database" / "sql_objects.sql"
        )
        with eng.begin() as conn:
            conn.execute(sa_text(sql_objects.read_text(encoding="utf-8")))

        yield eng
        eng.dispose()
        return

    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _setup(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
        dbapi_conn.create_function("normalize_arabic", 1, normalize_arabic)

    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture
def db(engine) -> Session:
    """جلسة قاعدة بيانات للاختبار."""
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def client(engine, db) -> TestClient:
    """عميل HTTP يشارك الاختبار قاعدة البيانات نفسها."""
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# بيانات أساسية
# ---------------------------------------------------------------------------

PASSWORD = "TestPass@2026"


@pytest.fixture
def governorate(db) -> Governorate:
    gov = Governorate(code="10", name_ar="بغداد", name_en="Baghdad")
    db.add(gov)
    db.commit()
    return gov


@pytest.fixture
def permissions(db) -> dict[str, Permission]:
    """صلاحيات مختصرة تكفي للاختبارات."""
    perms = {}
    for resource in (
        "persons",
        "births",
        "deaths",
        "marriages",
        "divorces",
        "documents",
        "family_cards",
        "requests",
        "reports",
        "users",
        "audit",
    ):
        for action in ("create", "read", "update", "delete", "approve"):
            code = f"{resource}.{action}"
            p = Permission(
                code=code, resource=resource, action=action, name_ar=code
            )
            db.add(p)
            perms[code] = p
    db.commit()
    return perms


@pytest.fixture
def roles(db, permissions) -> dict[str, Role]:
    """دورا مدير النظام والمستعلم."""
    admin = Role(code="admin", name_ar="مدير النظام", is_system=True)
    admin.permissions = list(permissions.values())

    viewer = Role(code="viewer", name_ar="مستعلم", is_system=True)
    viewer.permissions = [p for c, p in permissions.items() if c.endswith(".read")]

    # موظف الإدخال: ينشئ ويقرأ ويعدّل، ولا يحذف ولا يعتمد
    clerk = Role(code="clerk", name_ar="موظف إدخال", is_system=True)
    clerk.permissions = [
        p
        for c, p in permissions.items()
        if not c.endswith((".delete", ".approve")) and not c.startswith(("users.", "audit."))
    ]

    # مدير السجل: كصلاحيات الموظف مع الاعتماد
    registrar = Role(code="registrar", name_ar="مدير سجل", is_system=True)
    registrar.permissions = [
        p
        for c, p in permissions.items()
        if not c.endswith(".delete") and not c.startswith(("users.", "audit."))
    ]

    db.add_all([admin, viewer, clerk, registrar])
    db.commit()
    return {
        "admin": admin,
        "viewer": viewer,
        "clerk": clerk,
        "registrar": registrar,
    }


def _make_user(db, roles, *, username, role, **kwargs) -> User:
    user = User(
        username=username,
        email=f"{username}@civil.gov",
        password_hash=hash_password(PASSWORD),
        full_name_ar=f"مستخدم {username}",
        must_change_password=kwargs.pop("must_change_password", False),
        **kwargs,
    )
    user.roles = [roles[role]]
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def admin_user(db, roles) -> User:
    return _make_user(db, roles, username="admin", role="admin")


@pytest.fixture
def viewer_user(db, roles) -> User:
    return _make_user(db, roles, username="viewer", role="viewer")


@pytest.fixture
def clerk_user(db, roles) -> User:
    return _make_user(db, roles, username="clerk", role="clerk")


@pytest.fixture
def registrar_user(db, roles) -> User:
    return _make_user(db, roles, username="registrar", role="registrar")


@pytest.fixture
def new_user(db, roles) -> User:
    """مستخدم مُلزَم بتغيير كلمة مروره."""
    return _make_user(
        db, roles, username="newbie", role="viewer", must_change_password=True
    )


def login(client, username: str, password: str = PASSWORD, **extra) -> dict:
    """يسجّل الدخول ويُرجع جسم الاستجابة."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password, **extra},
    )
    return response.json()


def auth_headers(client, username: str, password: str = PASSWORD) -> dict[str, str]:
    """يُرجع ترويسة الاعتماد لمستخدم."""
    body = login(client, username, password)
    return {"Authorization": f"Bearer {body['access_token']}"}
