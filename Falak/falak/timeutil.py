# -*- coding: utf-8 -*-
"""وحدة الزمن: التاريخ اليولياني، فرق الزمن ΔT، والزمن النجمي.

الاصطلاحات المستخدمة في المشروع:
  * ``jd``   : التاريخ اليولياني بالتوقيت العالمي (UT).
  * ``jde``  : التاريخ اليولياني بالزمن الديناميكي (TT = UT + ΔT).
  * خطوط الطول شرقًا موجبة، وخطوط العرض شمالًا موجبة.
"""

from __future__ import division

import datetime
import math

from .angles import norm360

J2000 = 2451545.0
DAYS_PER_CENTURY = 36525.0

__all__ = [
    "J2000", "julian_day", "jd_from_datetime", "datetime_from_jd",
    "calendar_from_jd", "delta_t_seconds", "jde_from_jd", "julian_centuries",
    "gmst_degrees", "day_of_week_ar", "gregorian_month_ar",
]


# ---------------------------------------------------------------------------
# التحويل بين التقويم الميلادي واليوم اليولياني
# ---------------------------------------------------------------------------

def julian_day(year, month, day):
    """حساب اليوم اليولياني من تاريخ ميلادي (اليوم قد يكون كسريًا).

    يتبع خوارزمية ميوس (Astronomical Algorithms, الفصل 7) ويدعم
    التقويمين اليولياني (قبل 1582/10/15) والغريغوري.
    """
    gregorian = (year, month, day) >= (1582, 10, 15.0)
    if month <= 2:
        year -= 1
        month += 12
    if gregorian:
        a = int(math.floor(year / 100.0))
        b = 2 - a + int(math.floor(a / 4.0))
    else:
        b = 0
    return (int(math.floor(365.25 * (year + 4716)))
            + int(math.floor(30.6001 * (month + 1)))
            + day + b - 1524.5)


