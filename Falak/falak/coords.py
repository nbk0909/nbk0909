# -*- coding: utf-8 -*-
"""وحدة الإحداثيات: ميل دائرة البروج، التقلقل، التقديم، والتحويلات.

تشمل التحويل بين الإحداثيات الكسوفية والاستوائية والأفقية، وتصحيح
الانكسار الجوي والاختلاف اليومي (المنظر) للأجرام القريبة كالقمر.
"""

from __future__ import division

import math

from .angles import (acosd, asind, atan2d, cosd, norm360, rad, sind, tand)

__all__ = [
    "mean_obliquity", "nutation", "true_obliquity", "ecliptic_to_equatorial",
    "equatorial_to_ecliptic", "equatorial_to_horizontal", "refraction",
    "precession_matrix", "apply_matrix", "spherical_to_vector",
    "vector_to_spherical", "angular_separation", "topocentric",
]

# سرعة الضوء بالوحدات الفلكية في اليوم
LIGHT_SPEED_AU_PER_DAY = 173.1446326847


def mean_obliquity(t):
    """ميل دائرة البروج المتوسط بالدرجات (ميوس 22.2)، t بالقرون من J2000."""
    seconds = (84381.448 - 46.8150 * t - 0.00059 * t * t
               + 0.001813 * t * t * t)
    return seconds / 3600.0


def nutation(t):
    """التقلقل في الطول والميل بالدرجات (صيغة ميوس المختصرة، دقة ≈0.5″)."""
    omega = 125.04452 - 1934.136261 * t
    l_sun = 280.4665 + 36000.7698 * t
    l_moon = 218.3165 + 481267.8813 * t

    d_psi = (-17.20 * sind(omega) - 1.32 * sind(2 * l_sun)
             - 0.23 * sind(2 * l_moon) + 0.21 * sind(2 * omega))
    d_eps = (9.20 * cosd(omega) + 0.57 * cosd(2 * l_sun)
             + 0.10 * cosd(2 * l_moon) - 0.09 * cosd(2 * omega))
    return d_psi / 3600.0, d_eps / 3600.0


def true_obliquity(t):
    """ميل دائرة البروج الحقيقي بالدرجات."""
    d_psi, d_eps = nutation(t)
    return mean_obliquity(t) + d_eps


def ecliptic_to_equatorial(lon, lat, obliquity):
    """تحويل (طول، عرض) كسوفي إلى (مطلع مستقيم، ميل) بالدرجات."""
    sin_lat = sind(lat)
    cos_lat = cosd(lat)
    ra = atan2d(sind(lon) * cosd(obliquity) - tand(lat) * sind(obliquity),
                cosd(lon))
    dec = asind(sin_lat * cosd(obliquity)
                + cos_lat * sind(obliquity) * sind(lon))
    return norm360(ra), dec


def equatorial_to_ecliptic(ra, dec, obliquity):
    """تحويل (مطلع مستقيم، ميل) إلى (طول، عرض) كسوفي بالدرجات."""
    lon = atan2d(sind(ra) * cosd(obliquity) + tand(dec) * sind(obliquity),
                 cosd(ra))
    lat = asind(sind(dec) * cosd(obliquity)
                - cosd(dec) * sind(obliquity) * sind(ra))
    return norm360(lon), lat


def equatorial_to_horizontal(hour_angle, dec, latitude):
    """تحويل (زاوية ساعية، ميل) إلى (سمت، ارتفاع) بالدرجات.

    السمت مقيس من الشمال باتجاه الشرق (0° شمال، 90° شرق).
    """
    sin_alt = (sind(latitude) * sind(dec)
               + cosd(latitude) * cosd(dec) * cosd(hour_angle))
    alt = asind(sin_alt)
    az = atan2d(sind(hour_angle),
                cosd(hour_angle) * sind(latitude) - tand(dec) * cosd(latitude))
    # صيغة ميوس تعطي السمت من الجنوب؛ نضيف 180° ليصبح من الشمال
    return norm360(az + 180.0), alt


def refraction(apparent_altitude):
    """الانكسار الجوي بالدرجات لارتفاع ظاهري معطى (ميوس 16.4).

    القيمة المعادة تُطرح من الارتفاع الظاهري للحصول على الحقيقي.
    """
    if apparent_altitude < -2.0:
        return 0.0
    r = 1.02 / tand(apparent_altitude + 10.3 / (apparent_altitude + 5.11))
    return r / 60.0


def refraction_true_to_apparent(true_altitude):
    """الانكسار الجوي بالدرجات يُضاف لارتفاع حقيقي ليصبح ظاهريًا."""
    if true_altitude < -2.0:
        return 0.0
    r = 1.02 / tand(true_altitude + 10.3 / (true_altitude + 5.11))
    return r / 60.0


