"""إضافة عدّاد جيل الرموز

معرّف الترحيل: 0002_token_generation
السابق: 0001_baseline

كان إبطال رموز الوصول بعد تغيير كلمة المرور يعتمد على مقارنة زمنية مع
password_changed_at. وحقل iat في JWT عدد صحيح من الثواني، فلم تكن المقارنة
قادرة على التمييز بين رمز صدر قبل الإبطال بجزء من الثانية وآخر صدر بعده:
إمّا تبقى نافذة يعيش فيها رمز مسروق حتى انتهاء مدته، أو يُرفض الرمز الجديد
الذي حصل عليه المستخدم للتوّ فلا يستطيع الدخول.

العدّاد يحسم الالتباس: كل رمز يحمل رقم الجيل الذي صدر فيه، وكل إبطال يزيد
جيل المستخدم، فتسقط الرموز القديمة كلها دفعةً واحدة دون أي اعتماد على الوقت.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_token_generation"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_generation",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_generation")
