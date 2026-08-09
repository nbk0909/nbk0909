# -*- coding: utf-8 -*-
"""موقع القمر وأطواره (نظرية ELP-2000/82 المختصرة، ميوس الفصل 47).

الدقة المتوقعة: نحو 10 ثوانٍ قوسية في الطول، و4 ثوانٍ في العرض،
ونحو 20 كيلومترًا في البعد — وهي أدق بكثير مما يحتاجه الرصد بالعين.
"""

from __future__ import division

from .angles import asind, atan2d, cosd, norm360, sind
from .coords import (angular_separation, ecliptic_to_equatorial,
                     mean_obliquity, nutation)
from .sun import sun_apparent
from .timeutil import julian_centuries

__all__ = ["moon_position", "MoonPosition", "moon_phase_info",
           "next_moon_phase", "lunar_mansion"]

EARTH_RADIUS_KM = 6378.14

# جدول 47.أ — الحدود الدورية للطول (Σl بوحدة 1e-6 درجة)
# والبعد (Σr بوحدة 1e-3 كم). الأعمدة: D, M, M', F, Σl, Σr
_TERMS_LR = (
    (0, 0, 1, 0, 6288774, -20905355),
    (2, 0, -1, 0, 1274027, -3699111),
    (2, 0, 0, 0, 658314, -2955968),
    (0, 0, 2, 0, 213618, -569925),
    (0, 1, 0, 0, -185116, 48888),
    (0, 0, 0, 2, -114332, -3149),
    (2, 0, -2, 0, 58793, 246158),
    (2, -1, -1, 0, 57066, -152138),
    (2, 0, 1, 0, 53322, -170733),
    (2, -1, 0, 0, 45758, -204586),
    (0, 1, -1, 0, -40923, -129620),
    (1, 0, 0, 0, -34720, 108743),
    (0, 1, 1, 0, -30383, 104755),
    (2, 0, 0, -2, 15327, 10321),
    (0, 0, 1, 2, -12528, 0),
    (0, 0, 1, -2, 10980, 79661),
    (4, 0, -1, 0, 10675, -34782),
    (0, 0, 3, 0, 10034, -23210),
    (4, 0, -2, 0, 8548, -21636),
    (2, 1, -1, 0, -7888, 24208),
    (2, 1, 0, 0, -6766, 30824),
    (1, 0, -1, 0, -5163, -8379),
    (1, 1, 0, 0, 4987, -16675),
    (2, -1, 1, 0, 4036, -12831),
    (2, 0, 2, 0, 3994, -10445),
    (4, 0, 0, 0, 3861, -11650),
    (2, 0, -3, 0, 3665, 14403),
    (0, 1, -2, 0, -2689, -7003),
    (2, 0, -1, 2, -2602, 0),
    (2, -1, -2, 0, 2390, 10056),
    (1, 0, 1, 0, -2348, 6322),
    (2, -2, 0, 0, 2236, -9884),
    (0, 1, 2, 0, -2120, 5751),
    (0, 2, 0, 0, -2069, 0),
    (2, -2, -1, 0, 2048, -4950),
    (2, 0, 1, -2, -1773, 4130),
    (2, 0, 0, 2, -1595, 0),
    (4, -1, -1, 0, 1215, -3958),
    (0, 0, 2, 2, -1110, 0),
    (3, 0, -1, 0, -892, 3258),
    (2, 1, 1, 0, -810, 2616),
    (4, -1, -2, 0, 759, -1897),
    (0, 2, -1, 0, -713, -2117),
    (2, 2, -1, 0, -700, 2354),
    (2, 1, -2, 0, 691, 0),
    (2, -1, 0, -2, 596, 0),
    (4, 0, 1, 0, 549, -1423),
    (0, 0, 4, 0, 537, -1117),
    (4, -1, 0, 0, 520, -1571),
    (1, 0, -2, 0, -487, -1739),
    (2, 1, 0, -2, -399, 0),
    (0, 0, 2, -2, -381, -4421),
    (1, 1, 1, 0, 351, 0),
    (3, 0, -2, 0, -340, 0),
    (4, 0, -3, 0, 330, 0),
    (2, -1, 2, 0, 327, 0),
    (0, 2, 1, 0, -323, 1165),
    (1, 1, -1, 0, 299, 0),
    (2, 0, 3, 0, 294, 0),
    (2, 0, -1, -2, 0, 8752),
)

