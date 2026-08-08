"""يولّد ملف database/schema.sql من نماذج SQLAlchemy.

لماذا يُولَّد الملف ولا يُكتب يدوياً؟
    لو كُتب المخطط مرتين — مرة في النماذج ومرة في SQL — لانحرفت النسختان مع
    أول تعديل، وصار كل توليد تلقائي لترحيل Alembic يقترح إعادة تسمية عشرات
    الفهارس والقيود. بالتوليد يبقى مصدر البنية واحداً هو النماذج، ويبقى
    الملف مرجعاً مقروءاً لمن يريد فحص المخطط أو تهيئة قاعدة يدوياً.

    ما لا تستطيع النماذج التعبير عنه — الامتدادات، ودالة تطبيع النص العربي،
    والمُشغّلات، والعروض — يُقرأ من database/sql_objects.sql ويُلحق كما هو.

التشغيل من مجلد backend:
    python -m scripts.generate_schema
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database import Base
import app.models  # noqa: F401  — يسجّل كل النماذج في الميتاداتا
from app.models.enums import ENUM_TYPE_NAMES

ROOT = Path(__file__).resolve().parents[2]
SQL_OBJECTS = ROOT / "database" / "sql_objects.sql"
OUTPUT = ROOT / "database" / "schema.sql"

DIALECT = postgresql.dialect()

HEADER = """\
-- =============================================================================
--  نظام المعلومات المدنية الشامل — مخطط قاعدة البيانات
--  Civil Information System — Database Schema
--  المحرّك المستهدف: PostgreSQL 15+
-- =============================================================================
--
--  ⚠️  هذا الملف مُولَّد آلياً — لا تعدّله يدوياً.
--      لتغيير بنية الجداول: عدّل النماذج في backend/app/models/
--      لتغيير الدوال والمُشغّلات والعروض: عدّل database/sql_objects.sql
--      ثم أعد التوليد:  cd backend && python -m scripts.generate_schema
--
-- =============================================================================
--  ملاحظات:
--    * الحذف حذف منطقي (Soft Delete) عبر العمود deleted_at.
--      لا تُحذف أي سجلات مدنية حذفاً فعلياً إطلاقاً.
--    * الحقول النصية العربية تُخزَّن مرتين: القيمة الأصلية + قيمة مُطبَّعة
--      (full_name_normalized) تُستخدم في البحث لتجاهل التشكيل وصور الألف.
-- =============================================================================

BEGIN;
"""

FOOTER = """
COMMIT;

-- =============================================================================
--  نهاية المخطط
-- =============================================================================
"""


def render_enum_types() -> str:
    """يولّد CREATE TYPE لكل نوع معدود بقيمه العربية."""
    lines = [
        "",
        "-- ---------------------------------------------------------------------------",
        "--  الأنواع المعدودة",
        "-- ---------------------------------------------------------------------------",
        "",
    ]

    for py_enum, type_name in ENUM_TYPE_NAMES.items():
        values = ", ".join(f"'{member.value}'" for member in py_enum)
        lines.append(f"CREATE TYPE {type_name} AS ENUM ({values});")

    return "\n".join(lines) + "\n"


def render_tables() -> str:
    """يولّد CREATE TABLE و CREATE INDEX بالترتيب الصحيح للاعتماديات."""
    lines = [
        "",
        "-- ---------------------------------------------------------------------------",
        "--  الجداول والفهارس",
        "-- ---------------------------------------------------------------------------",
    ]

    for table in Base.metadata.sorted_tables:
        comment = table.comment or ""
        lines.append("")
        if comment:
            lines.append(f"-- {comment}")

        # create_type=False على أعمدة ENUM يمنع تكرار CREATE TYPE هنا
        ddl = str(CreateTable(table).compile(dialect=DIALECT)).strip()
        lines.append(ddl + ";")

        for index in sorted(table.indexes, key=lambda i: i.name or ""):
            index_ddl = str(CreateIndex(index).compile(dialect=DIALECT)).strip()
            lines.append(index_ddl + ";")

    return "\n".join(lines) + "\n"


def render_sql_objects() -> str:
    """يُلحق الدوال والمُشغّلات والعروض المكتوبة يدوياً."""
    if not SQL_OBJECTS.is_file():
        raise SystemExit(f"لم يُعثر على الملف: {SQL_OBJECTS}")
    return "\n" + SQL_OBJECTS.read_text(encoding="utf-8").rstrip() + "\n"


def build() -> str:
    # الامتدادات أولاً لأن فهرس gin_trgm_ops يعتمد على pg_trgm
    extensions = (
        "\n"
        "-- الامتدادات المطلوبة\n"
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- توليد المعرّفات الفريدة\n'
        'CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- البحث التقريبي في الأسماء\n'
        'CREATE EXTENSION IF NOT EXISTS "unaccent";\n'
    )

    # الترتيب مُلزم: الامتدادات قبل فهرس gin_trgm_ops، والأنواع المعدودة قبل
    # الجداول التي تستعملها، والمُشغّلات بعد الجداول التي تُركَّب عليها.
    return (
        HEADER
        + extensions
        + render_enum_types()
        + render_tables()
        + render_sql_objects()
        + FOOTER
    )


def main() -> int:
    OUTPUT.write_text(build(), encoding="utf-8")
    table_count = len(Base.metadata.tables)
    index_count = sum(len(t.indexes) for t in Base.metadata.tables.values())
    print(f"تم توليد {OUTPUT.relative_to(ROOT)}")
    print(f"  {table_count} جدولاً، {index_count} فهرساً، {len(ENUM_TYPE_NAMES)} نوعاً معدوداً")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
