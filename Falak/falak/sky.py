# -*- coding: utf-8 -*-
"""واجهة موحّدة للأجرام السماوية، وحساب أوقات الشروق والغروب والعبور.

الطريقة المتبعة لأوقات الشروق والغروب: تُحسب الإحداثيات الاستوائية في
خمس لحظات موزّعة على اليوم، ثم يُستوفى بينها بكثير حدود لاغرانج، ويُمسح
اليوم بخطوات من أربع دقائق للبحث عن لحظات عبور الارتفاع الحرج، ثم تُنقَّح
بطريقة التنصيف حتى دقة ثانية واحدة. هذا الأسلوب يصلح لجميع الأجرام بما
فيها القمر السريع الحركة، ولا يفشل قرب القطبين.
"""

from __future__ import division

from .angles import cosd, norm360
from .coords import (equatorial_to_horizontal,
                     refraction_true_to_apparent, topocentric)
from .moon import moon_position
from .planets import PLANET_ORDER, planet_geocentric
from .stars import STARS, star_apparent
from .sun import sun_apparent
from .timeutil import (delta_t_seconds, gmst_degrees, julian_centuries,
                       julian_day)
from .coords import mean_obliquity, nutation

__all__ = ["Body", "make_bodies", "BodyState", "DayEvents", "compute_events",
           "body_state", "twilight_times", "SUN_KEY", "MOON_KEY"]

SUN_KEY = "الشمس"
MOON_KEY = "القمر"

STANDARD_ALTITUDE = -0.5667  # الانكسار عند الأفق بالدرجات
SUN_ALTITUDE = -0.8333       # الانكسار + نصف قطر الشمس


# ---------------------------------------------------------------------------
# تعريف الأجرام
# ---------------------------------------------------------------------------

class Body(object):
    """جرم سماوي قابل للحساب: الشمس أو القمر أو كوكب أو نجم."""

    __slots__ = ("key", "name", "kind", "_star")

    def __init__(self, key, name, kind, star=None):
        self.key = key
        self.name = name
        self.kind = kind  # 'sun' | 'moon' | 'planet' | 'star'
        self._star = star

    def equatorial(self, jde):
        """يعيد (مطلع مستقيم، ميل، اختلاف المنظر بالدرجات)."""
        if self.kind == "sun":
            pos = sun_apparent(jde)
            # اختلاف منظر الشمس ضئيل (≈8.8″) لكنه يُدرج للاكتمال
            parallax = 8.794 / 3600.0 / pos.distance_au
            return pos.right_ascension, pos.declination, parallax
        if self.kind == "moon":
            pos = moon_position(jde)
            return pos.right_ascension, pos.declination, pos.parallax
        if self.kind == "planet":
            pos = planet_geocentric(self.name, jde)
            return pos.right_ascension, pos.declination, 0.0
        ra, dec = star_apparent(self._star, jde)
        return ra, dec, 0.0

    def horizon_altitude(self, jde):
        """الارتفاع الحرج للشروق والغروب بالدرجات."""
        if self.kind == "sun":
            return SUN_ALTITUDE
        if self.kind == "moon":
            pos = moon_position(jde)
            # الحساب موضعي (topocentric) لذا يُطرح نصف القطر الظاهري
            return STANDARD_ALTITUDE - pos.semidiameter
        return STANDARD_ALTITUDE

    @property
    def star(self):
        return self._star


def make_bodies(include_stars=0, include_pluto=False):
    """بناء قائمة الأجرام الافتراضية: الشمس والقمر والكواكب."""
    bodies = [Body(SUN_KEY, SUN_KEY, "sun"), Body(MOON_KEY, MOON_KEY, "moon")]
    for name in PLANET_ORDER:
        bodies.append(Body(name, name, "planet"))
    if include_pluto:
        bodies.append(Body("بلوتو", "بلوتو", "planet"))
    if include_stars:
        for star in sorted(STARS, key=lambda s: s.magnitude)[:include_stars]:
            bodies.append(Body("نجم:" + star.name_ar, star.name_ar, "star",
                               star))
    return bodies


def star_body(star):
    """إنشاء جرم من نجم في الفهرس."""
    return Body("نجم:" + star.name_ar, star.name_ar, "star", star)


# ---------------------------------------------------------------------------
# الحالة اللحظية للجرم
# ---------------------------------------------------------------------------

class BodyState(object):
    """حالة جرم في لحظة محددة بالنسبة لراصد."""

    __slots__ = ("body", "jd", "right_ascension", "declination", "azimuth",
                 "altitude", "altitude_apparent", "hour_angle", "extra")

    def __init__(self, body, jd, ra, dec, az, alt, alt_app, hour_angle,
                 extra=None):
        self.body = body
        self.jd = jd
        self.right_ascension = ra
        self.declination = dec
        self.azimuth = az
        self.altitude = alt
        self.altitude_apparent = alt_app
        self.hour_angle = hour_angle
        self.extra = extra or {}

    @property
    def is_up(self):
        return self.altitude_apparent > 0.0

    @property
    def direction_ar(self):
        return azimuth_to_arabic(self.azimuth)