# جدول 47.ب — الحدود الدورية للعرض (Σb بوحدة 1e-6 درجة)
_TERMS_B = (
    (0, 0, 0, 1, 5128122),
    (0, 0, 1, 1, 280602),
    (0, 0, 1, -1, 277693),
    (2, 0, 0, -1, 173237),
    (2, 0, -1, 1, 55413),
    (2, 0, -1, -1, 46271),
    (2, 0, 0, 1, 32573),
    (0, 0, 2, 1, 17198),
    (2, 0, 1, -1, 9266),
    (0, 0, 2, -1, 8822),
    (2, -1, 0, -1, 8216),
    (2, 0, -2, -1, 4324),
    (2, 0, 1, 1, 4200),
    (2, 1, 0, -1, -3359),
    (2, -1, -1, 1, 2463),
    (2, -1, 0, 1, 2211),
    (2, -1, -1, -1, 2065),
    (0, 1, -1, -1, -1870),
    (4, 0, -1, -1, 1828),
    (0, 1, 0, 1, -1794),
    (0, 0, 0, 3, -1749),
    (0, 1, -1, 1, -1565),
    (1, 0, 0, 1, -1491),
    (0, 1, 1, 1, -1475),
    (0, 1, 1, -1, -1410),
    (0, 1, 0, -1, -1344),
    (1, 0, 0, -1, -1335),
    (0, 0, 3, 1, 1107),
    (4, 0, 0, -1, 1021),
    (4, 0, -1, 1, 833),
    (0, 0, 1, -3, 777),
    (4, 0, -2, 1, 671),
    (2, 0, 0, -3, 607),
    (2, 0, 2, -1, 596),
    (2, -1, 1, -1, 491),
    (2, 0, -2, 1, -451),
    (0, 0, 3, -1, 439),
    (2, 0, 2, 1, 422),
    (2, 0, -3, -1, 421),
    (2, 1, -1, 1, -366),
    (2, 1, 0, 1, -351),
    (4, 0, 0, 1, 331),
    (2, -1, 1, 1, 315),
    (2, -2, 0, -1, 302),
    (0, 0, 1, 3, -283),
    (2, 1, 1, -1, -229),
    (1, 1, 0, -1, 223),
    (1, 1, 0, 1, 223),
    (0, 1, -2, -1, -220),
    (2, 1, -1, -1, -220),
    (1, 0, 1, 1, -185),
    (2, -1, -2, -1, 181),
    (0, 1, 2, 1, -177),
    (4, 0, -2, -1, 176),
    (4, -1, -1, -1, 166),
    (1, 0, 1, -1, -164),
    (4, 0, 1, -1, 132),
    (1, 0, -1, -1, -119),
    (4, -1, 0, -1, 115),
    (2, -2, 0, 1, 107),
)


class MoonPosition(object):
    """موقع القمر الظاهري في لحظة معطاة."""

    __slots__ = ("jde", "longitude", "latitude", "distance_km", "parallax",
                 "right_ascension", "declination", "semidiameter")

    def __init__(self, jde, longitude, latitude, distance_km, parallax,
                 right_ascension, declination, semidiameter):
        self.jde = jde
        self.longitude = longitude
        self.latitude = latitude
        self.distance_km = distance_km
        self.parallax = parallax
        self.right_ascension = right_ascension
        self.declination = declination
        self.semidiameter = semidiameter


