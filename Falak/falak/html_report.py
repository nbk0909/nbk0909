# -*- coding: utf-8 -*-
"""توليد تقرير HTML عربي (من اليمين إلى اليسار) يصلح للعرض على iPhone.

الصفحة مستقلة تمامًا: لا تحتاج إنترنت ولا ملفات خارجية، وتتكيف مع
الوضعين الفاتح والداكن في نظام iOS.
"""

from __future__ import division

import os

from .angles import dms, fmt_duration, fmt_time, hms
from .arabic import count_days
from .sky import azimuth_to_arabic
from .timeutil import datetime_from_jd

__all__ = ["build_html", "write_html"]

_CSS = """
:root{
  --bg:#f6f7fb; --card:#ffffff; --ink:#12161f; --muted:#5b6478;
  --line:#e3e7f0; --accent:#2f5bd7; --accent-soft:#eaf0ff;
  --warn:#a8620b; --good:#1c7a4a;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0d1017; --card:#151a24; --ink:#e9edf6; --muted:#98a2b8;
    --line:#242b39; --accent:#7aa2ff; --accent-soft:#1b2440;
    --warn:#e0a55a; --good:#5ad39a;
  }
}
*{box-sizing:border-box}
body{
  margin:0; padding:16px 14px 48px;
  background:var(--bg); color:var(--ink);
  font-family:-apple-system,"SF Arabic","Geeza Pro","Segoe UI",
              "Noto Naskh Arabic",Tahoma,sans-serif;
  font-size:17px; line-height:1.7; direction:rtl; text-align:right;
  -webkit-text-size-adjust:100%;
}
h1{font-size:1.45rem; margin:0 0 4px}
h2{font-size:1.1rem; margin:0 0 12px; color:var(--accent)}
.sub{color:var(--muted); font-size:.92rem; margin:0 0 18px}
.card{
  background:var(--card); border:1px solid var(--line); border-radius:16px;
  padding:16px; margin:0 0 14px;
}
.grid{display:grid; grid-template-columns:1fr 1fr; gap:8px 14px}
@media (max-width:430px){.grid{grid-template-columns:1fr}}
.kv{display:flex; justify-content:space-between; gap:10px;
    border-bottom:1px dashed var(--line); padding:5px 0}
.kv:last-child{border-bottom:none}
.kv .k{color:var(--muted); white-space:nowrap}
.kv .v{font-variant-numeric:tabular-nums; text-align:left; direction:ltr;
       unicode-bidi:embed}
.kv .v.rtl{direction:rtl; text-align:right}
table{width:100%; border-collapse:collapse; font-size:.95rem}
th,td{padding:7px 6px; border-bottom:1px solid var(--line); text-align:right}
th{color:var(--muted); font-weight:600; font-size:.85rem}
td.num{font-variant-numeric:tabular-nums; direction:ltr; text-align:left}
.scroll{overflow-x:auto; -webkit-overflow-scrolling:touch}
ul{margin:6px 0 0; padding-inline-start:20px}
li{margin:4px 0}
.badge{display:inline-block; background:var(--accent-soft); color:var(--accent);
       border-radius:999px; padding:2px 10px; font-size:.8rem; margin-inline-start:6px}
.moonbar{height:10px; border-radius:999px; background:var(--line);
         overflow:hidden; margin-top:6px}
.moonbar > i{display:block; height:100%; background:var(--accent)}
.note{color:var(--muted); font-size:.85rem; margin-top:10px}
.good{color:var(--good)} .warn{color:var(--warn)}
footer{color:var(--muted); font-size:.8rem; text-align:center; margin-top:18px}
"""


def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _kv(key, value, rtl=False):
    css = "v rtl" if rtl else "v"
    return ('<div class="kv"><span class="k">%s</span>'
            '<span class="%s">%s</span></div>' % (_esc(key), css, _esc(value)))


def _t(hours):
    return fmt_time(hours)


