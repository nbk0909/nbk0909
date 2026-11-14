"""فحص واجهة PWA في متصفّح حقيقي بمقاس شاشة أيفون.

يشغّل التطبيق فعلياً ويتفاعل معه كما يفعل المستخدم: يسجّل الدخول، ويبحث،
ويفتح شجرة العائلة، ويملأ نموذجاً. الفحوص التي لا يلتقطها اختبار الوحدة
— مساحات اللمس، والاتجاه، والتمرير الأفقي، وأخطاء الطرفية — تُلتقط هنا.

التشغيل (يتطلّب خادمين قيد العمل وقاعدة مُعبّأة بـ scripts.seed):
    # الطرفية 1
    cd backend && uvicorn app.main:app --port 8000
    # الطرفية 2
    cd frontend && python3 -m http.server 8080
    # الطرفية 3
    pip install playwright && playwright install chromium
    python frontend/tests/ui_check.py

المتغيّرات:
    PWA_URL       عنوان الواجهة (الافتراضي http://127.0.0.1:8080/index.html)
    PWA_BROWSER   مسار ملف Chromium التنفيذي إن لم يكن مثبّتاً عبر playwright
    PWA_PASSWORD  كلمة مرور الحسابين التجريبيين (الافتراضي 111)
    PWA_SHOTS     مجلد اللقطات

الفحص لا يغيّر كلمة المرور ولا يكتب بيانات، فيمكن تكراره على القاعدة نفسها.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("PWA_URL", "http://127.0.0.1:8080/index.html")
BROWSER_PATH = os.environ.get("PWA_BROWSER") or None
PASSWORD = os.environ.get("PWA_PASSWORD", "111")
SHOTS = Path(os.environ.get("PWA_SHOTS", "/tmp/pwa-shots"))
SHOTS.mkdir(parents=True, exist_ok=True)

# أبعاد iPhone 14 Pro بالنقاط
IPHONE = {
    "viewport": {"width": 393, "height": 852},
    "device_scale_factor": 3,
    "is_mobile": True,
    "has_touch": True,
    "user_agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "locale": "ar",
}

results: list[tuple[str, bool, str]] = []
console_errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    mark = "✓" if ok else "✗"
    print(f"  {mark} {name}" + (f" — {detail}" if detail else ""), flush=True)


def on_console(message) -> None:
    # استجابات 401 و422 مقصودة في فحوص الرفض، ويسجّلها المتصفح كأخطاء
    # تحميل موارد. ليست أخطاء JavaScript فلا تُحتسب.
    if message.type == "error" and "Failed to load resource" not in message.text:
        console_errors.append(message.text)


def login(page, username: str, password: str) -> None:
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('#login-form button[type="submit"]')


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=BROWSER_PATH)
        context = browser.new_context(**IPHONE)
        page = context.new_page()
        page.on("console", on_console)
        page.on("pageerror", lambda error: console_errors.append(str(error)))

        # ---------------- شاشة الدخول ----------------
        print("\n[1] شاشة الدخول", flush=True)
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_selector("#view-login:not([hidden])", timeout=10000)

        check("الصفحة من اليمين لليسار", page.get_attribute("html", "dir") == "rtl")
        check("لغة الصفحة عربية", page.get_attribute("html", "lang") == "ar")
        check(
            "viewport-fit=cover موجود (احترام نتوء الأيفون)",
            "viewport-fit=cover"
            in (page.get_attribute('meta[name="viewport"]', "content") or ""),
        )
        check(
            "apple-touch-icon معرّف",
            page.locator('link[rel="apple-touch-icon"]').count() == 1,
        )
        page.screenshot(path=str(SHOTS / "01-login.png"))

        button = page.locator('#login-form button[type="submit"]').bounding_box()
        check(f"زر الدخول ≥ 44 نقطة ({button['height']:.0f}px)", button["height"] >= 44)

        # دخول خاطئ
        login(page, "admin", "wrong-password")
        page.wait_for_selector("#login-error:not([hidden])", timeout=8000)
        error_text = page.inner_text("#login-error")
        check(
            "رسالة الخطأ بالعربية",
            "كلمة المرور" in error_text or "المستخدم" in error_text,
            error_text[:60],
        )

        # دخول صحيح
        login(page, "admin", PASSWORD)
        page.wait_for_selector("#app:not([hidden])", timeout=10000)
        page.wait_for_timeout(900)
        check(f"الدخول بكلمة المرور «{PASSWORD}» نجح", True)
        check(
            "لا إلزام بتغيير كلمة المرور عند أول دخول",
            "settings" not in page.url,
            page.url.split("#")[-1],
        )

        # ---------------- الخروج ثم الدخول من جديد ----------------
        print("\n[2] الخروج ثم الدخول ثانيةً", flush=True)
        page.click("#btn-menu")
        page.wait_for_selector("#menu-sheet:not([hidden])", timeout=5000)
        page.click("#btn-logout")
        page.wait_for_selector("#view-login:not([hidden])", timeout=10000)

        # اختبار انحدار: الزر كان يبقى معطّلاً بنص «جارٍ المعالجة…» بعد
        # دخول ناجح، فيتعذّر الدخول ثانيةً إلا بإعادة تحميل الصفحة.
        submit = page.locator('#login-form button[type="submit"]')
        check("زر الدخول مفعَّل بعد الخروج", submit.is_enabled())
        check("نص الزر عاد إلى «دخول»", submit.inner_text().strip() == "دخول")
        check(
            "حقل كلمة المرور أُفرغ بعد الخروج",
            page.input_value('input[name="password"]') == "",
        )

        login(page, "admin", PASSWORD)
        page.wait_for_selector("#app:not([hidden])", timeout=10000)
        check("الدخول الثاني نجح دون إعادة تحميل", True)

        # ---------------- الرئيسية ----------------
        print("\n[3] الشاشة الرئيسية", flush=True)
        page.wait_for_selector("#dash-stats .stat__value", timeout=8000)
        page.wait_for_timeout(1500)
        stats = page.locator("#dash-stats .stat__value").all_inner_texts()
        check(
            "الإحصاءات محمّلة",
            all(s not in ("—", "") for s in stats),
            " | ".join(stats),
        )
        check("شريط التبويب السفلي ظاهر", page.locator(".tabbar").is_visible())
        page.screenshot(path=str(SHOTS / "02-dashboard.png"))

        tab = page.locator('.tabbar__item[data-tab="/"]').bounding_box()
        check(f"عنصر التبويب ≥ 44 نقطة ({tab['height']:.0f}px)", tab["height"] >= 44)

        # ---------------- البحث ----------------
        print("\n[4] البحث العربي", flush=True)
        page.click('.tabbar__item[data-tab="/search"]')
        page.wait_for_selector("#search-q", timeout=8000)

        page.fill("#search-q", "احمد عباس")
        page.wait_for_timeout(1600)
        results_text = page.inner_text("#search-results")
        check(
            "البحث بلا همزة وجد الاسم المكتوب بهمزة",
            "أحمد" in results_text,
            results_text.split("\n")[0][:40],
        )
        page.screenshot(path=str(SHOTS / "03-search.png"))

        page.fill("#search-q", "احمد عباس حسين العبسي")
        page.wait_for_timeout(1800)
        fuzzy_text = page.inner_text("#search-results")
        check("البحث التقريبي وجد الاسم رغم الخطأ الإملائي", "العباسي" in fuzzy_text)
        check("شارة «نتائج تقريبية» ظاهرة", "تقريبية" in fuzzy_text)
        first_line = fuzzy_text.split("\n")[0]
        count = int("".join(ch for ch in first_line if ch.isdigit()) or 0)
        check(
            "النتائج التقريبية محصورة لا السجل كله",
            0 < count < 20,
            f"{count} نتيجة",
        )
        page.screenshot(path=str(SHOTS / "04-search-fuzzy.png"))

        # ---------------- سجل الشخص ----------------
        print("\n[5] سجل الشخص", flush=True)
        page.fill("#search-q", "احمد عباس")
        page.wait_for_timeout(1600)
        page.locator("#search-results .list-item").first.click()
        page.wait_for_selector(".data-list", timeout=8000)
        page.wait_for_timeout(1500)

        detail = page.inner_text("#content")
        check("الاسم الرباعي معروض", "العباسي" in detail)
        check("بيانات الميلاد معروضة", "تاريخ الميلاد" in detail)
        check("زر الرجوع ظهر", page.locator("#btn-back").is_visible())
        page.screenshot(path=str(SHOTS / "05-person.png"), full_page=True)

        consistency = page.inner_text("#consistency")
        check("فحص التماسك عمل", "تعارض" in consistency, consistency.strip()[:50])

        # ---------------- شجرة العائلة ----------------
        print("\n[6] شجرة العائلة", flush=True)
        page.click('a[href*="/tree"]')
        page.wait_for_selector(".tree", timeout=8000)
        page.wait_for_timeout(1000)
        tree_text = page.inner_text(".tree")
        for level_name in ("الوالدان", "الأبناء", "الإخوة"):
            check(f"مستوى «{level_name}» ظاهر", level_name in tree_text)
        page.screenshot(path=str(SHOTS / "06-family-tree.png"), full_page=True)

        # ---------------- القائمة ----------------
        print("\n[7] القائمة والتنقّل", flush=True)
        page.click("#btn-menu")
        page.wait_for_selector("#menu-sheet:not([hidden])", timeout=5000)
        check("القائمة المنسدلة فتحت", page.locator(".sheet__panel").is_visible())
        check("اسم المستخدم معروض", bool(page.inner_text("#menu-name").strip()))
        page.screenshot(path=str(SHOTS / "07-menu.png"))

        page.click('.sheet__link[href="#/births"]')
        page.wait_for_selector(".list-item, .empty", timeout=8000)
        page.wait_for_timeout(800)
        births = page.locator(".list-item").count()
        check("قائمة واقعات الميلاد حمّلت", births > 0, f"{births} سجل")

        # ---------------- نموذج التسجيل ----------------
        print("\n[8] نموذج تسجيل شخص", flush=True)
        page.click('.tabbar__item[data-tab="/person/new"]')
        page.wait_for_selector("#person-form", timeout=8000)
        page.wait_for_timeout(900)
        check("النموذج ظهر", page.locator('input[name="national_id"]').is_visible())
        governorates = page.locator("#gov-select option").count() - 1
        check("قائمة المحافظات محمّلة", governorates > 0, f"{governorates} محافظة")

        # رقم وطني بخانة تدقيق خاطئة — يُرفض ولا يُكتب شيء في القاعدة
        page.fill('input[name="national_id"]', "123456789012")
        page.fill('input[name="first_name"]', "سعد")
        page.fill('input[name="father_name"]', "جاسم")
        page.fill('input[name="grandfather_name"]', "علي")
        page.fill('input[name="family_name"]', "التميمي")
        page.fill('input[name="mother_full_name"]', "نور حسن")
        page.fill('input[name="birth_date"]', "1995-03-20")
        page.select_option('select[name="gender"]', "ذكر")
        page.click('#person-form button[type="submit"]')
        page.wait_for_timeout(1400)
        field_error = page.inner_text('[data-error-for="national_id"]')
        check(
            "خطأ الرقم الوطني ظهر على الحقل نفسه",
            bool(field_error.strip()),
            field_error[:50],
        )
        check(
            "رسالة التحقق عربية خالصة بلا بادئة إنجليزية",
            bool(field_error.strip()) and "Value error" not in field_error,
        )
        page.screenshot(path=str(SHOTS / "08-validation.png"), full_page=True)

        # ---------------- عامل الخدمة والعمل دون اتصال ----------------
        print("\n[9] عامل الخدمة والعمل دون اتصال", flush=True)
        registered = page.evaluate(
            "navigator.serviceWorker.getRegistrations().then(r => r.length > 0)"
        )
        check("عامل الخدمة مسجَّل", registered)

        manifest = context.request.get(BASE.replace("index.html", "manifest.json"))
        check("ملف manifest متاح", manifest.ok)
        if manifest.ok:
            data = manifest.json()
            sizes = {icon["sizes"] for icon in data["icons"]}
            check(
                "أيقونتا 192 و512 موجودتان (شرط تثبيت PWA)",
                "192x192" in sizes and "512x512" in sizes,
            )
            check("اتجاه manifest من اليمين لليسار", data.get("dir") == "rtl")
            check("لغة manifest عربية", data.get("lang") == "ar")

        icon = context.request.get(
            BASE.replace("index.html", "assets/icons/icon-180.png")
        )
        check("أيقونة الأيفون 180×180 متاحة", icon.ok)

        context.set_offline(True)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        shell_alive = page.locator("#app:not([hidden]), #view-login:not([hidden])").count() > 0
        check("التطبيق يُقلع دون اتصال من الذاكرة المؤقتة", shell_alive)
        page.screenshot(path=str(SHOTS / "09-offline.png"))
        context.set_offline(False)

        # ---------------- التمرير الأفقي ----------------
        print("\n[10] فحوص إضافية", flush=True)
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
        )
        check("لا يوجد تمرير أفقي في الصفحة", not overflow)

        # ---------------- الوضع الداكن ----------------
        dark_context = browser.new_context(**IPHONE, color_scheme="dark")
        dark_page = dark_context.new_page()
        dark_page.goto(BASE, wait_until="networkidle")
        dark_page.wait_for_selector("#view-login:not([hidden])", timeout=8000)
        background = dark_page.evaluate(
            "getComputedStyle(document.querySelector('.auth__card')).backgroundColor"
        )
        check("الوضع الداكن يغيّر ألوان الواجهة", background != "rgb(255, 255, 255)", background)
        dark_page.screenshot(path=str(SHOTS / "10-dark.png"))
        dark_context.close()

        # ---------------- شاشة أعرض ----------------
        wide_context = browser.new_context(
            viewport={"width": 1024, "height": 768}, locale="ar"
        )
        wide_page = wide_context.new_page()
        wide_page.goto(BASE, wait_until="networkidle")
        wide_page.wait_for_selector("#view-login:not([hidden])", timeout=8000)
        login(wide_page, "registrar", PASSWORD)
        wide_page.wait_for_selector("#app:not([hidden])", timeout=10000)
        wide_page.wait_for_timeout(1500)
        wide_page.screenshot(path=str(SHOTS / "11-wide.png"))
        check("حساب registrar يدخل بالكلمة نفسها على شاشة عريضة", True)
        wide_context.close()

        check(
            "لا أخطاء JavaScript في الطرفية",
            not console_errors,
            "; ".join(console_errors[:2])[:120],
        )

        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"النتيجة: {passed}/{total} فحصاً ناجحاً")
    failed = [(name, detail) for name, ok, detail in results if not ok]
    if failed:
        print("\nالفحوص الفاشلة:")
        for name, detail in failed:
            print(f"  ✗ {name} — {detail}")
    print(f"اللقطات في: {SHOTS}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