# ---------------------------------------------------------------------------
# المتجهات ومصفوفة التقديم (البدارية)
# ---------------------------------------------------------------------------

def spherical_to_vector(lon, lat, radius=1.0):
    """تحويل إحداثيات كروية بالدرجات إلى متجه ديكارتي."""
    return (radius * cosd(lat) * cosd(lon),
            radius * cosd(lat) * sind(lon),
            radius * sind(lat))


def vector_to_spherical(v):
    """تحويل متجه ديكارتي إلى (طول، عرض، نصف قطر)."""
    x, y, z = v
    r = math.sqrt(x * x + y * y + z * z)
    if r == 0.0:
        return 0.0, 0.0, 0.0
    return norm360(atan2d(y, x)), asind(z / r), r


def apply_matrix(m, v):
    """ضرب مصفوفة 3×3 في متجه."""
    return (m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2])


def precession_matrix(t):
    """مصفوفة التقديم الاستوائي من J2000 إلى الاعتدال الوسطي للتاريخ.

    ثوابت IAU 1976 (ميوس 21.2)، و t بالقرون اليوليانية من J2000.
    """
    zeta = (2306.2181 * t + 0.30188 * t * t + 0.017998 * t ** 3) / 3600.0
    z = (2306.2181 * t + 1.09468 * t * t + 0.018203 * t ** 3) / 3600.0
    theta = (2004.3109 * t - 0.42665 * t * t - 0.041833 * t ** 3) / 3600.0

    cz, sz = cosd(zeta), sind(zeta)
    cZ, sZ = cosd(z), sind(z)
    ct, st = cosd(theta), sind(theta)

    return (
        (cz * ct * cZ - sz * sZ, -sz * ct * cZ - cz * sZ, -st * cZ),
        (cz * ct * sZ + sz * cZ, -sz * ct * sZ + cz * cZ, -st * sZ),
        (cz * st, -sz * st, ct),
    )


def apply_nutation_equatorial(ra, dec, t):
    """إضافة أثر التقلقل إلى إحداثيات استوائية وسطية للتاريخ."""
    d_psi, d_eps = nutation(t)
    eps0 = mean_obliquity(t)
    lon, lat = equatorial_to_ecliptic(ra, dec, eps0)
    return ecliptic_to_equatorial(lon + d_psi, lat, eps0 + d_eps)


def angular_separation(ra1, dec1, ra2, dec2):
    """المسافة الزاوية بالدرجات بين موقعين استوائيين."""
    cos_d = (sind(dec1) * sind(dec2)
             + cosd(dec1) * cosd(dec2) * cosd(ra1 - ra2))
    return acosd(cos_d)


def position_angle(ra1, dec1, ra2, dec2):
    """زاوية الوضع للجرم الثاني بالنسبة للأول (0° شمالًا، 90° شرقًا)."""
    d_ra = rad(ra2 - ra1)
    y = math.sin(d_ra) * cosd(dec2)
    x = (cosd(dec1) * sind(dec2)
         - sind(dec1) * cosd(dec2) * math.cos(d_ra))
    return norm360(atan2d(y, x))


# ---------------------------------------------------------------------------
# التصحيح الموضعي (الاختلاف اليومي)
# ---------------------------------------------------------------------------

def observer_rho(latitude, elevation_m):
    """معاملا الراصد ρ·sinφ′ و ρ·cosφ′ (ميوس 11)."""
    flattening = 0.99664719  # b/a للكرة الأرضية المرجعية
    u = math.atan(flattening * tand(latitude))
    rho_sin = flattening * math.sin(u) + (elevation_m / 6378140.0) * sind(latitude)
    rho_cos = math.cos(u) + (elevation_m / 6378140.0) * cosd(latitude)
    return rho_sin, rho_cos


def topocentric(ra, dec, parallax_deg, local_sidereal_deg, latitude,
                elevation_m=0.0):
    """تحويل إحداثيات مركزية أرضية إلى موضعية للراصد (ميوس 40.6).

    ``parallax_deg`` هو اختلاف المنظر الأفقي الاستوائي للجرم.
    """
    if parallax_deg <= 0.0:
        return ra, dec
    rho_sin, rho_cos = observer_rho(latitude, elevation_m)
    sin_pi = sind(parallax_deg)
    hour_angle = local_sidereal_deg - ra

    d_ra = atan2d(-rho_cos * sin_pi * sind(hour_angle),
                  cosd(dec) - rho_cos * sin_pi * cosd(hour_angle))
    ra_topo = norm360(ra + d_ra)
    dec_topo = atan2d((sind(dec) - rho_sin * sin_pi) * cosd(d_ra),
                      cosd(dec) - rho_cos * sin_pi * cosd(hour_angle))
    return ra_topo, dec_topo
