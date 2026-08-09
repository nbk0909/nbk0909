# -*- coding: utf-8 -*-
"""اختبارات التحقق من دقة الحسابات الفلكية.

القيم المرجعية مأخوذة من أمثلة كتاب Jean Meeus «Astronomical Algorithms»
ومن بيانات JPL Horizons.
"""

from __future__ import division

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falak.coords import angular_separation, mean_obliquity, nutation
from falak.events import daily_forecast
from falak.hijri import hijri_to_jd, jd_to_hijri
from falak.locations import CITIES, Observer
from falak.moon import moon_position, next_moon_phase
from falak.planets import planet_geocentric
from falak.sky import (MOON_KEY, SUN_KEY, Body, compute_events,
                       local_midnight_jd, twilight_times)
from falak.stars import STARS, star_apparent
from falak.sun import sun_apparent
from falak.timeutil import (calendar_from_jd, julian_centuries, julian_day)


class TestTime(unittest.TestCase):
    def test_j2000(self):
        self.assertAlmostEqual(julian_day(2000, 1, 1.5), 2451545.0, places=6)

    def test_meeus_examples(self):
        # مثال 7.أ: 1957 أكتوبر 4.81 -> 2436116.31
        self.assertAlmostEqual(julian_day(1957, 10, 4.81), 2436116.31, places=5)
        # مثال 7.ب: 333 يناير 27.5 (تقويم يولياني) -> 1842713.0
        self.assertAlmostEqual(julian_day(333, 1, 27.5), 1842713.0, places=5)

    def test_roundtrip(self):
        for jd in (2451545.0, 2436116.31, 2400000.5, 2460000.75):
            year, month, day = calendar_from_jd(jd)
            self.assertAlmostEqual(julian_day(year, month, day), jd, places=5)


class TestObliquityNutation(unittest.TestCase):
    def test_obliquity_j2000(self):
        self.assertAlmostEqual(mean_obliquity(0.0), 23.4392911, places=6)

    def test_nutation_meeus_22a(self):
        # 1987 أبريل 10.0 TD -> Δψ = -3.788″، Δε = +9.443″
        t = julian_centuries(2446895.5)
        d_psi, d_eps = nutation(t)
        self.assertAlmostEqual(d_psi * 3600.0, -3.788, delta=0.5)
        self.assertAlmostEqual(d_eps * 3600.0, 9.443, delta=0.5)


class TestSun(unittest.TestCase):
    def test_meeus_25b(self):
        """1992 أكتوبر 13.0 TD: الطول الظاهري 199°54′21″ والميل -7°47′.″"""
        jde = 2448908.5
        sun = sun_apparent(jde)
        expected_longitude = 199 + 54 / 60.0 + 21.6 / 3600.0
        self.assertAlmostEqual(sun.longitude, expected_longitude, delta=0.01)
        # الصيغة المختصرة للبعد دقتها نحو 1e-4 و.ف مقارنة بـ VSOP87
        self.assertAlmostEqual(sun.distance_au, 0.99760775, delta=0.00015)
        expected_dec = -(7 + 47 / 60.0 + 1.7 / 3600.0)
        self.assertAlmostEqual(sun.declination, expected_dec, delta=0.01)
        expected_ra = (13 + 13 / 60.0 + 30.749 / 3600.0) * 15.0
        self.assertAlmostEqual(sun.right_ascension, expected_ra, delta=0.01)


