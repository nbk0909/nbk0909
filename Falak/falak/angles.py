# -*- coding: utf-8 -*-
"""وحدة الزوايا: دوال مثلثية بالدرجات وأدوات تنسيق عربية.

كل الزوايا في المشروع بالدرجات العشرية ما لم يُذكر خلاف ذلك.
"""

from __future__ import division

import math

__all__ = [
    "rad", "deg", "sind", "cosd", "tand", "asind", "acosd", "atan2d",
    "norm360", "norm180", "norm24", "dms", "hms", "fmt_time",
    "to_arabic_digits", "fmt_signed_deg",
]


def rad(d):
    """تحويل الدرجات إلى راديان."""
    return d * math.pi / 180.0


def deg(r):
    """تحويل الراديان إلى درجات."""
    return r * 180.0 / math.pi


def sind(d):
    return math.sin(rad(d))


def cosd(d):
    return math.cos(rad(d))


def tand(d):
    return math.tan(rad(d))


def asind(x):
    """قوس الجيب بالدرجات مع تقييد المدخل لتفادي أخطاء التقريب."""
    if x > 1.0:
        x = 1.0
    elif x < -1.0:
        x = -1.0
    return deg(math.asin(x))


def acosd(x):
    if x > 1.0:
        x = 1.0
    elif x < -1.0:
        x = -1.0
    return deg(math.acos(x))


def atan2d(y, x):
    return deg(math.atan2(y, x))


def norm360(x):
    """إرجاع الزاوية ضمن المدى [0, 360)."""
    return x % 360.0


def norm180(x):
    """إرجاع الزاوية ضمن المدى (-180, 180]."""
    x = x % 360.0
    if x > 180.0:
        x -= 360.0
    return x


def norm24(x):
    """إرجاع الساعات ضمن المدى [0, 24)."""
    return x % 24.0


# ---------------------------------------------------------------------------
# التنسيق
# ---------------------------------------------------------------------------

_ARABIC_DIGITS = {
    "0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤",
    "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩",
}


def to_arabic_digits(text):
    """تحويل الأرقام اللاتينية في نص إلى أرقام عربية-هندية (٠١٢٣...)."""
    return "".join(_ARABIC_DIGITS.get(ch, ch) for ch in str(text))


def _split_sexagesimal(value, seconds_decimals):
    sign = -1 if value < 0 else 1
    value = abs(value)
    seconds_total = round(value * 3600.0, seconds_decimals)
    whole = int(seconds_total // 3600)
    rest = seconds_total - whole * 3600
    minutes = int(rest // 60)
    seconds = rest - minutes * 60
    # معالجة حالات التقريب مثل 59.9999 ثانية
    if round(seconds, seconds_decimals) >= 60.0:
        seconds -= 60.0
        minutes += 1
    if minutes >= 60:
        minutes -= 60
        whole += 1
    return sign, whole, minutes, seconds


def dms(value_deg, seconds_decimals=0):
    """صياغة زاوية بالدرجات على هيئة ‎°‏ ‎′‏ ‎″‏ (مثال: 23° 26′ 21″)."""
    sign, d, m, s = _split_sexagesimal(value_deg, seconds_decimals)
    fmt = "%0" + str(2 + (1 + seconds_decimals if seconds_decimals else 0)) + "." + str(seconds_decimals) + "f"
    text = "%d° %02d′ %s″" % (d, m, fmt % s)
    return ("-" + text) if sign < 0 else text


def fmt_signed_deg(value_deg, decimals=2):
    """صياغة زاوية بالدرجات العشرية مع إشارة صريحة."""
    return ("%+." + str(decimals) + "f°") % value_deg


def hms(hours, seconds_decimals=0):
    """صياغة زاوية ساعية على هيئة ‎س‏ ‎د‏ ‎ث‏ (مثال: 6س 45د 09ث)."""
    sign, h, m, s = _split_sexagesimal(norm24(hours) if hours >= 0 else hours, seconds_decimals)
    fmt = "%0" + str(2 + (1 + seconds_decimals if seconds_decimals else 0)) + "." + str(seconds_decimals) + "f"
    text = "%02dس %02dد %sث" % (h, m, fmt % s)
    return ("-" + text) if sign < 0 else text


def fmt_time(hours, with_seconds=False):
    """صياغة وقت الساعة (0..24) على هيئة HH:MM أو HH:MM:SS."""
    if hours is None:
        return "—"
    total = round(hours * 3600.0)
    total %= 86400
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if with_seconds:
        return "%02d:%02d:%02d" % (h, m, s)
    # تقريب إلى أقرب دقيقة
    total_min = int(round(hours * 60.0)) % 1440
    return "%02d:%02d" % (total_min // 60, total_min % 60)


def fmt_duration(hours):
    """صياغة مدة زمنية بالساعات إلى «سس ساعة دد دقيقة»."""
    if hours is None:
        return "—"
    total_min = int(round(hours * 60.0))
    return "%d س %02d د" % (total_min // 60, total_min % 60)
