"""الترحيل الأساسي — إنشاء مخطط قاعدة البيانات كاملاً

معرّف الترحيل: 0001_baseline
السابق: لا يوجد

قرار معماري مقصود
------------------
هذا الترحيل لا يُعيد كتابة تعريفات الجداول ببنية Alembic، بل يُنفِّذ ملف
``database/schema.sql`` مباشرةً على PostgreSQL. السبب أن المخطط يحتوي على
دوال ومُشغّلات (Triggers) وفهارس جزئية لا يستطيع ORM التعبير عنها، ولو
كُتب المخطط مرتين — مرة في SQL ومرة في Alembic — لانحرفت النسختان عن
بعضهما مع أول تعديل.

فتكون قاعدة العمل:
  * ``database/schema.sql`` هو المرجع الوحيد للبنية الأولية.
  * الترحيلات اللاحقة (0002 فما بعد) تُكتب ببنية Alembic المعتادة.
  * في SQLite (بيئة التطوير) تُنشأ الجداول من النماذج، لأن الملف يستخدم
    خصائص خاصة بـ PostgreSQL. القواعد التي تفرضها المُشغّلات تُطبَّق عندئذ
    في طبقة الخدمات.
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

# backend/alembic/versions/ -> backend/ -> CivilInfoSystem/
SCHEMA_FILE = Path(__file__).resolve().parents[3] / "database" / "schema.sql"


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        if not SCHEMA_FILE.is_file():
            raise RuntimeError(f"لم يُعثر على ملف المخطط: {SCHEMA_FILE}")

        sql = SCHEMA_FILE.read_text(encoding="utf-8")
        # الملف يحتوي BEGIN/COMMIT، وAlembic يدير المعاملة بنفسه
        sql = sql.replace("BEGIN;", "").replace("COMMIT;", "")
        op.execute(sa.text(sql))
    else:
        # SQLite: تُبنى الجداول من النماذج
        from app.database import Base
        import app.models  # noqa: F401

        Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # حذف المخطط كاملاً ثم إعادة إنشائه — أبسط وأسلم من إسقاط 22 جدولاً
        # بالترتيب الصحيح مع أنواعها ودوالها ومُشغّلاتها.
        op.execute("DROP SCHEMA public CASCADE")
        op.execute("CREATE SCHEMA public")
        # جدول alembic_version يقع داخل المخطط المحذوف، وAlembic سيحذف منه
        # سطر النسخة الحالية بعد انتهاء هذه الدالة، ويتوقّع أن يجد سطراً
        # واحداً بالضبط — فيلزم إعادة إنشاء الجدول وإعادة السطر إليه.
        op.execute(
            "CREATE TABLE alembic_version ("
            "  version_num VARCHAR(32) NOT NULL,"
            "  CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
            ")"
        )
        op.execute(f"INSERT INTO alembic_version (version_num) VALUES ('{revision}')")
    else:
        from app.database import Base
        import app.models  # noqa: F401

        Base.metadata.drop_all(bind=bind)
