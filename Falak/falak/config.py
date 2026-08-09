# -*- coding: utf-8 -*-
"""حفظ إعدادات المستخدم واسترجاعها (الموقع وتفضيلات العرض)."""

from __future__ import division

import json
import os

from .locations import CITIES, Observer

__all__ = ["load_settings", "save_settings", "settings_path", "DEFAULTS"]

DEFAULTS = {
    "observer": CITIES[2].to_dict(),   # الرياض افتراضيًا
    "arabic_digits": False,
    "star_count": 12,
}


def settings_path():
    """مسار ملف الإعدادات بجوار المشروع، أو في مجلد المستخدم عند التعذر."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(here, "falak_settings.json")
    if os.access(here, os.W_OK):
        return candidate
    return os.path.join(os.path.expanduser("~"), ".falak_settings.json")


def load_settings():
    """قراءة الإعدادات المحفوظة مع القيم الافتراضية عند غيابها."""
    data = dict(DEFAULTS)
    path = settings_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
            if isinstance(stored, dict):
                data.update(stored)
        except (ValueError, OSError):
            pass
    return data


def save_settings(data):
    """كتابة الإعدادات إلى القرص؛ تعيد True عند النجاح."""
    try:
        with open(settings_path(), "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def observer_from_settings(data):
    """بناء كائن الراصد من الإعدادات."""
    return Observer.from_dict(data.get("observer", DEFAULTS["observer"]))
