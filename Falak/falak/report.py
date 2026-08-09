# -*- coding: utf-8 -*-
"""صياغة التقارير النصية بالعربية."""

from __future__ import division

from .angles import dms, fmt_duration, fmt_time, hms, to_arabic_digits
from .arabic import count_days, count_meteors
from .sky import azimuth_to_arabic
from .timeutil import datetime_from_jd

__all__ = ["format_full_report", "format_positions", "format_moon_section",
           "format_stars_section", "format_forecast_section"]

LINE = "─" * 46


def _t(hours):
    return fmt_time(hours)


def _heading(title):
    return "\n%s\n  %s\n%s" % (LINE, title, LINE)


def _row(label, value):
    return "  %-22s %s" % (label + ":", value)


def format_header(report):
    observer = report["observer"]
    lines = [
        "╔" + "═" * 44 + "╗",
        "   تقرير فلكي يومي — مواقع الأجرام والتوقعات",
        "╚" + "═" * 44 + "╝",
        "",
        _row("الموقع", observer.describe()),
        _row("اليوم", "%s %s" % (report["weekday"], report["gregorian"])),
        _row("التاريخ الهجري", report["hijri"] + "  (حسابي، قد يختلف عن الرؤية)"),
    ]
    return "\n".join(lines)


def format_sun_section(report):
    sun = report["sun"]
    events = sun["events"]
    position = sun["position"]
    lines = [_heading("☀  الشمس")]

    if events.always_up:
        lines.append(_row("الحالة", "الشمس لا تغرب اليوم (نهار قطبي)"))
    elif events.always_down:
        lines.append(_row("الحالة", "الشمس لا تشرق اليوم (ليل قطبي)"))
    else:
        lines.append(_row("الشروق", "%s  (%s، سمت %.1f°)"
                          % (_t(events.rise),
                             azimuth_to_arabic(events.rise_azimuth or 0),
                             events.rise_azimuth or 0)))
        lines.append(_row("الغروب", "%s  (%s، سمت %.1f°)"
                          % (_t(events.set),
                             azimuth_to_arabic(events.set_azimuth or 0),
                             events.set_azimuth or 0)))
    if events.transit is not None:
        lines.append(_row("الزوال (العبور)", "%s  بارتفاع %.2f°"
                          % (_t(events.transit), events.max_altitude)))
    else:
        lines.append(_row("أعلى ارتفاع", "%s  عند %.2f° (تحت الأفق)"
                          % (_t(events.peak_hour), events.max_altitude)))
    if sun["day_length"] is not None:
        lines.append(_row("طول النهار", fmt_duration(sun["day_length"])))

    dawn18, dusk18 = sun["twilight_astronomical"]
    dawn12, dusk12 = sun["twilight_nautical"]
    dawn6, dusk6 = sun["twilight_civil"]
    lines.append(_row("الشفق الفلكي", "فجرًا %s — مساءً %s"
                      % (_t(dawn18), _t(dusk18))))
    lines.append(_row("الشفق البحري", "فجرًا %s — مساءً %s"
                      % (_t(dawn12), _t(dusk12))))
    lines.append(_row("الشفق المدني", "فجرًا %s — مساءً %s"
                      % (_t(dawn6), _t(dusk6))))
    lines.append(_row("المطلع المستقيم", hms(position.right_ascension / 15.0)))
    lines.append(_row("الميل", dms(position.declination)))
    lines.append(_row("البعد عن الأرض", "%.6f و.ف (%.0f ألف كم)"
                      % (position.distance_au,
                         position.distance_au * 149597.8707)))
    lines.append(_row("موقعها في البروج", sun["sign"]))
    return "\n".join(lines)


