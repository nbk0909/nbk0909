"""يصدّر البيانات التجريبية من قاعدة PostgreSQL إلى database/seed_data.sql.

يُشغَّل بعد ``python -m scripts.seed`` لتحديث ملف SQL المرافق، فيبقى الملف
مطابقاً لما يولّده السكربت ولا يُكتب يدوياً.

التشغيل من مجلد backend:
    python -m scripts.export_seed
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "database" / "seed_data.sql"

HEADER = """\
-- =============================================================================
--  نظام المعلومات المدنية الشامل — بيانات تجريبية
-- =============================================================================
--
--  ⚠️  هذا الملف مُولَّد آلياً من backend/scripts/seed.py — لا تعدّله يدوياً.
--      لإعادة التوليد:
--          cd backend && python -m scripts.seed --reset
--          python -m scripts.export_seed
--
--  المحتوى: 54 شخصاً في أربعة أجيال موزّعين على 6 عائلات مترابطة بالمصاهرة،
--           مع واقعات ميلاد ووفاة وزواج وطلاق متسقة زمنياً.
--
--  ⚠️  كلمات المرور في هذا الملف معروفة وللتجربة فقط:
--          admin      / Admin@2026!
--          registrar  / Registrar@2026!
--      كلا الحسابين مُعلَّم بـ must_change_password.
--      لا تستخدم هذا الملف في بيئة إنتاج بأي حال.
-- =============================================================================

"""


def main() -> int:
    if settings.is_sqlite:
        print(
            "التصدير يتطلّب PostgreSQL. اضبط DATABASE_URL على قاعدة PostgreSQL أولاً.",
            file=sys.stderr,
        )
        return 1

    if shutil.which("pg_dump") is None:
        print("الأمر pg_dump غير متوفّر في مسار النظام.", file=sys.stderr)
        return 1

    # تحويل رابط SQLAlchemy إلى صيغة libpq التي يفهمها pg_dump
    url = urlparse(settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://"))

    result = subprocess.run(
        [
            "pg_dump",
            settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://"),
            "--data-only",
            "--no-owner",
            "--no-privileges",
            # المُشغّلات تُعطَّل أثناء الاستيراد وإلا أعادت تطبيق آثارها
            # (تحديث حالة الوفاة مثلاً) على بيانات مُصدَّرة أصلاً بعد تطبيقها
            "--disable-triggers",
            "--exclude-table=alembic_version",
            "--column-inserts",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"فشل pg_dump: {result.stderr.strip()}", file=sys.stderr)
        return 1

    # حذف أسطر SET وتعليقات pg_dump الفارغة لتقليل الضجيج
    body = "\n".join(
        line
        for line in result.stdout.splitlines()
        if line.strip() != "--"
        and not re.match(r"^(SET |SELECT pg_catalog)", line)
    )

    OUTPUT.write_text(HEADER + body + "\n", encoding="utf-8")

    inserts = body.count("INSERT INTO")
    print(f"تم تصدير {inserts} سطر إدراج إلى {OUTPUT.relative_to(ROOT)}")
    print(f"  قاعدة المصدر: {url.path.lstrip('/')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
