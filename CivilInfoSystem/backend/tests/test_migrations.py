"""اختبارات الترحيلات وتطابق مساري التهيئة.

يتحقق من أن الطريقين إلى قاعدة بيانات جاهزة ينتهيان إلى البنية نفسها:

    1. سلسلة الترحيلات:  alembic upgrade head
    2. المخطط المولَّد:   psql -f database/schema.sql  ثم  alembic stamp head

اختلافهما يعني أن قاعدة قائمة تُرقّى ستختلف عن قاعدة تُثبَّت من جديد،
وهو انحراف لا يظهر إلا متأخراً وفي الإنتاج.

يتطلّب PostgreSQL:
    TEST_DATABASE_URL=postgresql+psycopg://... pytest tests/test_migrations.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

BACKEND = Path(__file__).resolve().parents[1]
SCHEMA_FILE = BACKEND.parent / "database" / "schema.sql"

TEST_URL = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_URL.startswith("postgresql"),
    reason="يتطلّب TEST_DATABASE_URL موجّهاً إلى PostgreSQL",
)


def _reset_schema(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))


def _run_alembic(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": TEST_URL}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )


def _describe_schema(engine) -> dict[str, list]:
    """يلتقط بنية قاعدة البيانات بصورة قابلة للمقارنة."""
    with engine.connect() as conn:
        columns = conn.execute(
            text(
                """
                SELECT table_name, column_name, data_type, is_nullable
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name <> 'alembic_version'
                 ORDER BY table_name, column_name
                """
            )
        ).all()

        indexes = conn.execute(
            text(
                """
                SELECT tablename, indexname, indexdef
                  FROM pg_indexes
                 WHERE schemaname = 'public'
                   AND tablename <> 'alembic_version'
                 ORDER BY tablename, indexname
                """
            )
        ).all()

        constraints = conn.execute(
            text(
                """
                SELECT conrelid::regclass::text AS tbl, conname, pg_get_constraintdef(oid)
                  FROM pg_constraint
                 WHERE connamespace = 'public'::regnamespace
                   -- جدول alembic_version من صنع Alembic لا من المخطط،
                   -- فوجوده في مسار الترحيلات دون الآخر فرق متوقَّع
                   AND conrelid::regclass::text <> 'alembic_version'
                 ORDER BY 1, 2
                """
            )
        ).all()

    return {
        "columns": [tuple(r) for r in columns],
        "indexes": [tuple(r) for r in indexes],
        "constraints": [tuple(r) for r in constraints],
    }


@pytest.fixture
def pg_engine():
    engine = create_engine(TEST_URL)
    yield engine
    engine.dispose()


def test_upgrade_then_downgrade_is_clean(pg_engine):
    """دورة ترقية ثم تراجع كاملة تعمل دون خطأ."""
    _reset_schema(pg_engine)

    up = _run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr

    down = _run_alembic("downgrade", "base")
    assert down.returncode == 0, down.stderr


def test_migration_chain_applies_fully(pg_engine):
    """كل الترحيلات تُطبَّق ويصل الرأس إلى آخرها."""
    _reset_schema(pg_engine)

    result = _run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr

    with pg_engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    heads = _run_alembic("heads")
    assert version in heads.stdout


def test_no_drift_between_models_and_migrations(pg_engine):
    """بعد الترقية لا يجد Alembic أي فرق بين النماذج وقاعدة البيانات."""
    _reset_schema(pg_engine)
    _run_alembic("upgrade", "head")

    result = _run_alembic("check")
    assert result.returncode == 0, (
        "يوجد انحراف بين النماذج والترحيلات:\n" + result.stdout + result.stderr
    )


def test_generated_schema_matches_migration_chain(pg_engine):
    """المخطط المولَّد وسلسلة الترحيلات ينتجان البنية نفسها.

    هذا هو الاختبار الذي يمنع الانحراف فعلياً: لو أضاف أحدهم عموداً في
    النماذج دون ترحيل مقابل، اختلف المساران وفشل هنا.
    """
    # المسار الأول: سلسلة الترحيلات
    _reset_schema(pg_engine)
    result = _run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr
    via_migrations = _describe_schema(pg_engine)

    # المسار الثاني: المخطط المولَّد
    _reset_schema(pg_engine)
    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with pg_engine.begin() as conn:
        conn.execute(text(schema_sql.replace("BEGIN;", "").replace("COMMIT;", "")))
    via_schema_file = _describe_schema(pg_engine)

    assert via_migrations["columns"] == via_schema_file["columns"], (
        "اختلاف في الأعمدة بين الترحيلات والمخطط المولَّد"
    )
    assert via_migrations["indexes"] == via_schema_file["indexes"], (
        "اختلاف في الفهارس بين الترحيلات والمخطط المولَّد"
    )
    assert via_migrations["constraints"] == via_schema_file["constraints"], (
        "اختلاف في القيود بين الترحيلات والمخطط المولَّد"
    )


def test_schema_file_is_current():
    """ملف schema.sql الموجود مطابق لما يولّده السكربت من النماذج الحالية.

    يمنع نسيان إعادة التوليد بعد تعديل النماذج. المقارنة على المحتوى لا
    على حالة git، فيصحّ الاختبار قبل الإيداع وبعده.
    """
    before = SCHEMA_FILE.read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "scripts.generate_schema"],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": "sqlite:///:memory:"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    after = SCHEMA_FILE.read_text(encoding="utf-8")
    assert before == after, (
        "ملف database/schema.sql ليس محدّثاً بالنسبة للنماذج. أعد التوليد:\n"
        "  cd backend && python -m scripts.generate_schema"
    )
