"""مُتحقِّقات صحة البيانات المدنية.

تُستخدم في طبقة النماذج وفي مخططات Pydantic على حد سواء.
"""

from __future__ import annotations

import re
from datetime import date

# ---------------------------------------------------------------------------
# الرقم الوطني
# ---------------------------------------------------------------------------
#  بنية الرقم الوطني المعتمدة في هذا النظام (12 خانة):
#
#      YYMMDD  |  GG  |  SSS  |  C
#      ------- | ---- | ----- | ---
#      الميلاد | المحافظة | تسلسل | تدقيق
#
#  خانة التدقيق تُحسب بخوارزمية Luhn على الخانات الإحدى عشرة السابقة،
#  فتلتقط أخطاء الإدخال الشائعة (خانة خاطئة، أو تبديل خانتين متجاورتين).
# ---------------------------------------------------------------------------

NATIONAL_ID_LENGTH = 12
_NATIONAL_ID_RE = re.compile(r"^\d{12}$")


def compute_check_digit(payload: str) -> str:
    """يحسب خانة التدقيق (Luhn) للخانات الإحدى عشرة الأولى."""
    if not payload.isdigit() or len(payload) != NATIONAL_ID_LENGTH - 1:
        raise ValueError("يجب أن تتكوّن البيانات من 11 خانة رقمية")

    total = 0
    # الترقيم من اليمين: كل خانة في موضع فردي تُضاعف
    for index, char in enumerate(reversed(payload)):
        digit = int(char)
        if index % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit

    return str((10 - (total % 10)) % 10)


def validate_national_id(national_id: str | None) -> bool:
    """يتحقق من صحة الرقم الوطني شكلاً وخانةَ تدقيق."""
    if not national_id or not _NATIONAL_ID_RE.match(national_id):
        return False
    return compute_check_digit(national_id[:-1]) == national_id[-1]


def generate_national_id(birth_date: date, governorate_code: int, serial: int) -> str:
    """يولّد رقماً وطنياً صحيحاً — يُستخدم في التسجيل وفي البيانات التجريبية.

    >>> nid = generate_national_id(date(1990, 1, 15), 1, 42)
    >>> validate_national_id(nid)
    True
    """
    if not 0 <= governorate_code <= 99:
        raise ValueError("رمز المحافظة يجب أن يكون بين 0 و 99")
    if not 0 <= serial <= 999:
        raise ValueError("الرقم التسلسلي يجب أن يكون بين 0 و 999")

    payload = f"{birth_date:%y%m%d}{governorate_code:02d}{serial:03d}"
    return payload + compute_check_digit(payload)


def extract_birth_date_from_national_id(national_id: str) -> date | None:
    """يستخرج تاريخ الميلاد المضمّن في الرقم الوطني، أو None إن كان غير صالح.

    السنة ذات خانتين، فتُحسم بقاعدة النافذة: أي سنة تتجاوز السنة الحالية
    تُعتبر من القرن الماضي.
    """
    if not validate_national_id(national_id):
        return None

    yy, mm, dd = int(national_id[0:2]), int(national_id[2:4]), int(national_id[4:6])
    current_yy = date.today().year % 100
    century = 1900 if yy > current_yy else 2000

    try:
        return date(century + yy, mm, dd)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# مُتحقِّقات أخرى
# ---------------------------------------------------------------------------

_PHONE_RE = re.compile(r"^(\+?964|0)?7[3-9]\d{8}$")


def validate_phone(phone: str | None) -> bool:
    """يتحقق من صيغة رقم الهاتف المحمول."""
    if not phone:
        return False
    return bool(_PHONE_RE.match(phone.replace(" ", "").replace("-", "")))


def validate_password_strength(password: str, min_length: int = 10) -> list[str]:
    """يُرجع قائمة بالمشاكل في كلمة المرور — قائمة فارغة تعني أنها مقبولة."""
    problems: list[str] = []

    if len(password) < min_length:
        problems.append(f"يجب ألا يقل طول كلمة المرور عن {min_length} حرفاً")
    if not re.search(r"[a-z]", password):
        problems.append("يجب أن تحتوي على حرف لاتيني صغير")
    if not re.search(r"[A-Z]", password):
        problems.append("يجب أن تحتوي على حرف لاتيني كبير")
    if not re.search(r"\d", password):
        problems.append("يجب أن تحتوي على رقم")
    if not re.search(r"[^\w\s]", password):
        problems.append("يجب أن تحتوي على رمز خاص")

    return problems


def validate_date_not_future(value: date | None, field_name: str = "التاريخ") -> None:
    """يرفع ValueError إذا كان التاريخ في المستقبل."""
    if value and value > date.today():
        raise ValueError(f"{field_name} لا يمكن أن يكون في المستقبل")
