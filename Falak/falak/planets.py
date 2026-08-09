# -*- coding: utf-8 -*-
"""مواقع الكواكب اعتمادًا على العناصر المدارية التقريبية (Standish/JPL).

الجدول صالح للحقبة 1800–2050 م بدقة تتراوح بين عدة ثوانٍ قوسية
للكواكب الداخلية وبضع دقائق قوسية للكواكب الخارجية — وهي دقة أكثر
من كافية للرصد بالعين المجردة أو بتلسكوب صغير.

المرجع: E. M. Standish, "Keplerian Elements for Approximate Positions
of the Major Planets", JPL Solar System Dynamics.
"""

from __future__ import division

import math

from .angles import cosd, norm180, norm360, sind
from .coords import (LIGHT_SPEED_AU_PER_DAY, apply_matrix,
                     apply_nutation_equatorial, precession_matrix,
                     vector_to_spherical)
from .timeutil import julian_centuries

__all__ = ["PLANET_NAMES_AR", "planet_geocentric", "PlanetPosition",
           "earth_heliocentric", "PLANET_ORDER"]

# ميل دائرة البروج عند حقبة J2000.0
OBLIQUITY_J2000 = 84381.448 / 3600.0

# العناصر المدارية عند J2000 ومعدلات تغيرها لكل قرن يولياني:
#   a (و.ف)، e، I (°)، L (°)، ϖ (°)، Ω (°)
_ELEMENTS = {
    "عطارد": (
        (0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
        (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081),
    ),
    "الزهرة": (
        (0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
        (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418),
    ),
    "الأرض": (
        (1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
        (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0),
    ),
    "المريخ": (
        (1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
        (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343),
    ),
    "المشتري": (
        (5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
        (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106),
    ),
    "زحل": (
        (9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
        (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794),
    ),
    "أورانوس": (
        (19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503),
        (-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589),
    ),
    "نبتون": (
        (30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574),
        (0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664),
    ),
    "بلوتو": (
        (39.48211675, 0.24882730, 17.14001206, 238.92903833, 224.06891629, 110.30393684),
        (-0.00031596, 0.00005170, 0.00004818, 145.20780515, -0.04062942, -0.01183482),
    ),
}

# الترتيب المعتاد للعرض (دون الأرض)
PLANET_ORDER = ["عطارد", "الزهرة", "المريخ", "المشتري", "زحل",
                "أورانوس", "نبتون"]

PLANET_NAMES_AR = list(_ELEMENTS.keys())

# نصف القطر الاستوائي بالكيلومترات (لحساب القطر الظاهري)
_RADII_KM = {
    "عطارد": 2439.7, "الزهرة": 6051.8, "المريخ": 3396.2,
    "المشتري": 71492.0, "زحل": 60268.0, "أورانوس": 25559.0,
    "نبتون": 24764.0, "بلوتو": 1188.3,
}

AU_KM = 149597870.7


class PlanetPosition(object):
    """موقع كوكب ظاهري مركزي أرضي."""

    __slots__ = ("name", "jde", "right_ascension", "declination",
                 "ecliptic_longitude", "ecliptic_latitude", "distance_au",
                 "heliocentric_distance_au", "elongation", "phase_angle",
                 "illumination", "magnitude", "angular_diameter")

    def __init__(self, **kwargs):
        for key in self.__slots__:
            setattr(self, key, kwargs.get(key))


def _solve_kepler(mean_anomaly_deg, eccentricity):
    """حل معادلة كبلر بطريقة نيوتن-رافسون؛ يعيد الشذوذ الاختياري بالدرجات."""
    m = norm180(mean_anomaly_deg)
    e_star = math.degrees(eccentricity)
    ecc_anomaly = m + e_star * sind(m)
    for _ in range(60):
        delta_m = m - (ecc_anomaly - e_star * sind(ecc_anomaly))
        delta_e = delta_m / (1.0 - eccentricity * cosd(ecc_anomaly))
        ecc_anomaly += delta_e
        if abs(delta_e) < 1e-9:
            break
    return ecc_anomaly


def heliocentric_ecliptic_j2000(name, jde):
    """الموقع الديكارتي المركزي شمسي في مستوى دائرة البروج لحقبة J2000."""
    base, rate = _ELEMENTS[name]
    t = julian_centuries(jde)

    a = base[0] + rate[0] * t
    e = base[1] + rate[1] * t
    inc = base[2] + rate[2] * t
    mean_longitude = base[3] + rate[3] * t
    peri_longitude = base[4] + rate[4] * t
    node_longitude = base[5] + rate[5] * t

    arg_peri = peri_longitude - node_longitude
    mean_anomaly = mean_longitude - peri_longitude
    ecc_anomaly = _solve_kepler(mean_anomaly, e)

    # الإحداثيات في مستوى المدار
    x_orb = a * (cosd(ecc_anomaly) - e)
    y_orb = a * math.sqrt(max(0.0, 1.0 - e * e)) * sind(ecc_anomaly)

    cw, sw = cosd(arg_peri), sind(arg_peri)
    cO, sO = cosd(node_longitude), sind(node_longitude)
    ci, si = cosd(inc), sind(inc)

    x = (cw * cO - sw * sO * ci) * x_orb + (-sw * cO - cw * sO * ci) * y_orb
    y = (cw * sO + sw * cO * ci) * x_orb + (-sw * sO + cw * cO * ci) * y_orb
    z = (sw * si) * x_orb + (cw * si) * y_orb
    return x, y, z


def earth_heliocentric(jde):
    """موقع الأرض (مركز ثقل الأرض-القمر) المركزي شمسي عند لحظة معطاة."""
    return heliocentric_ecliptic_j2000("الأرض", jde)


def earth_velocity(jde):
    """سرعة الأرض بالوحدة الفلكية في اليوم (بالتفاضل العددي)."""
    step = 0.5
    p1 = earth_heliocentric(jde - step)
    p2 = earth_heliocentric(jde + step)
    return tuple((p2[i] - p1[i]) / (2.0 * step) for i in range(3))


def _ecliptic_to_equatorial_vector(v):
    """تدوير متجه من مستوى البروج لحقبة J2000 إلى المستوى الاستوائي."""
    ce, se = cosd(OBLIQUITY_J2000), sind(OBLIQUITY_J2000)
    x, y, z = v
    return (x, y * ce - z * se, y * se + z * ce)


def apparent_from_geometric(vector_eq_j2000, jde, add_aberration=True):
    """تحويل متجه استوائي هندسي (J2000) إلى مطلع مستقيم وميل ظاهريين."""
    v = list(vector_eq_j2000)

    if add_aberration:
        vel = _ecliptic_to_equatorial_vector(earth_velocity(jde))
        distance = math.sqrt(sum(c * c for c in v))
        for i in range(3):
            v[i] += vel[i] * distance / LIGHT_SPEED_AU_PER_DAY

    t = julian_centuries(jde)
    v = apply_matrix(precession_matrix(t), v)
    lon, lat, r = vector_to_spherical(v)
    ra, dec = apply_nutation_equatorial(lon, lat, t)
    return ra, dec, r


def planet_magnitude(name, r, delta, phase_angle):
    """تقدير القدر الظاهري للكوكب (صيغ التقويم الفلكي الأمريكي).

    الدقة نحو 0.1 قدر للكواكب الداخلية، وتقل لزحل بسبب إهمال ميل الحلقات.
    """
    if r <= 0 or delta <= 0:
        return None
    base = 5.0 * math.log10(r * delta)
    i = phase_angle
    if name == "عطارد":
        return -0.42 + base + 0.0380 * i - 0.000273 * i ** 2 + 0.000002 * i ** 3
    if name == "الزهرة":
        return -4.40 + base + 0.0009 * i + 0.000239 * i ** 2 - 0.00000065 * i ** 3
    if name == "المريخ":
        return -1.52 + base + 0.016 * i
    if name == "المشتري":
        return -9.40 + base + 0.005 * i
    if name == "زحل":
        return -8.88 + base
    if name == "أورانوس":
        return -7.19 + base
    if name == "نبتون":
        return -6.87 + base
    if name == "بلوتو":
        return -1.00 + base
    return None


def planet_geocentric(name, jde):
    """الموقع الظاهري المركزي أرضي لكوكب، مع تصحيح زمن الضوء والانحراف."""
    earth = earth_heliocentric(jde)

    # تصحيح زمن الضوء بالتكرار
    light_time = 0.0
    planet = heliocentric_ecliptic_j2000(name, jde)
    for _ in range(3):
        geo = tuple(planet[i] - earth[i] for i in range(3))
        distance = math.sqrt(sum(c * c for c in geo))
        light_time = distance / LIGHT_SPEED_AU_PER_DAY
        planet = heliocentric_ecliptic_j2000(name, jde - light_time)

    geo_ecl = tuple(planet[i] - earth[i] for i in range(3))
    distance = math.sqrt(sum(c * c for c in geo_ecl))
    geo_eq = _ecliptic_to_equatorial_vector(geo_ecl)
    ra, dec, _ = apparent_from_geometric(geo_eq, jde)

    # الطول والعرض الكسوفيان لتاريخ الرصد (لتحديد البرج)
    from .coords import equatorial_to_ecliptic, true_obliquity
    t = julian_centuries(jde)
    lon, lat = equatorial_to_ecliptic(ra, dec, true_obliquity(t))

    r_helio = math.sqrt(sum(c * c for c in planet))
    r_earth = math.sqrt(sum(c * c for c in earth))

    # زاوية الطور (شمس-كوكب-أرض) والاستطالة (شمس-أرض-كوكب)
    if r_helio > 0 and distance > 0:
        cos_phase = ((r_helio ** 2 + distance ** 2 - r_earth ** 2)
                     / (2.0 * r_helio * distance))
        phase_angle = math.degrees(math.acos(max(-1.0, min(1.0, cos_phase))))
        cos_elong = ((r_earth ** 2 + distance ** 2 - r_helio ** 2)
                     / (2.0 * r_earth * distance))
        elongation = math.degrees(math.acos(max(-1.0, min(1.0, cos_elong))))
    else:
        phase_angle = 0.0
        elongation = 0.0

    illumination = (1.0 + cosd(phase_angle)) / 2.0
    radius_km = _RADII_KM.get(name, 1000.0)
    angular_diameter = 2.0 * math.degrees(
        math.atan(radius_km / (distance * AU_KM))) * 3600.0  # بالثواني القوسية

    return PlanetPosition(
        name=name, jde=jde, right_ascension=ra, declination=dec,
        ecliptic_longitude=lon, ecliptic_latitude=lat,
        distance_au=distance, heliocentric_distance_au=r_helio,
        elongation=elongation, phase_angle=phase_angle,
        illumination=illumination,
        magnitude=planet_magnitude(name, r_helio, distance, phase_angle),
        angular_diameter=angular_diameter)


def elongation_side(planet_ra, planet_lon, sun_lon):
    """تحديد جهة الاستطالة: شرق الشمس (مسائي) أم غربها (صباحي)."""
    diff = norm360(planet_lon - sun_lon)
    return "شرقية" if diff < 180.0 else "غربية"