_DIRECTIONS = [
    (0, "شمال"), (22.5, "شمال شرق"), (67.5, "شرق"), (112.5, "جنوب شرق"),
    (157.5, "جنوب"), (202.5, "جنوب غرب"), (247.5, "غرب"),
    (292.5, "شمال غرب"), (337.5, "شمال"),
]


def azimuth_to_arabic(azimuth):
    """تحويل السمت بالدرجات إلى جهة بالعربية."""
    az = norm360(azimuth)
    names = ["شمال", "شمال شرق", "شرق", "جنوب شرق", "جنوب",
             "جنوب غرب", "غرب", "شمال غرب"]
    index = int((az + 22.5) // 45.0) % 8
    return names[index]


def local_sidereal(jd_ut, longitude_east):
    """الزمن النجمي الظاهري المحلي بالدرجات."""
    t = julian_centuries(jd_ut)
    d_psi, d_eps = nutation(t)
    eps = mean_obliquity(t) + d_eps
    return norm360(gmst_degrees(jd_ut) + d_psi * cosd(eps) + longitude_east)


def body_state(body, jd_ut, observer):
    """حساب الحالة اللحظية لجرم (موضعية، مع الانكسار الجوي)."""
    jde = jd_ut + delta_t_seconds(jd_ut) / 86400.0
    ra, dec, parallax = body.equatorial(jde)
    lst = local_sidereal(jd_ut, observer.longitude)
    if parallax > 0.0:
        ra, dec = topocentric(ra, dec, parallax, lst, observer.latitude,
                              observer.elevation)
    hour_angle = norm360(lst - ra)
    az, alt = equatorial_to_horizontal(hour_angle, dec, observer.latitude)
    alt_app = alt + refraction_true_to_apparent(alt)
    return BodyState(body, jd_ut, ra, dec, az, alt, alt_app, hour_angle)


# ---------------------------------------------------------------------------
# الاستيفاء وأوقات الأحداث
# ---------------------------------------------------------------------------

def _lagrange(xs, ys, x):
    """استيفاء لاغرانج لمجموعة نقاط قليلة."""
    total = 0.0
    n = len(xs)
    for i in range(n):
        term = ys[i]
        for j in range(n):
            if i != j:
                term *= (x - xs[j]) / (xs[i] - xs[j])
        total += term
    return total


class _Track(object):
    """مسار جرم خلال يوم واحد، معتمدًا على الاستيفاء بين عُقد محسوبة."""

    def __init__(self, body, jd_start, observer, nodes=5):
        self.body = body
        self.observer = observer
        self.jd_start = jd_start
        self.xs = []
        self.ra = []
        self.dec = []
        self.parallax = []

        previous_ra = None
        for i in range(nodes):
            jd = jd_start + i / (nodes - 1.0)
            jde = jd + delta_t_seconds(jd) / 86400.0
            ra, dec, par = body.equatorial(jde)
            if previous_ra is not None:
                # فك التفاف المطلع المستقيم ليصبح متصلًا
                while ra - previous_ra > 180.0:
                    ra -= 360.0
                while ra - previous_ra < -180.0:
                    ra += 360.0
            previous_ra = ra
            self.xs.append(jd)
            self.ra.append(ra)
            self.dec.append(dec)
            self.parallax.append(par)

        mid_jde = jd_start + 0.5
        self.h0 = body.horizon_altitude(mid_jde
                                        + delta_t_seconds(mid_jde) / 86400.0)

    def radec(self, jd):
        return (_lagrange(self.xs, self.ra, jd),
                _lagrange(self.xs, self.dec, jd),
                _lagrange(self.xs, self.parallax, jd))

    def altitude(self, jd):
        """الارتفاع الحقيقي الموضعي بالدرجات عند لحظة معطاة."""
        ra, dec, par = self.radec(jd)
        lst = local_sidereal(jd, self.observer.longitude)
        if par > 0.0:
            ra, dec = topocentric(ra, dec, par, lst, self.observer.latitude,
                                  self.observer.elevation)
        hour_angle = lst - ra
        _, alt = equatorial_to_horizontal(hour_angle, dec,
                                          self.observer.latitude)
        return alt

    def azimuth(self, jd):
        ra, dec, par = self.radec(jd)
        lst = local_sidereal(jd, self.observer.longitude)
        if par > 0.0:
            ra, dec = topocentric(ra, dec, par, lst, self.observer.latitude,
                                  self.observer.elevation)
        az, _ = equatorial_to_horizontal(lst - ra, dec,
                                         self.observer.latitude)
        return az


class DayEvents(object):
    """أحداث جرم خلال يوم محلي واحد."""

    __slots__ = ("body", "rise", "transit", "set", "max_altitude",
                 "peak_hour", "rise_azimuth", "set_azimuth", "always_up",
                 "always_down")

    def __init__(self, body):
        self.body = body
        self.rise = None
        self.transit = None
        self.set = None
        self.max_altitude = None
        self.peak_hour = None
        self.rise_azimuth = None
        self.set_azimuth = None
        self.always_up = False
        self.always_down = False


def _bisect(func, a, b, tolerance=1.0 / 86400.0):
    """إيجاد جذر دالة بين نقطتين بطريقة التنصيف."""
    fa = func(a)
    for _ in range(60):
        mid = (a + b) / 2.0
        fm = func(mid)
        if (b - a) < tolerance:
            return mid
        if (fa < 0) == (fm < 0):
            a, fa = mid, fm
        else:
            b = mid
    return (a + b) / 2.0


def compute_events(body, jd_local_midnight, observer, step_minutes=4.0):
    """حساب الشروق والعبور والغروب لجرم خلال اليوم المحلي المعطى.

    ``jd_local_midnight`` هو اليوم اليولياني (UT) للحظة منتصف الليل المحلي.
    الأوقات المعادة بالساعات المحلية من منتصف الليل.
    """
    track = _Track(body, jd_local_midnight, observer)
    events = DayEvents(body)

    step = step_minutes / 1440.0
    count = int(round(1.0 / step))

    samples = []
    for i in range(count + 1):
        jd = jd_local_midnight + i * step
        samples.append((jd, track.altitude(jd)))

    above = [alt > track.h0 for _, alt in samples]
    if all(above):
        events.always_up = True
    elif not any(above):
        events.always_down = True

    for i in range(count):
        jd0, alt0 = samples[i]
        jd1, alt1 = samples[i + 1]
        if (alt0 - track.h0) == 0.0:
            continue
        if (alt0 > track.h0) != (alt1 > track.h0):
            crossing = _bisect(lambda x: track.altitude(x) - track.h0,
                               jd0, jd1)
            hours = (crossing - jd_local_midnight) * 24.0
            if alt1 > alt0:
                if events.rise is None:
                    events.rise = hours
                    events.rise_azimuth = track.azimuth(crossing)
            else:
                if events.set is None:
                    events.set = hours
                    events.set_azimuth = track.azimuth(crossing)

    # العبور: أعلى ارتفاع خلال اليوم، يُنقَّح بالبحث الثلاثي
    best_index = max(range(len(samples)), key=lambda i: samples[i][1])
    lo = samples[max(0, best_index - 1)][0]
    hi = samples[min(len(samples) - 1, best_index + 1)][0]
    for _ in range(60):
        if hi - lo < 1.0 / 86400.0:
            break
        m1 = lo + (hi - lo) / 3.0
        m2 = hi - (hi - lo) / 3.0
        if track.altitude(m1) < track.altitude(m2):
            lo = m1
        else:
            hi = m2
    peak = (lo + hi) / 2.0
    events.max_altitude = track.altitude(peak)
    events.peak_hour = (peak - jd_local_midnight) * 24.0
    if events.max_altitude > track.h0:
        events.transit = events.peak_hour
    return events


def twilight_times(jd_local_midnight, observer, depression=18.0):
    """أوقات الشفق: يعيد (بداية الفجر، نهاية الشفق) بالساعات المحلية.

    ``depression``: 6 للشفق المدني، 12 للبحري، 18 للفلكي.
    """
    body = Body(SUN_KEY, SUN_KEY, "sun")
    track = _Track(body, jd_local_midnight, observer)
    target = -depression

    step = 4.0 / 1440.0
    count = int(round(1.0 / step))
    samples = []
    for i in range(count + 1):
        jd = jd_local_midnight + i * step
        samples.append((jd, track.altitude(jd)))

    dawn = dusk = None
    for i in range(count):
        jd0, alt0 = samples[i]
        jd1, alt1 = samples[i + 1]
        if (alt0 > target) != (alt1 > target):
            crossing = _bisect(lambda x: track.altitude(x) - target, jd0, jd1)
            hours = (crossing - jd_local_midnight) * 24.0
            if alt1 > alt0 and dawn is None:
                dawn = hours
            elif alt1 < alt0 and dusk is None:
                dusk = hours
    return dawn, dusk


# ---------------------------------------------------------------------------
# أدوات مساعدة للتاريخ المحلي
# ---------------------------------------------------------------------------

def local_midnight_jd(year, month, day, observer):
    """اليوم اليولياني (UT) للحظة منتصف الليل المحلي لتاريخ معطى."""
    return julian_day(year, month, day) - observer.tz_offset / 24.0


def jd_from_local(year, month, day, hours, observer):
    """تحويل تاريخ ووقت محليين إلى يوم يولياني بالتوقيت العالمي."""
    return julian_day(year, month, day + hours / 24.0) - observer.tz_offset / 24.0


def local_hours(jd_ut, jd_local_midnight):
    """تحويل يوم يولياني إلى ساعات محلية منذ منتصف الليل."""
    return (jd_ut - jd_local_midnight) * 24.0
