"""الترحيل الأساسي — إنشاء مخطط قاعدة البيانات كاملاً

معرّف الترحيل: 0001_baseline
السابق: لا يوجد

قرار معماري مقصود
------------------
هذا الترحيل ينفّذ ``0001_baseline_schema.sql`` المجاور له، وهو **لقطة
مجمّدة** لبنية قاعدة البيانات لحظة كتابة هذا الترحيل. لا يقرأ
``database/schema.sql`` ولا يُعاد توليده أبداً.

السبب: ملف ``database/schema.sql`` يُولَّد من النماذج فيعكس بنيتها الحالية
دائماً. لو نفّذه هذا الترحيل لاحتوى الأساس أعمدة تضيفها ترحيلات لاحقة،
فيفشل الترحيل 0002 لأنه يحاول إضافة عمود موجود. الترحيل تاريخ لا يُعاد
كتابته؛ والملف المولَّد صورة للحاضر. فلكلٍّ ملفه.

مساران لتهيئة قاعدة بيانات
---------------------------
1. **قاعدة قائمة**:  ``alembic upgrade head``
2. **تثبيت جديد**:   تنفيذ ``database/schema.sql`` ثم ``alembic stamp head``

يتحقق الاختبار ``test_migrations.py`` من أن المسارين ينتجان البنية نفسها.
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SNAPSHOT = Path(__file__).with_name("0001_baseline_schema.sql")


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        if not SCHEMA_SNAPSHOT.is_file():
            raise RuntimeError(f"لم يُعثر على لقطة المخطط: {SCHEMA_SNAPSHOT}")

        sql = SCHEMA_SNAPSHOT.read_text(encoding="utf-8")
        # الملف يحتوي BEGIN/COMMIT، وAlembic يدير المعاملة بنفسه
        sql = sql.replace("BEGIN;", "").replace("COMMIT;", "")
        op.execute(sa.text(sql))
    else:
        # SQLite: تُبنى الجداول من النماذج، لأن اللقطة تستخدم خصائص خاصة
        # بـ PostgreSQL (الامتدادات، وplpgsql، والفهارس الجزئية).
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
