# -*- coding: utf-8 -*-
"""موقع الشمس الظاهري (ميوس، الفصل 25).

الدقة المتوقعة في الطول أفضل من 0.01 درجة خلال القرون القريبة.
"""

from __future__ import division

from .angles import cosd, norm360, sind
from .coords import ecliptic_to_equatorial, mean_obliquity, nutation
from .timeutil import julian_centuries

__all__ = ["sun_geometric_longitude", "sun_apparent", "SunPosition"]


class SunPosition(object):
    """موقع الشمس الظاهري في لحظة معطاة."""

    __slots__ = ("jde", "longitude", "latitude", "distance_au",
                 "right_ascension", "declination", "semidiameter")

    def __init__(self, jde, longitude, latitude, distance_au,
                 right_ascension, declination, semidiameter):
        self.jde = jde
        self.longitude = longitude
        self.latitude = latitude
        self.distance_au = distance_au
        self.right_ascension = right_ascension
        self.declination = declination
        self.semidiameter = semidiameter


def sun_geometric_longitude(jde):
    """الطول الكسوفي الهندسي للشمس ومسافتها (بالوحدة الفلكية)."""
    t = julian_centuries(jde)

    l0 = norm360(280.46646 + 36000.76983 * t + 0.0003032 * t * t)
    m = norm360(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    e = 0.016708634 - 0.000042037 * t - 0.0000001267 * t * t

    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * sind(m)
         + (0.019993 - 0.000101 * t) * sind(2 * m)
         + 0.000289 * sind(3 * m))

    true_longitude = l0 + c
    true_anomaly = m + c
    radius = (1.000001018 * (1 - e * e)) / (1 + e * cosd(true_anomaly))
    return norm360(true_longitude), radius


def sun_apparent(jde):
    """الموقع الظاهري للشمس: الطول والمطلع المستقيم والميل."""
    t = julian_centuries(jde)
    true_longitude, radius = sun_geometric_longitude(jde)

    omega = 125.04 - 1934.136 * t
    # تصحيح الانحراف السنوي وتقلقل الطول مدمجان في المعامل 0.00569
    apparent_longitude = true_longitude - 0.00569 - 0.00478 * sind(omega)

    d_psi, d_eps = nutation(t)
    obliquity = mean_obliquity(t) + d_eps
    ra, dec = ecliptic_to_equatorial(apparent_longitude, 0.0, obliquity)

    semidiameter = 0.2666 / radius  # نصف القطر الظاهري بالدرجات
    return SunPosition(jde, norm360(apparent_longitude), 0.0, radius,
                       ra, dec, semidiameter)


def equation_of_time_minutes(jde):
    """معادلة الزمن بالدقائق (الفرق بين الزمن الشمسي الحقيقي والوسطي)."""
    t = julian_centuries(jde)
    l0 = norm360(280.4664567 + 360007.6982779 * (t / 10.0)
                 + 0.03032028 * (t / 10.0) ** 2)
    sun = sun_apparent(jde)
    d_psi, d_eps = nutation(t)
    obliquity = mean_obliquity(t) + d_eps

    e = l0 - 0.0057183 - sun.right_ascension + d_psi * cosd(obliquity)
    e = (e + 180.0) % 360.0 - 180.0
    return e * 4.0
