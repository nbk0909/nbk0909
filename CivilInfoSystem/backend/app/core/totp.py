"""المصادقة الثنائية بخوارزمية TOTP.

السرّ يُخزَّن مشفّراً في قاعدة البيانات (لا نصاً صريحاً)، ويُعرض للمستخدم
مرة واحدة فقط عند التفعيل عبر رمز QR.
"""

from __future__ import annotations

import base64
import io
import secrets

import pyotp

from app.config import settings

# نافذة التسامح: تُقبل الرموز من الفترة السابقة والحالية معاً، لاستيعاب
# فارق الساعة بين هاتف المستخدم والخادم. توسيعها أكثر يُضعف الحماية.
VALID_WINDOW = 1

# عدد رموز الاسترداد التي تُولَّد عند التفعيل
RECOVERY_CODE_COUNT = 8


def generate_secret() -> str:
    """يولّد سرّاً جديداً بصيغة Base32."""
    return pyotp.random_base32()


def build_provisioning_uri(secret: str, username: str) -> str:
    """يبني رابط التهيئة الذي يُقرأ من تطبيق المصادقة."""
    return pyotp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=settings.APP_NAME,
    )


def generate_qr_data_uri(secret: str, username: str) -> str:
    """يولّد رمز QR كصورة PNG مضمّنة بصيغة data: URI.

    التضمين يتجنّب حفظ الصورة على القرص أو تمريرها عبر خدمة خارجية —
    وكلاهما تسريب لسرّ المصادقة الثنائية.
    """
    import qrcode

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(build_provisioning_uri(secret, username))
    qr.make(fit=True)

    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    return f"data:image/png;base64,{encoded}"


def verify_totp(secret: str, code: str) -> bool:
    """يتحقق من صحة رمز المصادقة الثنائية."""
    if not secret or not code:
        return False

    cleaned = code.strip().replace(" ", "").replace("-", "")
    if not cleaned.isdigit():
        return False

    return pyotp.TOTP(secret).verify(cleaned, valid_window=VALID_WINDOW)


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    """يولّد رموز استرداد تُستخدم عند فقدان الهاتف.

    كل رمز صالح لاستعمال واحد، ويُخزَّن مجزّأً كما تُخزَّن كلمات المرور.
    """
    return [
        f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}"
        for _ in range(count)
    ]
