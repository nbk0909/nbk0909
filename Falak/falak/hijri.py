# -*- coding: utf-8 -*-
"""التقويم الهجري الحسابي (الجدولي) وتقدير رؤية الهلال.

التقويم المستخدم هنا هو التقويم الهجري الحسابي المعروف بالخوارزمية
الكويتية، وهو تقويم اصطلاحي قد يختلف عن التقويم المعتمد على الرؤية
الشرعية بيوم أو يومين. لذلك تُعرض معه دائمًا ملاحظة تنبيه.
"""

from __future__ import division

import math

__all__ = ["HIJRI_MONTHS_AR", "jd_to_hijri", "hijri_to_jd",
           "format_hijri", "crescent_visibility"]

HIJRI_MONTHS_AR = [
    "محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى",
    "جمادى الآخرة", "رجب", "شعبان", "رمضان", "شوال",
    "ذو القعدة", "ذو الحجة",
]


def jd_to_hijri(jd):
    """تحويل يوم يولياني إلى (سنة، شهر، يوم) هجرية حسابية."""
    jdn = int(math.floor(jd + 0.5))
    l = jdn - 1948440 + 10632
    n = (l - 1) // 10631
    l = l - 10631 * n + 354
    j = (((10985 - l) // 5316) * ((50 * l) // 17719)
         + (l // 5670) * ((43 * l) // 15238))
    l = (l - ((30 - j) // 15) * ((17719 * j) // 50)
         - (j // 16) * ((15238 * j) // 43) + 29)
    month = (24 * l) // 709
    day = l - (709 * month) // 24
    year = 30 * n + j - 30
    return year, month, day


def hijri_to_jd(year, month, day):
    """تحويل تاريخ هجري حسابي إلى يوم يولياني (عند منتصف الليل)."""
    jdn = (int((11 * year + 3) / 30) + 354 * year + 30 * month
           - int((month - 1) / 2) + day + 1948440 - 385)
    return float(jdn) - 0.5


def format_hijri(jd):
    """صياغة التاريخ الهجري بالعربية."""
    year, month, day = jd_to_hijri(jd)
    month = min(max(month, 1), 12)
    return "%d %s %d هـ" % (day, HIJRI_MONTHS_AR[month - 1], year)


def crescent_visibility(moon_set_hours, sun_set_hours, illumination,
                        moon_age_days, elongation):
    """تقدير مبسّط لإمكان رؤية الهلال بعد الغروب.

    يعتمد على معياري «زمن المكث» (الفرق بين غروب القمر وغروب الشمس)
    وعمر القمر والاستطالة، وهي معايير تقريبية شائعة في حساب أوائل الشهور.
    يعيد (تصنيف نصي، تفصيل نصي).
    """
    if moon_set_hours is None or sun_set_hours is None:
        return "غير محدد", "تعذّر حساب أوقات الغروب لهذا الموقع."

    lag_minutes = (moon_set_hours - sun_set_hours) * 60.0
    if lag_minutes < 0:
        return ("متعذّرة",
                "القمر يغرب قبل الشمس بـ %d دقيقة، فلا يمكن رؤية الهلال."
                % int(abs(lag_minutes)))

    details = ("زمن المكث %d دقيقة، عمر القمر %.1f ساعة، الاستطالة %.1f°."
               % (int(lag_minutes), moon_age_days * 24.0, elongation))

    if lag_minutes >= 40 and elongation >= 10.0 and moon_age_days * 24 >= 20:
        return "ممكنة بالعين المجردة", details
    if lag_minutes >= 25 and elongation >= 8.0:
        return "ممكنة بالمراصد والتلسكوبات", details
    if lag_minutes >= 15:
        return "صعبة جدًا", details
    return "متعذّرة", details
