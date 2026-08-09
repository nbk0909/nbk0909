# -*- coding: utf-8 -*-
"""التوقعات اليومية: أحداث السماء وظروف الرصد والاقترانات.

«التوقعات» هنا تنبؤات فلكية محسوبة: مواعيد الشروق والغروب، ونوافذ
الرصد المظلمة، ورؤية الكواكب، والاقترانات القريبة، وزخات الشهب النشطة.
"""

from __future__ import division

from .arabic import agree, count_days, count_meteors
from .coords import angular_separation
from .hijri import crescent_visibility, format_hijri
from .moon import (lunar_mansion, moon_libration_note, moon_phase_info,
                   upcoming_phases)
from .planets import PLANET_ORDER, planet_geocentric
from .sky import (MOON_KEY, SUN_KEY, Body, body_state, compute_events,
                  local_midnight_jd, star_body, twilight_times)
from .stars import brightest, star_apparent
from .sun import sun_apparent
from .timeutil import (day_of_week_ar, delta_t_seconds, format_gregorian_ar,
                       jde_from_jd)
from .zodiac import format_sign_position

__all__ = ["daily_forecast", "METEOR_SHOWERS"]


# (الاسم العربي، الاسم اللاتيني، بداية النشاط، الذروة، النهاية،
#  المعدل الساعي الأقصى، (مطلع المشع بالساعات، ميله))
METEOR_SHOWERS = [
    ("الرُّباعيات", "Quadrantids", (12, 28), (1, 3), (1, 12), 110, (15.33, 49)),
    ("القِيثاريات", "Lyrids", (4, 16), (4, 22), (4, 25), 18, (18.07, 34)),
    ("الدَّلويات إيتا", "Eta Aquariids", (4, 19), (5, 6), (5, 28), 50, (22.53, -1)),
    ("الدَّلويات دلتا", "Delta Aquariids", (7, 12), (7, 30), (8, 23), 25, (22.67, -16)),
    ("البَرشاويات", "Perseids", (7, 17), (8, 12), (8, 24), 100, (3.22, 58)),
    ("التِّنِّينيات", "Draconids", (10, 6), (10, 8), (10, 10), 10, (17.47, 54)),
    ("الجَبّاريات", "Orionids", (10, 2), (10, 21), (11, 7), 20, (6.35, 16)),
    ("الثَّوريات الجنوبية", "S. Taurids", (9, 10), (11, 5), (11, 20), 5, (3.73, 14)),
    ("الثَّوريات الشمالية", "N. Taurids", (10, 20), (11, 12), (12, 10), 5, (3.87, 22)),
    ("الأسَديات", "Leonids", (11, 6), (11, 17), (11, 30), 15, (10.28, 21)),
    ("التوأميات", "Geminids", (12, 4), (12, 14), (12, 17), 150, (7.47, 32)),
    ("الدُّبِّيات", "Ursids", (12, 17), (12, 22), (12, 26), 10, (14.47, 76)),
]


def _in_range(month, day, start, end):
    """هل التاريخ (شهر/يوم) واقع ضمن مدى قد يعبر رأس السنة؟"""
    value = month * 100 + day
    lo = start[0] * 100 + start[1]
    hi = end[0] * 100 + end[1]
    if lo <= hi:
        return lo <= value <= hi
    return value >= lo or value <= hi


def active_meteor_showers(month, day):
    """زخات الشهب النشطة في تاريخ معطى، مرتبة بحسب القرب من الذروة."""
    result = []
    for name, latin, start, peak, end, zhr, radiant in METEOR_SHOWERS:
        if _in_range(month, day, start, end):
            days_to_peak = (peak[0] - month) * 30 + (peak[1] - day)
            result.append({
                "name": name, "latin": latin, "zhr": zhr,
                "peak": peak, "radiant": radiant,
                "days_to_peak": days_to_peak,
                "at_peak": abs(days_to_peak) <= 1,
            })
    result.sort(key=lambda item: abs(item["days_to_peak"]))
    return result


