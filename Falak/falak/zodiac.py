# -*- coding: utf-8 -*-
"""بروج دائرة البروج ومنازلها، وتحديد البرج من الطول الكسوفي.

ملاحظة مهمة: ما يُعرض هنا وصف فلكي بحت — أي في أي ثلاثين درجة من
دائرة البروج يقع الجرم الآن — وليس تنبؤًا بالحظوظ أو الطباع.
"""

from __future__ import division

from .angles import norm360

__all__ = ["ZODIAC_SIGNS_AR", "sign_of", "sign_name", "format_sign_position",
           "sun_sign_dates"]

ZODIAC_SIGNS_AR = [
    "الحَمَل", "الثَّور", "الجَوزاء", "السَّرَطان", "الأسَد", "العَذراء",
    "الميزان", "العَقرَب", "القَوس", "الجَدي", "الدَّلو", "الحُوت",
]

ZODIAC_SYMBOLS = ["♈", "♉", "♊", "♋", "♌", "♍",
                  "♎", "♏", "♐", "♑", "♒", "♓"]


def sign_of(ecliptic_longitude):
    """يعيد (رقم البرج 0..11، الدرجة داخله)."""
    lon = norm360(ecliptic_longitude)
    index = int(lon // 30.0)
    return index, lon - index * 30.0


def sign_name(ecliptic_longitude):
    """اسم البرج الذي يقع فيه طول كسوفي معطى."""
    index, _ = sign_of(ecliptic_longitude)
    return ZODIAC_SIGNS_AR[index]


def format_sign_position(ecliptic_longitude, with_symbol=True):
    """صياغة موقع الجرم داخل برجه، مثل: «الأسد ‎16° 30′‏»."""
    index, degrees = sign_of(ecliptic_longitude)
    d = int(degrees)
    m = int(round((degrees - d) * 60.0))
    if m == 60:
        m = 0
        d += 1
    text = "%s %d° %02d′" % (ZODIAC_SIGNS_AR[index], d, m)
    if with_symbol:
        text = ZODIAC_SYMBOLS[index] + " " + text
    return text


# الحدود التقريبية لدخول الشمس كل برج (اليوم/الشهر الميلادي)
SUN_SIGN_RANGES = [
    ("الحَمَل", (3, 21), (4, 19)),
    ("الثَّور", (4, 20), (5, 20)),
    ("الجَوزاء", (5, 21), (6, 20)),
    ("السَّرَطان", (6, 21), (7, 22)),
    ("الأسَد", (7, 23), (8, 22)),
    ("العَذراء", (8, 23), (9, 22)),
    ("الميزان", (9, 23), (10, 22)),
    ("العَقرَب", (10, 23), (11, 21)),
    ("القَوس", (11, 22), (12, 21)),
    ("الجَدي", (12, 22), (1, 19)),
    ("الدَّلو", (1, 20), (2, 18)),
    ("الحُوت", (2, 19), (3, 20)),
]


def sun_sign_dates():
    """جدول البروج وحدودها التاريخية التقريبية."""
    return SUN_SIGN_RANGES


# أسماء الكواكب السبعة السيّارة كما وردت في التراث الفلكي العربي
CLASSICAL_NAMES = {
    "الشمس": "الشمس",
    "القمر": "القمر",
    "عطارد": "عطارد (الكاتب)",
    "الزهرة": "الزهرة (السعد الأصغر)",
    "المريخ": "المريخ (النحس الأصغر)",
    "المشتري": "المشتري (السعد الأكبر)",
    "زحل": "زحل (النحس الأكبر)",
}
