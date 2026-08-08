"""تجزئة كلمات المرور والتحقق منها.

تُستكمل هذه الوحدة في المرحلة الثالثة برموز JWT والمصادقة الثنائية.

لماذا bcrypt مباشرةً بدل passlib؟
    passlib هي الغلاف الشائع لهذا الغرض، لكن آخر إصدار لها كان عام 2020،
    وهي غير متوافقة مع bcrypt 4.x (تنكسر عند اكتشاف الخلفية لأنها تمرّر
    نصاً أطول من 72 بايت). استخدام bcrypt مباشرةً يتجنّب اعتمادية مهجورة
    ويُبقي الكود أبسط.
"""

from __future__ import annotations

import bcrypt

from app.config import settings

# عامل التكلفة: كل زيادة بمقدار 1 تُضاعف زمن الحساب.
# 12 توازن مقبول بين مقاومة التخمين وزمن الاستجابة (~250 مللي ثانية).
BCRYPT_ROUNDS = 12

# bcrypt يقتطع ما بعد 72 بايت بصمت، فنرفض الأطول صراحةً
MAX_PASSWORD_BYTES = 72


def hash_password(plain_password: str) -> str:
    """يُجزّئ كلمة المرور استعداداً لتخزينها."""
    encoded = plain_password.encode("utf-8")

    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"طول كلمة المرور يتجاوز الحد الأقصى ({MAX_PASSWORD_BYTES} بايت)"
        )

    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """يتحقق من مطابقة كلمة المرور للتجزئة المخزّنة.

    المقارنة داخل checkpw محصّنة ضد هجمات التوقيت (Timing Attacks).
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        # تجزئة تالفة أو بصيغة غير معروفة — تُعامل كفشل تحقق لا كخطأ نظام
        return False


def needs_rehash(password_hash: str) -> bool:
    """هل جُزّئت كلمة المرور بعامل تكلفة أقل من المعتمد حالياً؟

    إن كان كذلك، تُعاد تجزئتها عند أول دخول ناجح دون إزعاج المستخدم.
    """
    try:
        # صيغة التجزئة: $2b$<rounds>$<salt+checksum>
        rounds = int(password_hash.split("$")[2])
        return rounds < BCRYPT_ROUNDS
    except (IndexError, ValueError):
        return True


def check_password_policy(password: str) -> list[str]:
    """يُرجع قائمة مخالفات سياسة كلمات المرور — فارغة تعني القبول."""
    from app.utils.validators import validate_password_strength

    return validate_password_strength(password, settings.PASSWORD_MIN_LENGTH)
