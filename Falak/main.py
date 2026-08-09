#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فَلَك — برنامج فلكي عربي يعمل على iPhone وعلى الحاسوب.

التشغيل التفاعلي:      python3 main.py
التشغيل المباشر:       python3 main.py --html --city جدة
                       python3 main.py --date 2026-12-14 --city القاهرة

لا يحتاج البرنامج إلى أي مكتبة خارجية ولا إلى اتصال بالإنترنت.
"""

from __future__ import division, print_function

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from falak import __version__
from falak.angles import dms, hms, to_arabic_digits
from falak.config import (load_settings, observer_from_settings,
                          save_settings, settings_path)
from falak.events import daily_forecast
from falak.html_report import write_html
from falak.locations import CITIES, Observer, find_city
from falak.moon import moon_phase_info
from falak.planets import PLANET_ORDER
from falak.report import (format_full_report, format_forecast_section,
                          format_header, format_moon_section,
                          format_planets_section, format_stars_section,
                          format_sun_section)
from falak.sky import (MOON_KEY, SUN_KEY, Body, azimuth_to_arabic, body_state,
                       star_body)
from falak.stars import brightest, find_stars
from falak.timeutil import jd_from_datetime


# ---------------------------------------------------------------------------
# أدوات العرض
# ---------------------------------------------------------------------------

def emit(text, arabic_digits=False):
    """طباعة نص مع خيار تحويل الأرقام إلى عربية-هندية."""
    print(to_arabic_digits(text) if arabic_digits else text)


def ask(prompt, default=""):
    try:
        value = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return value.strip() or default


def current_jd():
    """اليوم اليولياني للحظة الحالية بالتوقيت العالمي."""
    return jd_from_datetime(datetime.datetime.utcnow())


def today_local(observer):
    """تاريخ اليوم في التوقيت المحلي للراصد."""
    now = datetime.datetime.utcnow() + datetime.timedelta(
        hours=observer.tz_offset)
    return now.year, now.month, now.day


# ---------------------------------------------------------------------------
# الشاشات
# ---------------------------------------------------------------------------

def screen_now(observer, arabic_digits=False, star_count=10):
    """مواقع الأجرام في اللحظة الحالية."""
    jd = current_jd()
    local = datetime.datetime.utcnow() + datetime.timedelta(
        hours=observer.tz_offset)

    lines = []
    lines.append("─" * 46)
    lines.append("  السماء الآن — %s" % observer.name)
    lines.append("  الوقت المحلي: %s" % local.strftime("%Y/%m/%d %H:%M:%S"))
    lines.append("─" * 46)
    lines.append("  %-22s %9s %8s %10s" % ("الجرم", "الارتفاع", "السمت", "الجهة"))

    bodies = [Body(SUN_KEY, SUN_KEY, "sun"), Body(MOON_KEY, MOON_KEY, "moon")]
    bodies += [Body(name, name, "planet") for name in PLANET_ORDER]
    for star in brightest(star_count):
        bodies.append(star_body(star))

    for body in bodies:
        state = body_state(body, jd, observer)
        if state.altitude_apparent > 0:
            status = "%8.2f°" % state.altitude
            direction = azimuth_to_arabic(state.azimuth)
        else:
            status = "%8.2f°" % state.altitude
            direction = "تحت الأفق"
        lines.append("  %-22s %9s %7.1f° %10s"
                     % (body.name, status, state.azimuth, direction))

    phase = moon_phase_info(jd)
    lines.append("─" * 46)
    lines.append("  القمر: %s — إضاءة %.1f%% — عمر %.1f يوم"
                 % (phase["phase_name"], phase["illumination"] * 100,
                    phase["age_days"]))
    lines.append("─" * 46)
    emit("\n".join(lines), arabic_digits)


def screen_stars(observer, arabic_digits=False):
    """قائمة النجوم أو البحث فيها."""
    query = ask("  ابحث عن نجم (اتركه فارغًا لعرض الألمع): ")
    stars = find_stars(query) if query else brightest(20)
    if not stars:
        emit("  لم يُعثر على نجم بهذا الاسم.", arabic_digits)
        return

    jd = current_jd()
    lines = ["─" * 60,
             "  %-24s %-14s %6s %9s %9s"
             % ("النجم", "اللاتيني", "القدر", "الارتفاع", "الجهة"),
             "─" * 60]
    for star in stars:
        state = body_state(star_body(star), jd, observer)
        altitude = ("%8.2f°" % state.altitude)
        direction = (azimuth_to_arabic(state.azimuth)
                     if state.altitude > 0 else "تحت الأفق")
        lines.append("  %-24s %-14s %6.2f %9s %9s"
                     % (star.name_ar, star.name_lat, star.magnitude,
                        altitude, direction))
        lines.append("      %s — %s — مطلع %s، ميل %s"
                     % (star.bayer, star.constellation_ar,
                        hms(state.right_ascension / 15.0),
                        dms(state.declination)))
    lines.append("─" * 60)
    emit("\n".join(lines), arabic_digits)


def screen_change_location(settings):
    """تغيير موقع الراصد: من قائمة المدن أو بإدخال الإحداثيات."""
    print("\n  المدن المتوفرة:")
    for index, city in enumerate(CITIES, 1):
        print("   %3d) %-18s %s" % (index, city.name, city.country), end="")
        if index % 2 == 0:
            print()
    print("\n")
    choice = ask("  اكتب رقم المدينة أو اسمها، أو 'يدوي' لإدخال الإحداثيات: ")
    if not choice:
        return settings

    if choice in ("يدوي", "manual", "م"):
        name = ask("  اسم الموقع: ", "موقع مخصص")
        try:
            latitude = float(ask("  خط العرض (شمالًا موجب): ", "0"))
            longitude = float(ask("  خط الطول (شرقًا موجب): ", "0"))
            tz = float(ask("  فرق التوقيت عن غرينتش بالساعات: ", "0"))
            elevation = float(ask("  الارتفاع بالأمتار: ", "0"))
        except ValueError:
            print("  قيمة غير صالحة، أُلغي التغيير.")
            return settings
        observer = Observer(name, latitude, longitude, tz, elevation, "")
    else:
        observer = None
        if choice.isdigit() and 1 <= int(choice) <= len(CITIES):
            observer = CITIES[int(choice) - 1]
        else:
            matches = find_city(choice)
            if not matches:
                print("  لم يُعثر على المدينة.")
                return settings
            observer = matches[0]

    settings["observer"] = observer.to_dict()
    if save_settings(settings):
        print("  ✓ حُفظ الموقع: %s" % observer.describe())
    else:
        print("  تعذّر حفظ الإعدادات، لكن الموقع سيُستعمل في هذه الجلسة.")
    return settings


def screen_settings(settings):
    """تبديل تفضيلات العرض."""
    print("\n  الإعدادات الحالية:")
    print("   • الأرقام العربية-الهندية: %s"
          % ("نعم" if settings.get("arabic_digits") else "لا"))
    print("   • عدد النجوم في التقرير: %d" % settings.get("star_count", 12))
    print("   • ملف الإعدادات: %s" % settings_path())
    choice = ask("\n  (1) تبديل شكل الأرقام  (2) تغيير عدد النجوم  (Enter للرجوع): ")
    if choice == "1":
        settings["arabic_digits"] = not settings.get("arabic_digits", False)
    elif choice == "2":
        try:
            settings["star_count"] = max(3, min(40, int(ask("  العدد: ", "12"))))
        except ValueError:
            print("  قيمة غير صالحة.")
    save_settings(settings)
    return settings


def ask_date(observer):
    """طلب تاريخ من المستخدم، والافتراضي تاريخ اليوم المحلي."""
    year, month, day = today_local(observer)
    text = ask("  التاريخ (YYYY-MM-DD) أو Enter لليوم: ")
    if not text:
        return year, month, day
    for separator in ("-", "/", " "):
        if separator in text:
            parts = text.split(separator)
            break
    else:
        parts = [text]
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except (ValueError, IndexError):
        print("  صيغة التاريخ غير مفهومة، سيُستعمل تاريخ اليوم.")
        return year, month, day


def open_in_browser(path):
    """محاولة فتح ملف HTML في متصفح الجهاز."""
    try:
        import webbrowser
        webbrowser.open("file://" + path)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# القائمة الرئيسية
# ---------------------------------------------------------------------------

MENU = """
╔══════════════════════════════════════════════╗
║        فَلَك — الحاسبة الفلكية العربية        ║
╚══════════════════════════════════════════════╝
  الموقع الحالي: %s

   1) التقرير الفلكي الكامل لليوم
   2) السماء الآن (مواقع لحظية)
   3) الشمس
   4) القمر والمنازل القمرية
   5) الكواكب
   6) النجوم اللامعة
   7) التوقعات اليومية وظروف الرصد
   8) تقرير HTML للعرض على الجهاز
   9) تغيير الموقع
  10) الإعدادات
   0) خروج
