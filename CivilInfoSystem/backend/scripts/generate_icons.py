"""يولّد أيقونات التطبيق بكل المقاسات التي يحتاجها الأيفون والأندرويد.

التشغيل من مجلد backend:
    python -m scripts.generate_icons

المقاسات مطلوبة لأسباب مختلفة:
  * 180×180  أيقونة الشاشة الرئيسية في الأيفون (apple-touch-icon)
  * 192, 512 الحد الأدنى الذي يشترطه معيار PWA لقبول التثبيت
  * maskable  نسخة بهامش داخلي تسمح لأندرويد بقصّها بأي شكل دون قطع الرمز
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ICONS_DIR = ROOT / "frontend" / "assets" / "icons"

# ألوان هوية النظام
PRIMARY = (13, 90, 84)      # أخضر مزرقّ داكن
ACCENT = (198, 160, 74)     # ذهبي
LIGHT = (245, 247, 246)

SIZES = [72, 96, 128, 144, 152, 180, 192, 256, 384, 512]


def draw_emblem(size: int, *, padding_ratio: float = 0.0) -> Image.Image:
    """يرسم شعار النظام: درع يحمل نجمة وسطور تمثّل السجل.

    padding_ratio يترك هامشاً داخلياً للنسخة القابلة للقصّ (maskable)،
    فلا يُقتطع جزء من الرمز مهما كان شكل القناع الذي يطبّقه النظام.
    """
    image = Image.new("RGBA", (size, size), PRIMARY + (255,))
    draw = ImageDraw.Draw(image)

    pad = size * padding_ratio
    inner = size - 2 * pad

    # الدرع
    shield_w = inner * 0.56
    shield_h = inner * 0.66
    left = pad + (inner - shield_w) / 2
    top = pad + (inner - shield_h) / 2

    draw.rounded_rectangle(
        [left, top, left + shield_w, top + shield_h],
        radius=shield_w * 0.16,
        fill=LIGHT + (255,),
    )

    # سطور السجل
    line_x1 = left + shield_w * 0.20
    line_x2 = left + shield_w * 0.80
    for index in range(3):
        y = top + shield_h * (0.52 + index * 0.13)
        thickness = max(2, int(size * 0.022))
        end_x = line_x2 if index < 2 else line_x1 + (line_x2 - line_x1) * 0.6
        draw.rounded_rectangle(
            [line_x1, y, end_x, y + thickness],
            radius=thickness / 2,
            fill=PRIMARY + (255,),
        )

    # النجمة الذهبية
    cx = left + shield_w / 2
    cy = top + shield_h * 0.32
    r = shield_w * 0.16
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        radius = r if i % 2 == 0 else r * 0.45
        points.append((cx + radius * math.cos(angle), cy - radius * math.sin(angle)))
    draw.polygon(points, fill=ACCENT + (255,))

    return image


def main() -> int:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    for size in SIZES:
        draw_emblem(size).save(ICONS_DIR / f"icon-{size}.png", "PNG", optimize=True)

    # نسخة قابلة للقصّ: الرمز داخل 80% من المساحة
    for size in (192, 512):
        draw_emblem(size, padding_ratio=0.10).save(
            ICONS_DIR / f"maskable-{size}.png", "PNG", optimize=True
        )

    # أيقونة المتصفح
    draw_emblem(32).save(ICONS_DIR / "favicon.png", "PNG", optimize=True)

    count = len(list(ICONS_DIR.glob("*.png")))
    print(f"تم توليد {count} أيقونة في {ICONS_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
