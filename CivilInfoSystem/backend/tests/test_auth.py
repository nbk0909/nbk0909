"""اختبارات المصادقة وإدارة الجلسة."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.config import settings
from app.core.tokens import create_access_token, create_refresh_token, decode_token
from app.models import AuditAction, AuditLog, RefreshToken, User
from tests.conftest import PASSWORD, auth_headers, login

LOGIN_URL = "/api/v1/auth/login"


# ---------------------------------------------------------------------------
# الدخول
# ---------------------------------------------------------------------------

def test_login_success(client, admin_user):
    """الدخول ببيانات صحيحة يُصدر رمزَي وصول وتحديث."""
    response = client.post(
        LOGIN_URL, json={"username": "admin", "password": PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "admin"
    assert "persons.create" in body["user"]["permissions"]


def test_login_wrong_password(client, admin_user):
    """كلمة مرور خاطئة تُرفض بـ 401."""
    response = client.post(
        LOGIN_URL, json={"username": "admin", "password": "WrongPass@123"}
    )
    assert response.status_code == 401


def test_login_unknown_user_same_message_as_wrong_password(client, admin_user):
    """اسم غير موجود وكلمة مرور خاطئة يُعطيان الرسالة نفسها.

    اختلاف الرسالتين يسمح للمهاجم بحصر أسماء المستخدمين الصحيحة.
    """
    unknown = client.post(
        LOGIN_URL, json={"username": "ghost", "password": PASSWORD}
    )
    wrong = client.post(
        LOGIN_URL, json={"username": "admin", "password": "WrongPass@123"}
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"]["الرسالة"] == wrong.json()["detail"]["الرسالة"]


def test_login_normalizes_username_case(client, admin_user):
    """اسم المستخدم غير حسّاس لحالة الأحرف."""
    response = client.post(
        LOGIN_URL, json={"username": "ADMIN", "password": PASSWORD}
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# قفل الحساب
# ---------------------------------------------------------------------------

def test_account_locks_after_max_failed_attempts(client, db, admin_user):
    """يُقفل الحساب بعد بلوغ حد المحاولات الفاشلة."""
    limit = settings.MAX_FAILED_LOGIN_ATTEMPTS

    for _ in range(limit):
        client.post(LOGIN_URL, json={"username": "admin", "password": "Wrong@123"})

    db.refresh(admin_user)
    assert admin_user.failed_login_attempts == limit
    assert admin_user.is_locked

    # حتى كلمة المرور الصحيحة تُرفض ما دام الحساب مقفلاً
    response = client.post(LOGIN_URL, json={"username": "admin", "password": PASSWORD})
    assert response.status_code == 403
    assert "مقفل" in response.json()["detail"]["الرسالة"]


def test_successful_login_resets_failed_counter(client, db, admin_user):
    """الدخول الناجح يصفّر عدّاد المحاولات الفاشلة."""
    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS - 1):
        client.post(LOGIN_URL, json={"username": "admin", "password": "Wrong@123"})

    db.refresh(admin_user)
    assert admin_user.failed_login_attempts > 0

    client.post(LOGIN_URL, json={"username": "admin", "password": PASSWORD})
    db.refresh(admin_user)
    assert admin_user.failed_login_attempts == 0
    assert admin_user.last_login_at is not None


def test_disabled_account_rejected(client, db, admin_user):
    """الحساب المعطّل يُرفض بـ 403."""
    admin_user.is_active = False
    db.commit()

    response = client.post(LOGIN_URL, json={"username": "admin", "password": PASSWORD})
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# الرموز
# ---------------------------------------------------------------------------

def test_refresh_token_cannot_be_used_as_access_token(client, admin_user):
    """رمز التحديث لا يصلح للوصول إلى المسارات المحمية.

    لولا التحقق من نوع الرمز لتحوّل رمز عمره أسبوع إلى مفتاح وصول دائم.
    """
    body = login(client, "admin")
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['refresh_token']}"},
    )
    assert response.status_code == 401


def test_access_token_cannot_be_used_to_refresh(client, admin_user):
    """رمز الوصول لا يصلح لتجديد الجلسة."""
    body = login(client, "admin")
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["access_token"]}
    )
    assert response.status_code == 401


def test_tampered_token_rejected(client, admin_user):
    """رمز مُعدَّل التوقيع يُرفض."""
    body = login(client, "admin")
    tampered = body["access_token"][:-6] + "AAAAAA"

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert response.status_code == 401


def test_expired_token_rejected(client, db, admin_user, monkeypatch):
    """الرمز المنتهي يُرفض."""
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", -1)
    token, _ = create_access_token(admin_user.id, admin_user.username)

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert "انتهت" in response.json()["detail"]["الرسالة"]


def test_missing_token_rejected(client):
    """الطلب بلا رمز يُرفض."""
    assert client.get("/api/v1/auth/me").status_code == 401


def test_token_for_deleted_user_rejected(client, db, admin_user):
    """رمز مستخدم محذوف منطقياً يُرفض."""
    headers = auth_headers(client, "admin")
    admin_user.deleted_at = datetime.now(timezone.utc)
    db.commit()

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


# ---------------------------------------------------------------------------
# تدوير رموز التحديث
# ---------------------------------------------------------------------------

def test_refresh_rotates_token(client, admin_user):
    """التجديد يُصدر رمز تحديث جديداً مختلفاً عن السابق."""
    first = login(client, "admin")
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )

    assert response.status_code == 200
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]


def test_old_refresh_token_revoked_after_rotation(client, admin_user):
    """الرمز القديم يُبطَل فور استعماله."""
    first = login(client, "admin")
    client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})

    replay = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert replay.status_code == 401


def test_refresh_token_reuse_revokes_all_sessions(client, db, admin_user):
    """إعادة استعمال رمز مُبطَل تُبطل كل جلسات المستخدم.

    إعادة الاستعمال مؤشّر سرقة: الرمز الشرعي أُبطل عند أول استعمال، فمن
    يقدّمه ثانيةً إمّا نسخة مسروقة أو الضحية بعد سرقة رمزه.
    """
    first = login(client, "admin")
    second = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    ).json()

    # الرمز الثاني صالح في هذه اللحظة
    assert db.scalar(
        select(RefreshToken).where(RefreshToken.revoked_at.is_(None))
    ) is not None

    # إعادة استعمال الأول تُبطل كل شيء
    client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})

    active = db.scalars(
        select(RefreshToken).where(RefreshToken.revoked_at.is_(None))
    ).all()
    assert active == []

    # والرمز الثاني لم يعد صالحاً رغم أنه لم يُستعمل قط
    assert client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}
    ).status_code == 401


def test_unknown_refresh_token_rejected(client, admin_user):
    """رمز تحديث موقّع لكنه غير مخزَّن يُرفض."""
    token, _ = create_refresh_token(uuid.uuid4(), "ghost")
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# الخروج
# ---------------------------------------------------------------------------

def test_logout_revokes_refresh_token(client, db, admin_user):
    """الخروج يُبطل رمز التحديث."""
    body = login(client, "admin")
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": body["refresh_token"]},
        headers=headers,
    )
    assert response.status_code == 200

    assert client.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    ).status_code == 401


def test_logout_all_revokes_every_session(client, db, admin_user):
    """إنهاء كل الجلسات يُبطل رموز جميع الأجهزة."""
    first = login(client, "admin")
    second = login(client, "admin")

    client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )

    for body in (first, second):
        assert client.post(
            "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
        ).status_code == 401


# ---------------------------------------------------------------------------
# كلمة المرور
# ---------------------------------------------------------------------------

def test_change_password_success(client, db, admin_user):
    """تغيير كلمة المرور ينجح ويسمح بالدخول بالجديدة."""
    headers = auth_headers(client, "admin")
    new_password = "BrandNew@2026x"

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": new_password},
        headers=headers,
    )
    assert response.status_code == 200

    assert client.post(
        LOGIN_URL, json={"username": "admin", "password": new_password}
    ).status_code == 200
    assert client.post(
        LOGIN_URL, json={"username": "admin", "password": PASSWORD}
    ).status_code == 401


def test_change_password_wrong_current_rejected(client, admin_user):
    """كلمة المرور الحالية الخاطئة تمنع التغيير."""
    headers = auth_headers(client, "admin")
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Wrong@123", "new_password": "BrandNew@2026x"},
        headers=headers,
    )
    assert response.status_code == 400


def test_change_password_rejects_weak(client, admin_user):
    """كلمة مرور لا تحقّق السياسة تُرفض."""
    headers = auth_headers(client, "admin")
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "weakpassword"},
        headers=headers,
    )
    assert response.status_code in (400, 422)


def test_change_password_rejects_same_password(client, admin_user):
    """إعادة كلمة المرور نفسها تُرفض."""
    headers = auth_headers(client, "admin")
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": PASSWORD},
        headers=headers,
    )
    assert response.status_code == 400


def test_change_password_invalidates_old_access_tokens(client, db, admin_user):
    """رموز الوصول المُصدرة قبل تغيير كلمة المرور تُرفض بعده فوراً.

    لو ظلّت صالحة لبقيت جلسة المهاجم مفتوحة رغم تغيير الضحية لكلمتها،
    وهو ما يُفرغ تغيير كلمة المرور من معناه. لا انتظار هنا عمداً: النافذة
    التي تقع فيها العملية كلها داخل ثانية واحدة هي بالضبط الحالة التي
    كانت تفلت من الفحص.
    """
    headers = auth_headers(client, "admin")
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "BrandNew@2026x"},
        headers=headers,
    )

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401

    # والرمز الجديد يعمل فوراً — لا نافذة انتظار بعد التغيير
    fresh = login(client, "admin", "BrandNew@2026x")
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {fresh['access_token']}"},
    ).status_code == 200


def test_logout_all_invalidates_access_tokens_not_just_refresh(client, db, admin_user):
    """إنهاء كل الجلسات يُبطل رموز الوصول القائمة، لا رموز التحديث وحدها.

    رمز الوصول لا يُراجَع في قاعدة البيانات، فإبطال رموز التحديث وحدها
    يترك المهاجم يعمل حتى انتهاء مدة رمزه.
    """
    first = login(client, "admin")
    headers = {"Authorization": f"Bearer {first['access_token']}"}

    second = login(client, "admin")
    other_headers = {"Authorization": f"Bearer {second['access_token']}"}

    assert client.get("/api/v1/auth/me", headers=other_headers).status_code == 200

    client.post("/api/v1/auth/logout-all", headers=headers)

    assert client.get("/api/v1/auth/me", headers=other_headers).status_code == 401

    # الدخول بعدها يعطي رمزاً صالحاً فوراً
    fresh = login(client, "admin")
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {fresh['access_token']}"},
    ).status_code == 200


def test_must_change_password_blocks_other_endpoints(client, new_user):
    """المستخدم المُلزَم بتغيير كلمة مروره لا يصل إلى بقية النظام."""
    body = login(client, "newbie")
    assert body["must_change_password"] is True

    headers = {"Authorization": f"Bearer {body['access_token']}"}

    # /me متاح لأنه لا يتطلّب ActiveUser
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    # لكن تفعيل المصادقة الثنائية (يتطلّب ActiveUser) محجوب
    response = client.post("/api/v1/auth/totp/setup", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"]["الإجراء"] == "change_password"


def test_must_change_password_allows_changing_it(client, new_user):
    """المستخدم المُلزَم يستطيع تغيير كلمة مروره فعلاً."""
    body = login(client, "newbie")
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "BrandNew@2026x"},
        headers=headers,
    )
    assert response.status_code == 200

    after = login(client, "newbie", "BrandNew@2026x")
    assert after["must_change_password"] is False


# ---------------------------------------------------------------------------
# سجل التدقيق
# ---------------------------------------------------------------------------

def test_successful_login_recorded(client, db, admin_user):
    """الدخول الناجح يُقيَّد في سجل التدقيق."""
    login(client, "admin")

    entry = db.scalar(
        select(AuditLog).where(AuditLog.action == AuditAction.LOGIN)
    )
    assert entry is not None
    assert entry.username == "admin"
    assert entry.succeeded is True


def test_failed_login_recorded(client, db, admin_user):
    """المحاولة الفاشلة تُقيَّد حتى مع التراجع عن باقي التغييرات."""
    client.post(LOGIN_URL, json={"username": "admin", "password": "Wrong@123"})

    entry = db.scalar(
        select(AuditLog).where(AuditLog.action == AuditAction.FAILED_ATTEMPT)
    )
    assert entry is not None
    assert entry.succeeded is False


def test_unknown_username_recorded_without_user_id(client, db):
    """محاولة الدخول باسم غير موجود تُسجَّل باسمه دون معرّف مستخدم."""
    client.post(LOGIN_URL, json={"username": "ghost", "password": PASSWORD})

    entry = db.scalar(
        select(AuditLog).where(AuditLog.action == AuditAction.FAILED_ATTEMPT)
    )
    assert entry is not None
    assert entry.username == "ghost"
    assert entry.user_id is None


def test_audit_never_stores_password(client, db, admin_user):
    """سجل التدقيق لا يحتوي كلمة مرور ولا تجزئتها بأي حال."""
    headers = auth_headers(client, "admin")
    client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "BrandNew@2026x"},
        headers=headers,
    )

    for entry in db.scalars(select(AuditLog)).all():
        blob = f"{entry.old_values} {entry.new_values} {entry.error_message}"
        assert PASSWORD not in blob
        assert "BrandNew@2026x" not in blob
        assert "$2b$" not in blob


def test_token_usable_immediately_after_creation(client, db, roles):
    """رمز يُصدَر في الثانية نفسها التي أُنشئ فيها الحساب يبقى صالحاً.

    اختبار انحدار: حقل iat في JWT بدقّة الثانية بينما يخزّن PostgreSQL
    الطابع الزمني بدقّة الميكروثانية، فكان الرمز يُرفض فور إصداره لأن
    password_changed_at يسبقه بكسور الثانية.
    """
    from app.core.security import hash_password
    from app.models import User

    user = User(
        username="fresh",
        password_hash=hash_password(PASSWORD),
        full_name_ar="مستخدم جديد",
        must_change_password=False,
    )
    user.roles = [roles["viewer"]]
    db.add(user)
    db.commit()

    body = login(client, "fresh")
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert response.status_code == 200
