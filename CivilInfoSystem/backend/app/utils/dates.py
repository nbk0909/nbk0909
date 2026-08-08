"""أدوات التعامل مع التواريخ والأوقات.

المشكلة التي تحلّها ensure_utc
------------------------------
PostgreSQL يحفظ المنطقة الزمنية مع العمود TIMESTAMPTZ ويعيدها، أمّا SQLite
فلا يملك نوعاً زمنياً أصلاً ويخزّن النص كما هو، فيعود التاريخ بلا منطقة
زمنية (naive). مقارنة تاريخ بلا منطقة بآخر يحملها ترفع TypeError في بايثون،
فتنهار المقارنة في بيئة التطوير بينما تعمل في الإنتاج — وهو أسوأ أنواع
الأعطال لأنه لا يظهر حيث يُختبر الكود.

القاعدة المتّبعة: كل ما يُقرأ من قاعدة البيانات يمرّ على ensure_utc قبل
أي مقارنة زمنية.
"""

from __future__ import annotations

from datetime import date, datetime, timezone


def utcnow() -> datetime:
    """الوقت الحالي بتوقيت UTC مع منطقة زمنية صريحة."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime | None) -> datetime | None:
    """يضمن أن التاريخ يحمل منطقة زمنية UTC.

    التواريخ بلا منطقة زمنية تُفترض UTC — وهو الصحيح هنا لأن كل ما يُكتب
    في قاعدة البيانات يُكتب بتوقيت UTC.

    >>> ensure_utc(datetime(2026, 1, 1)).tzinfo is timezone.utc
    True
    """
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def is_past(value: datetime | None) -> bool:
    """هل مضى هذا الوقت؟ يتعامل مع التواريخ بلا منطقة زمنية بأمان."""
    normalized = ensure_utc(value)
    return normalized is not None and normalized <= utcnow()


def is_future(value: datetime | None) -> bool:
    """هل هذا الوقت في المستقبل؟"""
    normalized = ensure_utc(value)
    return normalized is not None and normalized > utcnow()


def age_in_years(birth_date: date, as_of: date | None = None) -> int:
    """يحسب العمر بالسنوات الكاملة."""
    reference = as_of or date.today()
    return (
        reference.year
        - birth_date.year
        - ((reference.month, reference.day) < (birth_date.month, birth_date.day))
    )
