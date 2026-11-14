"""تشفير الحقول الحسّاسة داخل قاعدة البيانات.

بعض الحقول لا يكفي تجزئتها (لأننا نحتاج قيمتها الأصلية لاحقاً) ولا يصحّ
تخزينها نصاً صريحاً — مثل سرّ المصادقة الثنائية. تُشفَّر هذه الحقول بمفتاح
مستقل عن مفتاح توقيع الرموز، فتسريب نسخة من قاعدة البيانات وحدها لا يكشفها.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def _get_cipher() -> Fernet:
    """يبني كائن التشفير من مفتاح البيئة.

    إن لم يُضبط FIELD_ENCRYPTION_KEY يُشتقّ مفتاح من SECRET_KEY كحل احتياطي
    للتطوير فقط — ويُرفض ذلك صراحةً في بيئة الإنتاج، لأن استعمال مفتاح واحد
    للتوقيع والتشفير يعني أن تسريبه يكشف الاثنين معاً.
    """
    key = settings.FIELD_ENCRYPTION_KEY.strip()

    if key:
        return Fernet(key.encode())

    if settings.is_production:
        raise RuntimeError(
            "يجب ضبط FIELD_ENCRYPTION_KEY في بيئة الإنتاج. ولّده بالأمر:\n"
            "  python -c \"from cryptography.fernet import Fernet; "
            'print(Fernet.generate_key().decode())"'
        )

    logger.warning(
        "FIELD_ENCRYPTION_KEY غير مضبوط — يُشتقّ مفتاح مؤقت من SECRET_KEY "
        "(مقبول في التطوير فقط)"
    )
    derived = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_field(plaintext: str | None) -> str | None:
    """يشفّر قيمة نصّية استعداداً لتخزينها."""
    if plaintext is None:
        return None
    return _get_cipher().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_field(ciphertext: str | None) -> str | None:
    """يفكّ تشفير قيمة مخزّنة، ويُرجع None إن تعذّر ذلك.

    فشل فكّ التشفير يعني عادةً تغيّر المفتاح أو تلف البيانات؛ يُسجَّل الحدث
    دون كشف النص المشفّر في السجلات.
    """
    if ciphertext is None:
        return None

    try:
        return _get_cipher().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        logger.error("تعذّر فكّ تشفير حقل — تحقّق من FIELD_ENCRYPTION_KEY")
        return None


def hash_token(token: str) -> str:
    """يُجزّئ رمزاً للتخزين والمقارنة.

    رموز التحديث تُخزَّن مجزّأة لا صريحة: من يقرأ قاعدة البيانات لا يستطيع
    انتحال جلسة. SHA-256 كافٍ هنا (بخلاف كلمات المرور) لأن الرمز نفسه
    عشوائي طويل لا يقبل التخمين بقاموس.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