def moon_position(jde, apparent=True):
    """حساب موقع القمر: الطول والعرض الكسوفيان والبعد والإحداثيات الاستوائية.

    عند ``apparent=True`` تُضاف تقلقل الطول ليكون الموقع ظاهريًا.
    """
    t = julian_centuries(jde)

    l_prime = norm360(218.3164477 + 481267.88123421 * t - 0.0015786 * t ** 2
                      + t ** 3 / 538841.0 - t ** 4 / 65194000.0)
    d = norm360(297.8501921 + 445267.1114034 * t - 0.0018819 * t ** 2
                + t ** 3 / 545868.0 - t ** 4 / 113065000.0)
    m = norm360(357.5291092 + 35999.0502909 * t - 0.0001536 * t ** 2
                + t ** 3 / 24490000.0)
    m_prime = norm360(134.9633964 + 477198.8675055 * t + 0.0087414 * t ** 2
                      + t ** 3 / 69699.0 - t ** 4 / 14712000.0)
    f = norm360(93.2720950 + 483202.0175233 * t - 0.0036539 * t ** 2
                - t ** 3 / 3526000.0 + t ** 4 / 863310000.0)

    a1 = norm360(119.75 + 131.849 * t)
    a2 = norm360(53.09 + 479264.290 * t)
    a3 = norm360(313.45 + 481266.484 * t)

    e = 1.0 - 0.002516 * t - 0.0000074 * t * t
    e2 = e * e

    sum_l = 0.0
    sum_r = 0.0
    for cd, cm, cmp_, cf, coef_l, coef_r in _TERMS_LR:
        arg = cd * d + cm * m + cmp_ * m_prime + cf * f
        if cm == 1 or cm == -1:
            factor = e
        elif cm == 2 or cm == -2:
            factor = e2
        else:
            factor = 1.0
        if coef_l:
            sum_l += coef_l * factor * sind(arg)
        if coef_r:
            sum_r += coef_r * factor * cosd(arg)

    sum_b = 0.0
    for cd, cm, cmp_, cf, coef_b in _TERMS_B:
        arg = cd * d + cm * m + cmp_ * m_prime + cf * f
        if cm == 1 or cm == -1:
            factor = e
        elif cm == 2 or cm == -2:
            factor = e2
        else:
            factor = 1.0
        sum_b += coef_b * factor * sind(arg)

    # حدود إضافية ناتجة عن تأثير الزهرة والمشتري وتفلطح الأرض
    sum_l += (3958.0 * sind(a1) + 1962.0 * sind(l_prime - f)
              + 318.0 * sind(a2))
    sum_b += (-2235.0 * sind(l_prime) + 382.0 * sind(a3)
              + 175.0 * sind(a1 - f) + 175.0 * sind(a1 + f)
              + 127.0 * sind(l_prime - m_prime) - 115.0 * sind(l_prime + m_prime))

    longitude = norm360(l_prime + sum_l / 1000000.0)
    latitude = sum_b / 1000000.0
    distance_km = 385000.56 + sum_r / 1000.0
    parallax = asind(EARTH_RADIUS_KM / distance_km)

    d_psi, d_eps = nutation(t)
    if apparent:
        longitude = norm360(longitude + d_psi)
    obliquity = mean_obliquity(t) + d_eps
    ra, dec = ecliptic_to_equatorial(longitude, latitude, obliquity)

    semidiameter = asind(0.272481 * sind(parallax))
    return MoonPosition(jde, longitude, latitude, distance_km, parallax,
                        ra, dec, semidiameter)


# ---------------------------------------------------------------------------
# الأطوار والإضاءة
# ---------------------------------------------------------------------------

PHASE_NAMES_AR = [
    "المحاق", "الهلال المتزايد", "التربيع الأول", "الأحدب المتزايد",
    "البدر", "الأحدب المتناقص", "التربيع الأخير", "الهلال المتناقص",
]

SYNODIC_MONTH = 29.530588853