def calendar_from_jd(jd):
    """عكس ``julian_day``: يعيد (سنة، شهر، يوم كسري)."""
    jd = jd + 0.5
    z = int(math.floor(jd))
    f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) // 36524.25)
        a = z + 1 + alpha - int(alpha // 4)
    b = a + 1524
    c = int((b - 122.1) // 365.25)
    d = int(365.25 * c)
    e = int((b - d) // 30.6001)
    day = b - d - int(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    return year, month, day


def jd_from_datetime(dt):
    """تحويل ``datetime`` بالتوقيت العالمي (UTC) إلى يوم يولياني."""
    frac = (dt.hour + dt.minute / 60.0 + dt.second / 3600.0
            + dt.microsecond / 3.6e9) / 24.0
    return julian_day(dt.year, dt.month, dt.day + frac)


def datetime_from_jd(jd):
    """تحويل يوم يولياني إلى ``datetime`` (بدون منطقة زمنية، يمثل UTC)."""
    year, month, day = calendar_from_jd(jd)
    d = int(math.floor(day))
    seconds = (day - d) * 86400.0
    base = datetime.datetime(year, month, d)
    return base + datetime.timedelta(seconds=seconds)


def julian_centuries(jd):
    """عدد القرون اليوليانية منذ حقبة J2000.0."""
    return (jd - J2000) / DAYS_PER_CENTURY


# ---------------------------------------------------------------------------
# فرق الزمن ΔT = TT - UT
# ---------------------------------------------------------------------------

# قيم مرصودة تقريبية لفرق الزمن (بالثواني) عند بداية كل سنة مذكورة.
# تُستخدم للاستيفاء في الحقبة الحديثة لأن متعددات الحدود التاريخية
# تبالغ في تقدير ΔT بعد سنة 2015 بعدة ثوانٍ.
_DELTA_T_MODERN = [
    (1990.0, 56.86), (1995.0, 60.78), (2000.0, 63.83), (2005.0, 64.69),
    (2010.0, 66.07), (2015.0, 67.64), (2018.0, 69.00), (2020.0, 69.36),
    (2022.0, 69.29), (2024.0, 69.18), (2025.0, 69.20),
]


def _year_fraction(jd):
    year, month, day = calendar_from_jd(jd)
    return year + (month - 0.5) / 12.0


def delta_t_seconds(jd):
    """تقدير فرق الزمن ΔT بالثواني عند يوم يولياني معطى.

    الحقبة 1990–2025 تعتمد على استيفاء خطي لقيم مرصودة، وما عداها
    يعتمد على متعددات حدود إسبيناك وميوس (NASA Five Millennium Canon).
    الخطأ المتوقع في الحقبة الحديثة أقل من ثانيتين، وهو أثر مهمل
    على المواقع المحسوبة (أقل من ثانية قوسية للقمر).
    """
    y = _year_fraction(jd)

    if 1990.0 <= y <= 2025.0:
        for i in range(len(_DELTA_T_MODERN) - 1):
            y0, d0 = _DELTA_T_MODERN[i]
            y1, d1 = _DELTA_T_MODERN[i + 1]
            if y0 <= y <= y1:
                return d0 + (d1 - d0) * (y - y0) / (y1 - y0)
        return _DELTA_T_MODERN[-1][1]

    if 2025.0 < y < 2050.0:
        # استقراء خطي معتدل من آخر قيمة مرصودة (≈0.4 ثانية سنويًا)
        return 69.20 + 0.40 * (y - 2025.0)

    if y < 1600.0:
        u = (y - 1820.0) / 100.0
        return -20.0 + 32.0 * u * u
    if y < 1700.0:
        t = y - 1600.0
        return 120.0 - 0.9808 * t - 0.01532 * t ** 2 + t ** 3 / 7129.0
    if y < 1800.0:
        t = y - 1700.0
        return (8.83 + 0.1603 * t - 0.0059285 * t ** 2
                + 0.00013336 * t ** 3 - t ** 4 / 1174000.0)
    if y < 1860.0:
        t = y - 1800.0
        return (13.72 - 0.332447 * t + 0.0068612 * t ** 2 + 0.0041116 * t ** 3
                - 0.00037436 * t ** 4 + 0.0000121272 * t ** 5
                - 0.0000001699 * t ** 6 + 0.000000000875 * t ** 7)
    if y < 1900.0:
        t = y - 1860.0
        return (7.62 + 0.5737 * t - 0.251754 * t ** 2 + 0.01680668 * t ** 3
                - 0.0004473624 * t ** 4 + t ** 5 / 233174.0)
    if y < 1920.0:
        t = y - 1900.0
        return (-2.79 + 1.494119 * t - 0.0598939 * t ** 2
                + 0.0061966 * t ** 3 - 0.000197 * t ** 4)
    if y < 1941.0:
        t = y - 1920.0
        return 21.20 + 0.84493 * t - 0.076100 * t ** 2 + 0.0020936 * t ** 3
    if y < 1961.0:
        t = y - 1950.0
        return 29.07 + 0.407 * t - t ** 2 / 233.0 + t ** 3 / 2547.0
    if y < 1986.0:
        t = y - 1975.0
        return 45.45 + 1.067 * t - t ** 2 / 260.0 - t ** 3 / 718.0
    if y < 1990.0:
        t = y - 2000.0
        return (63.86 + 0.3345 * t - 0.060374 * t ** 2 + 0.0017275 * t ** 3
                + 0.000651814 * t ** 4 + 0.00002373599 * t ** 5)
    if y < 2150.0:
        u = (y - 1820.0) / 100.0
        return -20.0 + 32.0 * u * u - 0.5628 * (2150.0 - y)
    u = (y - 1820.0) / 100.0
    return -20.0 + 32.0 * u * u


def jde_from_jd(jd):
    """تحويل اليوم اليولياني بالتوقيت العالمي إلى الزمن الديناميكي."""
    return jd + delta_t_seconds(jd) / 86400.0


# ---------------------------------------------------------------------------
# الزمن النجمي
# ---------------------------------------------------------------------------

def gmst_degrees(jd_ut):
    """الزمن النجمي المتوسط في غرينتش بالدرجات (ميوس 12.4)."""
    t = julian_centuries(jd_ut)
    theta = (280.46061837 + 360.98564736629 * (jd_ut - J2000)
             + 0.000387933 * t * t - t ** 3 / 38710000.0)
    return norm360(theta)


def gast_degrees(jd_ut, nutation_longitude_deg, true_obliquity_deg):
    """الزمن النجمي الظاهري في غرينتش بالدرجات."""
    from .angles import cosd
    return norm360(gmst_degrees(jd_ut)
                   + nutation_longitude_deg * cosd(true_obliquity_deg))


def local_sidereal_degrees(jd_ut, longitude_east, nutation_longitude_deg=0.0,
                           true_obliquity_deg=23.4392911):
    """الزمن النجمي الظاهري المحلي بالدرجات (خط الطول شرقًا موجب)."""
    return norm360(gast_degrees(jd_ut, nutation_longitude_deg,
                                true_obliquity_deg) + longitude_east)


# ---------------------------------------------------------------------------
# أسماء عربية للتقويم الميلادي
# ---------------------------------------------------------------------------

DAYS_AR = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس",
           "الجمعة", "السبت", "الأحد"]

MONTHS_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
             "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]


def day_of_week_ar(jd):
    """اسم يوم الأسبوع بالعربية ليوم يولياني."""
    index = int(math.floor(jd + 1.5)) % 7  # 0 = الأحد
    order = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء",
             "الخميس", "الجمعة", "السبت"]
    return order[index]


def gregorian_month_ar(month):
    """اسم الشهر الميلادي بالعربية (1..12)."""
    return MONTHS_AR[month - 1]


def format_gregorian_ar(year, month, day):
    """صياغة تاريخ ميلادي بالعربية."""
    return "%d %s %d م" % (int(day), gregorian_month_ar(month), year)
