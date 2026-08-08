"""اختبارات تحديد معدّل الطلبات.

يُشغَّل هذا الملف في عملية مستقلة بحدّ منخفض، لأن المُزيِّن @limiter.limit
يلتقط قيمة الحد وقت استيراد الوحدة فلا تنفع تغييرها بعد ذلك:

    RATE_LIMIT_LOGIN_PER_MINUTE=3 pytest tests/test_rate_limit.py

بقية الاختبارات ترفع الحد إلى 1000/دقيقة حتى لا يمنعها المحدِّد.
"""

from __future__ import annotations

import os

import pytest

from app.config import settings

LOGIN_URL = "/api/v1/auth/login"

# يعمل هذا الملف فقط عندما يكون الحد منخفضاً بما يكفي لبلوغه في اختبار
pytestmark = pytest.mark.skipif(
    settings.RATE_LIMIT_LOGIN_PER_MINUTE > 10,
    reason=(
        "يتطلّب حدّاً منخفضاً — شغّله بـ "
        "RATE_LIMIT_LOGIN_PER_MINUTE=3 pytest tests/test_rate_limit.py"
    ),
)


def test_login_rate_limited(client, admin_user):
    """تجاوز حد محاولات الدخول يُرجع 429 برسالة عربية."""
    limit = settings.RATE_LIMIT_LOGIN_PER_MINUTE
    statuses = []

    for _ in range(limit + 2):
        response = client.post(
            LOGIN_URL, json={"username": "admin", "password": "Wrong@123"}
        )
        statuses.append(response.status_code)

    assert 429 in statuses, f"لم يُفعَّل التحديد: {statuses}"

    blocked = next(
        r
        for r in [
            client.post(LOGIN_URL, json={"username": "admin", "password": "Wrong@1"})
        ]
        if r.status_code == 429
    )
    assert "الحد المسموح" in blocked.json()["الرسالة"]
    assert blocked.headers["Retry-After"] == "60"


def test_rate_limit_blocks_before_lockout_is_bypassed(client, admin_user):
    """المحدِّد يوقف التخمين الآلي قبل استنزاف عدّاد القفل.

    القفل وحده لا يكفي: مهاجم يجرّب على آلاف الحسابات يبقى تحت حد القفل
    لكل حساب. تحديد المعدّل يوقفه على مستوى المصدر لا الحساب.
    """
    for _ in range(settings.RATE_LIMIT_LOGIN_PER_MINUTE + 1):
        client.post(LOGIN_URL, json={"username": "admin", "password": "Wrong@123"})

    # حتى تبديل اسم المستخدم لا يتجاوز الحد، لأنه محسوب على المصدر
    response = client.post(
        LOGIN_URL, json={"username": "viewer", "password": "Wrong@123"}
    )
    assert response.status_code == 429


def test_rate_limit_key_uses_user_when_authenticated():
    """مفتاح التحديد يعتمد على المستخدم إن كان معروفاً، وإلا على العنوان."""
    import uuid
    from types import SimpleNamespace

    from app.core.rate_limit import rate_limit_key

    user_id = uuid.uuid4()
    authenticated = SimpleNamespace(
        state=SimpleNamespace(current_user=SimpleNamespace(id=user_id)),
        client=SimpleNamespace(host="10.0.0.5"),
        headers={},
    )
    assert rate_limit_key(authenticated) == f"user:{user_id}"

    anonymous = SimpleNamespace(
        state=SimpleNamespace(),
        client=SimpleNamespace(host="10.0.0.5"),
        headers={},
    )
    assert rate_limit_key(anonymous).startswith("ip:")