def format_moon_section(report):
    moon = report["moon"]
    events = moon["events"]
    position = moon["position"]
    phase = moon["phase"]
    mansion_name, mansion_index, mansion_degree = moon["mansion"]

    lines = [_heading("☾  القمر")]
    if events.always_up:
        lines.append(_row("الحالة", "القمر فوق الأفق طوال اليوم"))
    elif events.always_down:
        lines.append(_row("الحالة", "القمر تحت الأفق طوال اليوم"))
    else:
        lines.append(_row("الشروق", "%s  (%s)"
                          % (_t(events.rise),
                             azimuth_to_arabic(events.rise_azimuth or 0))))
        lines.append(_row("الغروب", "%s  (%s)"
                          % (_t(events.set),
                             azimuth_to_arabic(events.set_azimuth or 0))))
    if events.transit is not None:
        lines.append(_row("العبور", "%s بارتفاع %.1f°"
                          % (_t(events.transit), events.max_altitude)))
    else:
        lines.append(_row("أعلى ارتفاع", "%s عند %.1f° (تحت الأفق)"
                          % (_t(events.peak_hour), events.max_altitude)))
    lines.append(_row("الطور", phase["phase_name"]))
    lines.append(_row("نسبة الإضاءة", "%.1f%%" % (phase["illumination"] * 100)))
    lines.append(_row("عمر القمر", "%.1f يوم" % phase["age_days"]))
    lines.append(_row("الاستطالة عن الشمس", "%.1f°" % phase["elongation"]))
    lines.append(_row("البعد عن الأرض", "%.0f كم" % position.distance_km))
    lines.append(_row("القطر الظاهري", "%.1f دقيقة قوسية"
                      % (position.semidiameter * 120.0)))
    lines.append(_row("المطلع المستقيم", hms(position.right_ascension / 15.0)))
    lines.append(_row("الميل", dms(position.declination)))
    lines.append(_row("موقعه في البروج", moon["sign"]))
    lines.append(_row("المنزلة القمرية",
                      "%s (المنزلة %d) عند %.1f° منها"
                      % (mansion_name, mansion_index, mansion_degree)))
    if moon["distance_note"]:
        lines.append(_row("ملاحظة", moon["distance_note"]))

    lines.append("")
    lines.append("  الأطوار القادمة:")
    for jde, name in moon["next_phases"]:
        dt = datetime_from_jd(jde + report["observer"].tz_offset / 24.0)
        lines.append("    • %-14s %04d/%02d/%02d الساعة %02d:%02d"
                     % (name, dt.year, dt.month, dt.day, dt.hour, dt.minute))

    label, details = moon["crescent"]
    lines.append("")
    lines.append(_row("رؤية الهلال", label))
    lines.append("    " + details)
    return "\n".join(lines)


def format_planets_section(report):
    lines = [_heading("🪐  الكواكب")]
    for planet in report["planets"]:
        events = planet["events"]
        position = planet["position"]
        magnitude = ("%.1f" % position.magnitude
                     if position.magnitude is not None else "—")
        lines.append("")
        lines.append("  ● %s" % planet["name"])
        lines.append(_row("    الشروق/الغروب",
                          "%s — %s" % (_t(events.rise), _t(events.set))))
        if events.transit is not None:
            lines.append(_row("    العبور", "%s بارتفاع %.1f°"
                              % (_t(events.transit), events.max_altitude)))
        else:
            lines.append(_row("    أعلى ارتفاع", "%s عند %.1f° (تحت الأفق)"
                              % (_t(events.peak_hour), events.max_altitude)))
        lines.append(_row("    القدر الظاهري", magnitude))
        lines.append(_row("    البعد", "%.4f و.ف" % position.distance_au))
        lines.append(_row("    الاستطالة", "%.1f°" % position.elongation))
        lines.append(_row("    القطر الظاهري", "%.1f″" % position.angular_diameter))
        lines.append(_row("    المطلع/الميل",
                          "%s , %s" % (hms(position.right_ascension / 15.0),
                                       dms(position.declination))))
        lines.append(_row("    البرج", planet["sign"]))
        lines.append(_row("    أفضل وقت للرصد", planet["best_time"]))
        if planet["note"]:
            lines.append("      ↳ " + planet["note"])
    return "\n".join(lines)