class TestMoon(unittest.TestCase):
    def test_meeus_47a(self):
        """1992 أبريل 12.0 TD: λ=133.162655°، β=-3.229126°، Δ=368409.7 كم."""
        jde = 2448724.5
        moon = moon_position(jde, apparent=False)
        self.assertAlmostEqual(moon.longitude, 133.162655, delta=0.0005)
        self.assertAlmostEqual(moon.latitude, -3.229126, delta=0.0005)
        self.assertAlmostEqual(moon.distance_km, 368409.7, delta=1.0)
        self.assertAlmostEqual(moon.parallax, 0.991990, delta=0.0002)

    def test_new_moon_meeus_49a(self):
        """مثال ميوس 49.أ: محاق فبراير 1977 عند JDE = 2443192.65118 TD."""
        jde = next_moon_phase(julian_day(1977, 2, 14.0), 0.0)
        self.assertAlmostEqual(jde, 2443192.65118, delta=0.003)

    def test_full_moon_ordering(self):
        start = julian_day(2026, 8, 1.0)
        new_moon = next_moon_phase(start, 0.0)
        full_moon = next_moon_phase(start, 180.0)
        self.assertGreater(new_moon, start)
        self.assertGreater(full_moon, start)
        self.assertLess(new_moon - start, 30.0)
        self.assertLess(full_moon - start, 30.0)


class TestPlanets(unittest.TestCase):
    def test_venus_meeus_33a(self):
        """1992 ديسمبر 20.0 TD: α=21س04د41.5ث، δ=-18°53′17″ للزهرة."""
        jde = 2448976.5
        venus = planet_geocentric("الزهرة", jde)
        expected_ra = (21 + 4 / 60.0 + 41.454 / 3600.0) * 15.0
        expected_dec = -(18 + 53 / 60.0 + 16.84 / 3600.0)
        separation = angular_separation(venus.right_ascension,
                                        venus.declination,
                                        expected_ra, expected_dec)
        # العناصر المدارية التقريبية تعطي دقة أفضل من دقيقة قوسية هنا
        self.assertLess(separation, 1.0 / 60.0 * 2.0)
        self.assertAlmostEqual(venus.distance_au, 0.910947, delta=0.0005)

    def test_mars_opposition_2025(self):
        """المريخ في 2025-01-16 قرب التقابل: الاستطالة تقارب 180°."""
        jde = julian_day(2025, 1, 16.0)
        mars = planet_geocentric("المريخ", jde)
        self.assertGreater(mars.elongation, 170.0)
        self.assertLess(mars.distance_au, 0.65)

    def test_magnitudes_reasonable(self):
        jde = julian_day(2026, 8, 9.0)
        jupiter = planet_geocentric("المشتري", jde)
        self.assertTrue(-3.0 > jupiter.magnitude > -3.5
                        or -1.0 > jupiter.magnitude > -3.5)
        venus = planet_geocentric("الزهرة", jde)
        self.assertLess(venus.magnitude, -3.0)


class TestStars(unittest.TestCase):
    def test_catalog_integrity(self):
        self.assertGreater(len(STARS), 50)
        names = [s.name_ar for s in STARS]
        self.assertEqual(len(names), len(set(names)))
        for star in STARS:
            self.assertTrue(0.0 <= star.ra_j2000 < 360.0)
            self.assertTrue(-90.0 <= star.dec_j2000 <= 90.0)

    def test_precession_of_sirius(self):
        """موقع الشعرى اليمانية في 2026 يبعد عن موقع J2000 بنحو 0.36 درجة."""
        sirius = [s for s in STARS if s.name_lat == "Sirius"][0]
        ra, dec = star_apparent(sirius, julian_day(2026, 1, 1.0))
        separation = angular_separation(ra, dec, sirius.ra_j2000,
                                        sirius.dec_j2000)
        self.assertTrue(0.2 < separation < 0.5)

    def test_polaris_near_pole(self):
        polaris = [s for s in STARS if s.name_lat == "Polaris"][0]
        ra, dec = star_apparent(polaris, julian_day(2026, 1, 1.0))
        self.assertGreater(dec, 89.0)