def _window_max_altitude(body, jd_midnight, observer, start_hour, end_hour,
                         step_hours=0.25):
    """أقصى ارتفاع يبلغه جرم خلال نافذة زمنية محلية، أو None إن لم يظهر."""
    if start_hour is None or end_hour is None or end_hour <= start_hour:
        return None, None
    best_altitude = None
    best_hour = None
    hour = start_hour
    while hour <= end_hour + 1e-9:
        state = body_state(body, jd_midnight + hour / 24.0, observer)
        if best_altitude is None or state.altitude > best_altitude:
            best_altitude = state.altitude
            best_hour = hour
        hour += step_hours
    return best_altitude, best_hour


def _observing_windows(sun_events):
    """نافذتا الرصد المسائية والصباحية بالساعات المحلية.

    تبدأ النافذة المسائية بعد الغروب بنصف ساعة (بداية ظهور الكواكب)
    وتمتد خمس ساعات، والصباحية تنتهي قبل الشروق بنصف ساعة.
    """
    evening = morning = (None, None)
    if sun_events.set is not None:
        evening = (sun_events.set + 0.5, sun_events.set + 5.5)
    if sun_events.rise is not None:
        morning = (sun_events.rise - 5.5, sun_events.rise - 0.5)
    return evening, morning


def _visibility_label(altitude, name=""):
    """وصف حالة الرؤية موافقًا لجنس اسم الجرم."""
    if altitude is None or altitude < 5:
        return agree(name, "غير مرئي", "غير مرئية")
    if altitude >= 30:
        return agree(name, "مرتفع وواضح", "مرتفعة وواضحة")
    if altitude >= 15:
        return agree(name, "مرئي بوضوح", "مرئية بوضوح")
    return agree(name, "منخفض قرب الأفق", "منخفضة قرب الأفق")


def _planet_note(name, position):
    """ملاحظة عن ظروف الكوكب: التقابل أو الاستطالة القصوى أو الاقتران."""
    elongation = position.elongation
    if name in ("عطارد", "الزهرة"):
        limit = 27.0 if name == "عطارد" else 46.0
        if elongation > limit * 0.92:
            return agree(name,
                         "قرب استطالته القصوى — أفضل فترة لرصده",
                         "قرب استطالتها القصوى — أفضل فترة لرصدها")
        if elongation < 10.0:
            return agree(name,
                         "قريب جدًا من الشمس — يتعذر رصده",
                         "قريبة جدًا من الشمس — يتعذر رصدها")
        return ""
    if elongation > 160.0:
        return agree(name,
                     "قرب التقابل — يُرى طوال الليل وهو في أفضل حالاته",
                     "قرب التقابل — تُرى طوال الليل وهي في أفضل حالاتها")
    if elongation < 15.0:
        return agree(name, "قريب من الشمس — يصعب رصده",
                     "قريبة من الشمس — يصعب رصدها")
    return ""


