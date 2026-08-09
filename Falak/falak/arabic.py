# -*- coding: utf-8 -*-
"""مساعدات لغوية عربية: التذكير والتأنيث وتمييز العدد.

العربية تشترط مطابقة الوصف للموصوف في التذكير والتأنيث، ومطابقة تمييز
العدد لصيغته، فتُكتب «ثلاثة أيام» لا «3 يوم». هذه الوحدة تتكفل بذلك
حتى تخرج نصوص التقرير سليمة.
"""

from __future__ import division

__all__ = ["is_feminine", "agree", "count_days", "count_hours"]

# الأجرام المؤنثة لفظًا في العربية
FEMININE_BODIES = frozenset(["الشمس", "الزهرة", "الثريا", "الشعرى اليمانية",
                             "الشعرى الشامية", "الجوزاء", "النعائم"])


def is_feminine(name):
    """هل اسم الجرم مؤنث لفظًا؟"""
    return name in FEMININE_BODIES


def agree(name, masculine, feminine):
    """اختيار الصيغة الموافقة لجنس اسم الجرم."""
    return feminine if is_feminine(name) else masculine


def _counted(count, singular, dual, plural, accusative, bare):
    """صياغة العدد مع تمييزه وفق قواعد العربية.

    من 3 إلى 10 يُجمع التمييز، ومن 11 إلى 99 يُفرد منصوبًا،
    ومع المئة والألف يُفرد مجرورًا (مئةُ يومٍ لا مئةُ يومًا).
    """
    count = int(count)
    if count == 1:
        return singular
    if count == 2:
        return dual
    if 3 <= count <= 10:
        return "%d %s" % (count, plural)
    if count >= 100 and count % 100 == 0:
        return "%d %s" % (count, bare)
    return "%d %s" % (count, accusative)


def count_days(count):
    """صياغة عدد الأيام: «يوم واحد»، «يومان»، «3 أيام»، «12 يومًا»."""
    return _counted(count, "يوم واحد", "يومان", "أيام", "يومًا", "يوم")


def count_hours(count):
    """صياغة عدد الساعات بالطريقة نفسها."""
    return _counted(count, "ساعة واحدة", "ساعتان", "ساعات", "ساعة", "ساعة")


def count_meteors(count):
    """صياغة عدد الشهب في الساعة."""
    return _counted(count, "شهاب واحد", "شهابان", "شهب", "شهابًا", "شهاب")