class TestRiseSet(unittest.TestCase):
    def setUp(self):
        self.mecca = [c for c in CITIES if c.name == "مكة المكرمة"][0]

    def test_sun_rise_set_mecca(self):
        """شروق وغروب الشمس في مكة يوم 2026-03-21 (قرب الاعتدال)."""
        jd_midnight = local_midnight_jd(2026, 3, 21, self.mecca)
        events = compute_events(Body(SUN_KEY, SUN_KEY, "sun"), jd_midnight,
                                self.mecca)
        # عند الاعتدال يقارب طول النهار 12 ساعة و7 دقائق
        length = events.set - events.rise
        self.assertAlmostEqual(length, 12.13, delta=0.05)
        # القيم المرجعية محسوبة يدويًا من زاوية نصف القوس ومعادلة الزمن
        self.assertAlmostEqual(events.rise, 6.40, delta=0.03)
        self.assertAlmostEqual(events.set, 18.54, delta=0.03)

    def test_transit_between_rise_and_set(self):
        for city in (CITIES[0], CITIES[7], CITIES[50]):
            jd_midnight = local_midnight_jd(2026, 6, 21, city)
            events = compute_events(Body(SUN_KEY, SUN_KEY, "sun"),
                                    jd_midnight, city)
            if events.rise is not None and events.set is not None:
                self.assertLess(events.rise, events.transit)
                self.assertLess(events.transit, events.set)

    def test_polar_day(self):
        """موقع قطبي في يونيو: الشمس لا تغرب."""
        north = Observer("قطبي", 78.0, 15.0, 1.0)
        jd_midnight = local_midnight_jd(2026, 6, 21, north)
        events = compute_events(Body(SUN_KEY, SUN_KEY, "sun"), jd_midnight,
                                north)
        self.assertTrue(events.always_up)
        self.assertIsNone(events.rise)

    def test_moon_events_exist(self):
        jd_midnight = local_midnight_jd(2026, 8, 9, self.mecca)
        events = compute_events(Body(MOON_KEY, MOON_KEY, "moon"),
                                jd_midnight, self.mecca)
        self.assertTrue(events.rise is not None or events.set is not None)

    def test_twilight_ordering(self):
        jd_midnight = local_midnight_jd(2026, 8, 9, self.mecca)
        events = compute_events(Body(SUN_KEY, SUN_KEY, "sun"), jd_midnight,
                                self.mecca)
        dawn18, dusk18 = twilight_times(jd_midnight, self.mecca, 18.0)
        dawn6, dusk6 = twilight_times(jd_midnight, self.mecca, 6.0)
        self.assertLess(dawn18, dawn6)
        self.assertLess(dawn6, events.rise)
        self.assertLess(events.set, dusk6)
        self.assertLess(dusk6, dusk18)


class TestHijri(unittest.TestCase):
    def test_roundtrip(self):
        for jd in (2451545.0, 2460000.5, 2470000.5):
            year, month, day = jd_to_hijri(jd)
            back = hijri_to_jd(year, month, day)
            self.assertLessEqual(abs(back - jd), 1.0)

    def test_known_epoch(self):
        """1 محرم 1 هـ يوافق تقريبًا 16 يوليو 622 م."""
        year, month, day = jd_to_hijri(julian_day(622, 7, 16.5))
        self.assertEqual((year, month), (1, 1))


class TestReport(unittest.TestCase):
    def test_full_report_runs(self):
        observer = [c for c in CITIES if c.name == "الرياض"][0]
        report = daily_forecast(observer, 2026, 8, 9, include_stars=6)
        self.assertIn("sun", report)
        self.assertIn("moon", report)
        self.assertEqual(len(report["planets"]), 7)
        self.assertTrue(report["highlights"])
        from falak.report import format_full_report
        text = format_full_report(report)
        self.assertIn("الشمس", text)
        self.assertIn("القمر", text)
        self.assertIn("التوقعات", text)

    def test_html_report_runs(self):
        observer = [c for c in CITIES if c.name == "القاهرة"][0]
        report = daily_forecast(observer, 2026, 12, 14, include_stars=5)
        from falak.html_report import build_html
        html = build_html(report)
        self.assertIn("<table>", html)
        self.assertIn("التوأميات", html)  # زخة التوأميات في ذروتها


if __name__ == "__main__":
    unittest.main(verbosity=2)