def daily_forecast(observer, year, month, day, include_stars=12):
    """التقرير الفلكي الكامل ليوم محلي واحد.

    يعيد قاموسًا منظمًا يمكن عرضه نصًا أو تحويله إلى صفحة HTML.
    """
    jd_midnight = local_midnight_jd(year, month, day, observer)
    jd_noon = jd_midnight + 0.5
    jde_noon = jde_from_jd(jd_noon)

    report = {
        "observer": observer,
        "date": (year, month, day),
        "weekday": day_of_week_ar(jd_midnight + 0.5),
        "gregorian": format_gregorian_ar(year, month, day),
        "hijri": format_hijri(jd_noon),
        "jd_midnight": jd_midnight,
        "jd_noon": jd_noon,
        "delta_t": delta_t_seconds(jd_noon),
    }

    # ------------------------------------------------------------------
    # الشمس
    # ------------------------------------------------------------------
    sun_body = Body(SUN_KEY, SUN_KEY, "sun")
    sun_events = compute_events(sun_body, jd_midnight, observer)
    sun_pos = sun_apparent(jde_noon)

    civil = twilight_times(jd_midnight, observer, 6.0)
    nautical = twilight_times(jd_midnight, observer, 12.0)
    astronomical = twilight_times(jd_midnight, observer, 18.0)

    day_length = None
    if sun_events.rise is not None and sun_events.set is not None:
        day_length = sun_events.set - sun_events.rise

    report["sun"] = {
        "events": sun_events,
        "position": sun_pos,
        "sign": format_sign_position(sun_pos.longitude),
        "day_length": day_length,
        "twilight_civil": civil,
        "twilight_nautical": nautical,
        "twilight_astronomical": astronomical,
    }

    # ------------------------------------------------------------------
    # القمر
    # ------------------------------------------------------------------
    moon_body = Body(MOON_KEY, MOON_KEY, "moon")
    moon_events = compute_events(moon_body, jd_midnight, observer)
    phase = moon_phase_info(jde_noon)
    moon_pos = phase["moon"]
    mansion_name, mansion_index, mansion_degree = lunar_mansion(
        moon_pos.longitude, jde_noon)

    crescent = crescent_visibility(moon_events.set, sun_events.set,
                                   phase["illumination"], phase["age_days"],
                                   phase["elongation"])

    report["moon"] = {
        "events": moon_events,
        "position": moon_pos,
        "phase": phase,
        "sign": format_sign_position(moon_pos.longitude),
        "mansion": (mansion_name, mansion_index, mansion_degree),
        "distance_note": moon_libration_note(moon_pos),
        "next_phases": upcoming_phases(jde_noon),
        "crescent": crescent,
    }

    # ------------------------------------------------------------------
    # الكواكب
    # ------------------------------------------------------------------
    evening_window, morning_window = _observing_windows(sun_events)

    planets = []
    for name in PLANET_ORDER:
        body = Body(name, name, "planet")
        events = compute_events(body, jd_midnight, observer)
        position = planet_geocentric(name, jde_noon)

        evening_alt, evening_at = _window_max_altitude(
            body, jd_midnight, observer, evening_window[0], evening_window[1])
        morning_alt, morning_at = _window_max_altitude(
            body, jd_midnight, observer, morning_window[0], morning_window[1])

        visible_evening = evening_alt is not None and evening_alt >= 5.0
        visible_morning = morning_alt is not None and morning_alt >= 5.0
        if visible_evening and visible_morning:
            best = "المساء والفجر"
        elif visible_evening:
            best = "المساء"
        elif visible_morning:
            best = "الفجر"
        else:
            best = "غير مرئي"

        altitudes = [a for a in (evening_alt, morning_alt) if a is not None]
        planets.append({
            "name": name,
            "events": events,
            "position": position,
            "sign": format_sign_position(position.ecliptic_longitude),
            "evening_altitude": evening_alt,
            "evening_hour": evening_at,
            "morning_altitude": morning_alt,
            "morning_hour": morning_at,
            "best_time": best,
            "visibility": _visibility_label(max(altitudes) if altitudes
                                            else None, name),
            "note": _planet_note(name, position),
        })
    report["planets"] = planets

    # ------------------------------------------------------------------
    # النجوم اللامعة
    # ------------------------------------------------------------------
    if astronomical[1] is not None:
        reference_hour = astronomical[1] + 0.5
    elif sun_events.set is not None:
        reference_hour = sun_events.set + 1.5
    else:
        reference_hour = 21.0
    reference_jd = jd_midnight + reference_hour / 24.0

    stars = []
    for star in brightest(include_stars):
        body = star_body(star)
        state = body_state(body, reference_jd, observer)
        events = compute_events(body, jd_midnight, observer)
        stars.append({
            "star": star,
            "state": state,
            "events": events,
        })
    stars.sort(key=lambda item: -item["state"].altitude)
    report["stars"] = stars
    report["reference_hour"] = reference_hour

    # ------------------------------------------------------------------
    # نافذة الرصد المظلمة
    # ------------------------------------------------------------------
    dark_start = astronomical[1]
    dark_end = astronomical[0]
    report["dark_window"] = (dark_start, dark_end)
    report["moon_interference"] = _moon_interference(
        moon_events, dark_start, dark_end, phase["illumination"])

    # ------------------------------------------------------------------
    # الاقترانات
    # ------------------------------------------------------------------
    report["conjunctions"] = _conjunctions(observer, reference_jd)

    # ------------------------------------------------------------------
    # زخات الشهب
    # ------------------------------------------------------------------
    report["meteor_showers"] = active_meteor_showers(month, day)

    # ------------------------------------------------------------------
    # الخلاصة والنصائح
    # ------------------------------------------------------------------
    report["highlights"] = _highlights(report)
    return report