def format_stars_section(report, count=12):
    lines = [_heading("✦  ألمع النجوم عند الساعة %s"
                      % _t(report["reference_hour"]))]
    lines.append("  %-24s %6s %8s %10s" % ("النجم", "القدر", "الارتفاع", "الجهة"))
    for item in report["stars"][:count]:
        star = item["star"]
        state = item["state"]
        status = "%.1f°" % state.altitude
        if state.altitude < 0:
            status = "تحت الأفق"
        lines.append("  %-24s %6.2f %8s %10s"
                     % (star.name_ar, star.magnitude, status,
                        azimuth_to_arabic(state.azimuth)
                        if state.altitude > 0 else "—"))
    lines.append("")
    lines.append("  (الأسماء اللاتينية: " +
                 "، ".join(item["star"].name_lat
                           for item in report["stars"][:count]) + ")")
    return "\n".join(lines)


def format_forecast_section(report):
    lines = [_heading("🔭  التوقعات اليومية وظروف الرصد")]

    dark_start, dark_end = report["dark_window"]
    if dark_start is not None and dark_end is not None:
        lines.append(_row("نافذة الليل الفلكي",
                          "من %s إلى %s" % (_t(dark_start), _t(dark_end))))
    else:
        lines.append(_row("نافذة الليل الفلكي", "لا يكتمل الظلام الفلكي اليوم"))

    lines.append("")
    for line in report["highlights"]:
        lines.append("  • " + line)

    if report["conjunctions"]:
        lines.append("")
        lines.append("  الاقترانات القريبة (أقل من 6 درجات):")
        for conjunction in report["conjunctions"]:
            lines.append("    • %s ↔ %s : %.2f°"
                         % (conjunction["first"], conjunction["second"],
                            conjunction["separation"]))

    if report["meteor_showers"]:
        lines.append("")
        lines.append("  زخات الشهب النشطة:")
        for shower in report["meteor_showers"]:
            when = ("الذروة اليوم" if shower["at_peak"]
                    else ("الذروة بعد %s" % count_days(shower["days_to_peak"])
                          if shower["days_to_peak"] > 0
                          else "مضت الذروة منذ %s"
                               % count_days(abs(shower["days_to_peak"]))))
            lines.append("    • %s (%s) — %s — حتى %s في الساعة"
                         % (shower["name"], shower["latin"], when,
                            count_meteors(shower["zhr"])))
    return "\n".join(lines)


def format_footer(report):
    return "\n".join([
        "",
        LINE,
        "  ملاحظات الدقة:",
        "   • مواقع الشمس والقمر بدقة أفضل من دقيقة قوسية.",
        "   • مواقع الكواكب بدقة تتراوح بين ثوانٍ ودقائق قوسية قليلة.",
        "   • الأوقات محسوبة لمركز الجرم مع الانكسار الجوي المعتاد،",
        "     وقد تختلف دقائق بحسب الارتفاع وحالة الجو.",
        "   • التاريخ الهجري حسابي لا يغني عن الرؤية الشرعية.",
        "   • ΔT المستخدم: %.1f ثانية." % report["delta_t"],
        LINE,
    ])


def format_full_report(report, arabic_digits=False, sections=None):
    """التقرير الكامل نصًا. ``sections`` قائمة اختيارية بالأقسام المطلوبة."""
    builders = [
        ("header", format_header),
        ("sun", format_sun_section),
        ("moon", format_moon_section),
        ("planets", format_planets_section),
        ("stars", format_stars_section),
        ("forecast", format_forecast_section),
        ("footer", format_footer),
    ]
    parts = []
    for key, builder in builders:
        if sections is None or key in sections or key in ("header", "footer"):
            parts.append(builder(report))
    text = "\n".join(parts)
    return to_arabic_digits(text) if arabic_digits else text


def format_positions(report):
    """جدول مختصر لمواقع الأجرام الرئيسية."""
    return "\n".join([format_header(report),
                      format_sun_section(report),
                      format_moon_section(report),
                      format_planets_section(report)])