"""


def interactive():
    settings = load_settings()
    observer = observer_from_settings(settings)

    while True:
        digits = settings.get("arabic_digits", False)
        observer = observer_from_settings(settings)
        print(MENU % observer.describe())
        choice = ask("  اختيارك: ")

        if choice in ("0", "خروج", "q", "خ"):
            print("  إلى اللقاء 🌙")
            return 0

        if choice == "2":
            screen_now(observer, digits, settings.get("star_count", 10))
            continue
        if choice == "6":
            screen_stars(observer, digits)
            continue
        if choice == "9":
            settings = screen_change_location(settings)
            continue
        if choice == "10":
            settings = screen_settings(settings)
            continue

        if choice not in ("1", "3", "4", "5", "7", "8"):
            print("  اختيار غير معروف.")
            continue

        year, month, day = ask_date(observer)
        print("  … جارٍ الحساب")
        report = daily_forecast(observer, year, month, day,
                                settings.get("star_count", 12))

        if choice == "1":
            emit(format_full_report(report, digits), False)
        elif choice == "3":
            emit(format_header(report) + "\n" + format_sun_section(report), digits)
        elif choice == "4":
            emit(format_header(report) + "\n" + format_moon_section(report), digits)
        elif choice == "5":
            emit(format_header(report) + "\n" + format_planets_section(report), digits)
        elif choice == "7":
            emit(format_header(report) + "\n" + format_forecast_section(report), digits)
        elif choice == "8":
            path = write_html(report)
            print("  ✓ حُفظ التقرير في: %s" % path)
            if open_in_browser(path):
                print("  ✓ فُتح التقرير في المتصفح.")
            else:
                print("  افتح الملف يدويًا من تطبيق الملفات لعرضه.")


# ---------------------------------------------------------------------------
# سطر الأوامر
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description="فَلَك — حاسبة فلكية عربية (مواقع الكواكب والنجوم والقمر)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--city", help="اسم مدينة من القائمة المدمجة")
    parser.add_argument("--lat", type=float, help="خط العرض (شمالًا موجب)")
    parser.add_argument("--lon", type=float, help="خط الطول (شرقًا موجب)")
    parser.add_argument("--tz", type=float, help="فرق التوقيت بالساعات")
    parser.add_argument("--elev", type=float, default=0.0,
                        help="الارتفاع عن سطح البحر بالأمتار")
    parser.add_argument("--date", help="التاريخ بصيغة YYYY-MM-DD")
    parser.add_argument("--html", action="store_true",
                        help="توليد تقرير HTML بدل النص")
    parser.add_argument("--out", help="مسار ملف HTML الناتج")
    parser.add_argument("--now", action="store_true",
                        help="عرض مواقع الأجرام في اللحظة الحالية")
    parser.add_argument("--section", choices=["sun", "moon", "planets",
                                              "stars", "forecast"],
                        help="عرض قسم واحد فقط من التقرير")
    parser.add_argument("--arabic-digits", action="store_true",
                        help="استخدام الأرقام العربية-الهندية")
    parser.add_argument("--stars", type=int, default=12,
                        help="عدد النجوم المعروضة")
    parser.add_argument("--version", action="version",
                        version="فَلَك %s" % __version__)
    return parser


def resolve_observer(args, settings):
    if args.lat is not None and args.lon is not None:
        return Observer("موقع مخصص", args.lat, args.lon,
                        args.tz if args.tz is not None else 0.0,
                        args.elev, "")
    if args.city:
        matches = find_city(args.city)
        if not matches:
            print("لم يُعثر على المدينة: %s" % args.city, file=sys.stderr)
            sys.exit(2)
        return matches[0]
    return observer_from_settings(settings)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return interactive()

    args = build_parser().parse_args(argv)
    settings = load_settings()
    observer = resolve_observer(args, settings)
    digits = args.arabic_digits or settings.get("arabic_digits", False)

    if args.now:
        screen_now(observer, digits, args.stars)
        return 0

    if args.date:
        try:
            parts = args.date.replace("/", "-").split("-")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        except (ValueError, IndexError):
            print("صيغة التاريخ غير صحيحة، استخدم YYYY-MM-DD", file=sys.stderr)
            return 2
    else:
        year, month, day = today_local(observer)

    report = daily_forecast(observer, year, month, day, args.stars)

    if args.html:
        path = write_html(report, args.out)
        print("حُفظ التقرير في: %s" % path)
        open_in_browser(path)
        return 0

    if args.section:
        builders = {
            "sun": format_sun_section, "moon": format_moon_section,
            "planets": format_planets_section, "stars": format_stars_section,
            "forecast": format_forecast_section,
        }
        emit(format_header(report) + "\n" + builders[args.section](report),
             digits)
        return 0

    emit(format_full_report(report, digits), False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