def moon_phase_info(jde):
    """معلومات طور القمر: الزاوية والإضاءة والعمر والاسم العربي.

    يعيد قاموسًا يحوي:
      ``elongation`` الاستطالة عن الشمس بالدرجات (0=المحاق، 180=البدر)،
      ``illumination`` نسبة القرص المضيء (0..1)،
      ``age_days`` عمر القمر بالأيام منذ المحاق،
      ``phase_name`` اسم الطور بالعربية،
      ``waxing`` هل القمر متزايد.
    """
    moon = moon_position(jde)
    sun = sun_apparent(jde)

    elongation = angular_separation(moon.right_ascension, moon.declination,
                                    sun.right_ascension, sun.declination)

    # زاوية الطور: الزاوية شمس-قمر-أرض
    sun_distance_km = sun.distance_au * 149597870.7
    phase_angle = atan2d(
        sun_distance_km * sind(elongation),
        moon.distance_km - sun_distance_km * cosd(elongation))
    illumination = (1.0 + cosd(phase_angle)) / 2.0

    # الفرق الطولي شمس-قمر يحدد الطور واتجاهه
    delta_lon = norm360(moon.longitude - sun.longitude)
    age_days = delta_lon / 360.0 * SYNODIC_MONTH
    waxing = delta_lon < 180.0

    index = int((delta_lon + 22.5) % 360.0 // 45.0)
    return {
        "elongation": elongation,
        "phase_angle": phase_angle,
        "illumination": illumination,
        "age_days": age_days,
        "delta_longitude": delta_lon,
        "waxing": waxing,
        "phase_name": PHASE_NAMES_AR[index],
        "moon": moon,
        "sun": sun,
    }


def _phase_difference(jde, target_deg):
    """الفرق بين الطول النسبي للقمر والقيمة المطلوبة، ضمن (-180, 180]."""
    moon = moon_position(jde)
    sun = sun_apparent(jde)
    diff = (moon.longitude - sun.longitude - target_deg) % 360.0
    if diff > 180.0:
        diff -= 360.0
    return diff


def next_moon_phase(jde_start, target_deg):
    """أقرب لحظة بعد ``jde_start`` يبلغ فيها الفرق الطولي القيمة المطلوبة.

    ``target_deg``: 0 للمحاق، 90 للتربيع الأول، 180 للبدر، 270 للتربيع الأخير.
    """
    diff = _phase_difference(jde_start, target_deg)
    # تقدير أولي: القمر يتقدم على الشمس بنحو 12.19 درجة يوميًا
    jde = jde_start + (-diff) / 12.1907
    if jde < jde_start:
        jde += SYNODIC_MONTH

    for _ in range(30):
        diff = _phase_difference(jde, target_deg)
        step = -diff / 12.1907
        jde += step
        if abs(step) < 1e-6:
            break
    if jde < jde_start:
        jde += SYNODIC_MONTH
        for _ in range(30):
            diff = _phase_difference(jde, target_deg)
            step = -diff / 12.1907
            jde += step
            if abs(step) < 1e-6:
                break
    return jde


def upcoming_phases(jde_start):
    """قائمة الأطوار الأربعة القادمة مرتبة زمنيًا."""
    names = [(0.0, "المحاق"), (90.0, "التربيع الأول"),
             (180.0, "البدر"), (270.0, "التربيع الأخير")]
    result = [(next_moon_phase(jde_start, target), name)
              for target, name in names]
    result.sort()
    return result


# ---------------------------------------------------------------------------
# المنازل القمرية العربية الثماني والعشرون
# ---------------------------------------------------------------------------

LUNAR_MANSIONS_AR = [
    "الشَّرَطان", "البُطَين", "الثُّرَيّا", "الدَّبَران", "الهَقعَة", "الهَنعَة",
    "الذِّراع", "النَّثرَة", "الطَّرْف", "الجَبهَة", "الزُّبرَة", "الصَّرفَة",
    "العَوّاء", "السِّماك", "الغَفْر", "الزُّبانى", "الإكليل", "القَلْب",
    "الشَّولَة", "النَّعائم", "البَلدَة", "سعد الذابح", "سعد بُلَع",
    "سعد السُّعود", "سعد الأخبية", "الفَرْغ المُقَدَّم", "الفَرْغ المُؤَخَّر",
    "بَطْن الحوت",
]

MANSION_WIDTH = 360.0 / 28.0  # 12° 51′ 26″


def ayanamsa(jde):
    """مقدار فرق الاعتدالين (لاهيري تقريبًا) بالدرجات.

    يُستخدم لتحويل الطول المداري الاستوائي إلى طول نجمي، لأن المنازل
    القمرية العربية مرتبطة بمجموعات نجمية ثابتة لا بنقطة الاعتدال.
    """
    years = (jde - 2451545.0) / 365.25
    return 23.85 + 0.0139673 * years


def lunar_mansion(longitude_tropical, jde):
    """المنزلة القمرية التي يقع فيها طول كسوفي معطى.

    يعيد (اسم المنزلة، رقمها 1..28، الدرجة داخلها).
    """
    sidereal = norm360(longitude_tropical - ayanamsa(jde))
    index = int(sidereal // MANSION_WIDTH)
    within = sidereal - index * MANSION_WIDTH
    return LUNAR_MANSIONS_AR[index], index + 1, within


def moon_libration_note(moon):
    """ملاحظة قصيرة عن قرب القمر أو بعده (الحضيض والأوج)."""
    if moon.distance_km < 362600:
        return "القمر قرب الحضيض (أقرب نقطة) فيبدو أكبر حجمًا"
    if moon.distance_km > 405400:
        return "القمر قرب الأوج (أبعد نقطة) فيبدو أصغر حجمًا"
    return ""