def build_html(report):
    """بناء صفحة HTML كاملة من قاموس التقرير."""
    observer = report["observer"]
    sun = report["sun"]
    moon = report["moon"]
    phase = moon["phase"]
    sun_events = sun["events"]
    moon_events = moon["events"]

    out = []
    out.append('<meta charset="utf-8">')
    out.append('<meta name="viewport" content="width=device-width,'
               ' initial-scale=1, viewport-fit=cover">')
    out.append('<meta name="color-scheme" content="light dark">')
    out.append('<title>تقرير فلكي — %s</title>' % _esc(observer.name))
    out.append("<style>%s</style>" % _CSS)

    out.append('<h1>التقرير الفلكي اليومي</h1>')
    out.append('<p class="sub">%s &nbsp;·&nbsp; %s %s<br>%s</p>'
               % (_esc(observer.describe()), _esc(report["weekday"]),
                  _esc(report["gregorian"]), _esc(report["hijri"] +
                                                  " (حسابي)")))

    # ---------------- الخلاصة ----------------
    out.append('<div class="card"><h2>خلاصة الليلة</h2><ul>')
    for line in report["highlights"]:
        out.append("<li>%s</li>" % _esc(line))
    out.append("</ul></div>")

    # ---------------- الشمس ----------------
    out.append('<div class="card"><h2>☀ الشمس</h2><div class="grid">')
    if sun_events.always_up:
        out.append(_kv("الحالة", "لا تغرب اليوم", rtl=True))
    elif sun_events.always_down:
        out.append(_kv("الحالة", "لا تشرق اليوم", rtl=True))
    else:
        out.append(_kv("الشروق", _t(sun_events.rise)))
        out.append(_kv("الغروب", _t(sun_events.set)))
    out.append(_kv("الزوال", _t(sun_events.transit)
                   if sun_events.transit is not None
                   else _t(sun_events.peak_hour)))
    out.append(_kv("أقصى ارتفاع", "%.2f°" % sun_events.max_altitude))
    if sun["day_length"] is not None:
        out.append(_kv("طول النهار", fmt_duration(sun["day_length"]), rtl=True))
    out.append(_kv("الشفق الفلكي فجرًا", _t(sun["twilight_astronomical"][0])))
    out.append(_kv("الشفق الفلكي مساءً", _t(sun["twilight_astronomical"][1])))
    out.append(_kv("المطلع المستقيم", hms(sun["position"].right_ascension / 15.0)))
    out.append(_kv("الميل", dms(sun["position"].declination)))
    out.append(_kv("البرج", sun["sign"], rtl=True))
    out.append("</div></div>")

    # ---------------- القمر ----------------
    percent = phase["illumination"] * 100.0
    out.append('<div class="card"><h2>☾ القمر '
               '<span class="badge">%s</span></h2>' % _esc(phase["phase_name"]))
    out.append('<div class="moonbar"><i style="width:%.1f%%"></i></div>'
               % percent)
    out.append('<div class="grid" style="margin-top:10px">')
    out.append(_kv("الإضاءة", "%.1f%%" % percent))
    out.append(_kv("العمر", "%.1f يوم" % phase["age_days"], rtl=True))
    if moon_events.always_up:
        out.append(_kv("الحالة", "فوق الأفق طوال اليوم", rtl=True))
    elif moon_events.always_down:
        out.append(_kv("الحالة", "تحت الأفق طوال اليوم", rtl=True))
    else:
        out.append(_kv("الشروق", _t(moon_events.rise)))
        out.append(_kv("الغروب", _t(moon_events.set)))
    out.append(_kv("العبور", _t(moon_events.transit)
                   if moon_events.transit is not None
                   else _t(moon_events.peak_hour)))
    out.append(_kv("الاستطالة", "%.1f°" % phase["elongation"]))
    out.append(_kv("البعد", "%.0f كم" % moon["position"].distance_km))
    out.append(_kv("القطر الظاهري", "%.1f′" % (moon["position"].semidiameter * 120.0)))
    out.append(_kv("البرج", moon["sign"], rtl=True))
    out.append(_kv("المنزلة القمرية", "%s (%d)" % (moon["mansion"][0],
                                                   moon["mansion"][1]), rtl=True))
    out.append("</div>")

    out.append('<div class="scroll"><table><tr><th>الطور القادم</th>'
               '<th>التاريخ</th><th>الوقت المحلي</th></tr>')
    for jde, name in moon["next_phases"]:
        dt = datetime_from_jd(jde + observer.tz_offset / 24.0)
        out.append("<tr><td>%s</td><td class='num'>%04d/%02d/%02d</td>"
                   "<td class='num'>%02d:%02d</td></tr>"
                   % (_esc(name), dt.year, dt.month, dt.day, dt.hour, dt.minute))
    out.append("</table></div>")

    label, details = moon["crescent"]
    out.append('<p class="note">رؤية الهلال: <b>%s</b> — %s</p>'
               % (_esc(label), _esc(details)))
    if moon["distance_note"]:
        out.append('<p class="note">%s</p>' % _esc(moon["distance_note"]))
    out.append("</div>")

    # ---------------- الكواكب ----------------
    out.append('<div class="card"><h2>🪐 الكواكب</h2><div class="scroll">')
    out.append("<table><tr><th>الكوكب</th><th>الشروق</th><th>العبور</th>"
               "<th>الغروب</th><th>القدر</th><th>الاستطالة</th>"
               "<th>البرج</th><th>أفضل وقت</th></tr>")
    for planet in report["planets"]:
        events = planet["events"]
        position = planet["position"]
        magnitude = ("%.1f" % position.magnitude
                     if position.magnitude is not None else "—")
        out.append("<tr><td>%s</td><td class='num'>%s</td>"
                   "<td class='num'>%s</td><td class='num'>%s</td>"
                   "<td class='num'>%s</td><td class='num'>%.0f°</td>"
                   "<td>%s</td><td>%s</td></tr>"
                   % (_esc(planet["name"]), _t(events.rise), _t(events.transit),
                      _t(events.set), magnitude, position.elongation,
                      _esc(planet["sign"]), _esc(planet["best_time"])))
    out.append("</table></div>")
    notes = [p for p in report["planets"] if p["note"]]
    if notes:
        out.append("<ul>")
        for planet in notes:
            out.append("<li><b>%s</b>: %s</li>"
                       % (_esc(planet["name"]), _esc(planet["note"])))
        out.append("</ul>")
    out.append("</div>")

    # ---------------- النجوم ----------------
    out.append('<div class="card"><h2>✦ ألمع النجوم عند الساعة %s</h2>'
               '<div class="scroll">' % _t(report["reference_hour"]))
    out.append("<table><tr><th>النجم</th><th>Latin</th><th>الكوكبة</th>"
               "<th>القدر</th><th>الارتفاع</th><th>الجهة</th></tr>")
    for item in report["stars"]:
        star = item["star"]
        state = item["state"]
        altitude = ("%.1f°" % state.altitude if state.altitude > 0
                    else "تحت الأفق")
        direction = (azimuth_to_arabic(state.azimuth) if state.altitude > 0
                     else "—")
        out.append("<tr><td>%s</td><td>%s</td><td>%s</td>"
                   "<td class='num'>%.2f</td><td class='num'>%s</td>"
                   "<td>%s</td></tr>"
                   % (_esc(star.name_ar), _esc(star.name_lat),
                      _esc(star.constellation_ar), star.magnitude,
                      altitude, _esc(direction)))
    out.append("</table></div></div>")

    # ---------------- التوقعات ----------------
    out.append('<div class="card"><h2>🔭 التوقعات وظروف الرصد</h2>')
    dark_start, dark_end = report["dark_window"]
    if dark_start is not None and dark_end is not None:
        out.append('<p>نافذة الليل الفلكي: من <b>%s</b> إلى <b>%s</b></p>'
                   % (_t(dark_start), _t(dark_end)))
    else:
        out.append("<p>لا يكتمل الظلام الفلكي في هذا الموقع اليوم.</p>")
    out.append('<p class="note">%s</p>' % _esc(report["moon_interference"]))

    if report["conjunctions"]:
        out.append("<h2 style='margin-top:14px'>الاقترانات القريبة</h2>")
        out.append('<div class="scroll"><table><tr><th>الجرم الأول</th>'
                   "<th>الجرم الثاني</th><th>البُعد الزاوي</th></tr>")
        for conjunction in report["conjunctions"]:
            out.append("<tr><td>%s</td><td>%s</td><td class='num'>%.2f°</td></tr>"
                       % (_esc(conjunction["first"]), _esc(conjunction["second"]),
                          conjunction["separation"]))
        out.append("</table></div>")

    if report["meteor_showers"]:
        out.append("<h2 style='margin-top:14px'>زخات الشهب النشطة</h2>")
        out.append('<div class="scroll"><table><tr><th>الزخة</th>'
                   "<th>الاسم اللاتيني</th><th>الذروة</th>"
                   "<th>المعدل الساعي</th></tr>")
        for shower in report["meteor_showers"]:
            when = ("اليوم" if shower["at_peak"]
                    else ("بعد %s" % count_days(shower["days_to_peak"])
                          if shower["days_to_peak"] > 0
                          else "مضت %s" % count_days(abs(shower["days_to_peak"]))))
            out.append("<tr><td>%s</td><td>%s</td><td>%s</td>"
                       "<td class='num'>%d</td></tr>"
                       % (_esc(shower["name"]), _esc(shower["latin"]),
                          _esc(when), shower["zhr"]))
        out.append("</table></div>")
    out.append("</div>")

    out.append('<footer>حُسب محليًا على الجهاز دون اتصال بالإنترنت · '
               'ΔT = %.1f ث · التاريخ الهجري حسابي لا يغني عن الرؤية'
               '</footer>' % report["delta_t"])
    return "\n".join(out)


def write_html(report, path=None):
    """كتابة التقرير إلى ملف HTML وإرجاع مساره."""
    if path is None:
        path = os.path.join(os.path.expanduser("~"), "تقرير_فلكي.html")
    body = build_html(report)
    # الجزء الأول (الوسوم الوصفية والتنسيق) يوضع في <head> والباقي في <body>
    head_end = body.find("</style>") + len("</style>")
    html = ("<!doctype html>\n<html lang=\"ar\" dir=\"rtl\">\n<head>\n"
            + body[:head_end] + "\n</head>\n<body>\n"
            + body[head_end:] + "\n</body>\n</html>")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(html)
    return path