def _moon_interference(moon_events, dark_start, dark_end, illumination):
    """تقدير أثر ضوء القمر على الرصد خلال الليل."""
    if dark_start is None or dark_end is None:
        return "لا يوجد ليل فلكي كامل في هذا الموقع اليوم."

    if illumination < 0.15:
        return "ضوء القمر ضعيف جدًا — الليلة ممتازة لرصد الأجرام الخافتة."

    percent = int(round(illumination * 100))
    if moon_events.always_down:
        return "القمر تحت الأفق طوال الليل — سماء مظلمة رغم إضاءته %d%%." % percent
    if moon_events.always_up:
        return "القمر فوق الأفق طوال الليل بإضاءة %d%% — يصعب رصد الأجرام الخافتة." % percent

    parts = []
    if moon_events.set is not None:
        parts.append("يغرب القمر الساعة %02d:%02d فتصفو السماء بعدها"
                     % (int(moon_events.set) % 24,
                        int(round((moon_events.set % 1) * 60)) % 60))
    if moon_events.rise is not None:
        parts.append("ويشرق الساعة %02d:%02d"
                     % (int(moon_events.rise) % 24,
                        int(round((moon_events.rise % 1) * 60)) % 60))
    prefix = "إضاءة القمر %d%%" % percent
    return prefix + ("، " + "، ".join(parts) if parts else "") + "."


def _conjunctions(observer, jd, limit_degrees=6.0):
    """رصد الاقترانات القريبة بين القمر والكواكب والنجوم اللامعة."""
    jde = jde_from_jd(jd)

    entries = []
    moon = Body(MOON_KEY, MOON_KEY, "moon")
    state = body_state(moon, jd, observer)
    entries.append(("القمر", state.right_ascension, state.declination))

    for name in PLANET_ORDER:
        position = planet_geocentric(name, jde)
        entries.append((name, position.right_ascension, position.declination))

    for star in brightest(20):
        if abs(star.dec_j2000) > 60:
            continue
        ra, dec = star_apparent(star, jde)
        entries.append((star.name_ar, ra, dec))

    results = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            name1, ra1, dec1 = entries[i]
            name2, ra2, dec2 = entries[j]
            separation = angular_separation(ra1, dec1, ra2, dec2)
            if separation <= limit_degrees:
                results.append({
                    "first": name1, "second": name2,
                    "separation": separation,
                })
    results.sort(key=lambda item: item["separation"])
    return results


def _highlights(report):
    """أبرز ما في سماء الليلة، في جمل قصيرة."""
    lines = []
    phase = report["moon"]["phase"]
    lines.append("القمر في طور %s بإضاءة %d%%."
                 % (phase["phase_name"], int(round(phase["illumination"] * 100))))

    visible = [p for p in report["planets"] if p["best_time"] != "غير مرئي"]
    if visible:
        names = "، ".join(
            "%s في %s (%s، أقصى ارتفاع %.0f°)"
            % (p["name"], p["best_time"], p["visibility"],
               max(a for a in (p["evening_altitude"], p["morning_altitude"])
                   if a is not None))
            for p in visible)
        lines.append("الكواكب المرئية اليوم: " + names + ".")
    else:
        lines.append("لا توجد كواكب في وضع رصد جيد اليوم.")

    for planet in report["planets"]:
        if planet["note"]:
            lines.append("%s: %s." % (planet["name"], planet["note"]))

    for conjunction in report["conjunctions"][:3]:
        lines.append("اقتران: %s و%s على بُعد %.1f° من بعضهما."
                     % (conjunction["first"], conjunction["second"],
                        conjunction["separation"]))

    for shower in report["meteor_showers"]:
        if shower["at_peak"]:
            lines.append("زخة %s في ذروتها الليلة بمعدل يصل إلى %s في الساعة."
                         % (shower["name"], count_meteors(shower["zhr"])))
        elif shower["days_to_peak"] > 0:
            lines.append("زخة %s نشطة، وذروتها بعد %s."
                         % (shower["name"],
                            count_days(shower["days_to_peak"])))

    lines.append(report["moon_interference"])
    return lines
