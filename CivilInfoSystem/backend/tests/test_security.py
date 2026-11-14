"""اختبارات التشفير والتجزئة والمصادقة الثنائية."""

from __future__ import annotations

import time

import pyotp
import pytest

from app.core.encryption import decrypt_field, encrypt_field, hash_token
from app.core.security import (
    MAX_PASSWORD_BYTES,
    check_password_policy,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.core.totp import generate_secret, verify_totp
from app.core.tokens import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from tests.conftest import PASSWORD, auth_headers


# ---------------------------------------------------------------------------
# كلمات المرور
# ---------------------------------------------------------------------------

def test_hash_and_verify():
    """التجزئة والتحقق يعملان."""
    hashed = hash_password("MyPassword@2026")
    assert hashed != "MyPassword@2026"
    assert verify_password("MyPassword@2026", hashed)
    assert not verify_password("WrongPassword@1", hashed)


def test_hash_is_salted():
    """التجزئتان لكلمة المرور نفسها مختلفتان (ملح عشوائي).

    بدون الملح تكشف التجزئات المتطابقة أن مستخدمَين يستعملان كلمة المرور
    نفسها، ويصبح جدول التجزئات قابلاً للكسر دفعة واحدة.
    """
    first = hash_password("SamePassword@1")
    second = hash_password("SamePassword@1")

    assert first != second
    assert verify_password("SamePassword@1", first)
    assert verify_password("SamePassword@1", second)


def test_password_over_72_bytes_rejected():
    """كلمة المرور الأطول من حدّ bcrypt تُرفض بدل أن تُقتطع بصمت.

    الاقتطاع الصامت يعني أن أول 72 بايت وحدها هي المؤثّرة، فتصبح كلمة
    مرور طويلة أضعف مما يظنّ صاحبها.
    """
    with pytest.raises(ValueError, match="الحد الأقصى"):
        hash_password("a" * (MAX_PASSWORD_BYTES + 1))


def test_arabic_password_byte_length():
    """الحرف العربي يشغل بايتين، فيُحسب الحد بالبايتات لا بالأحرف."""
    # 40 حرفاً عربياً = 80 بايت > 72
    with pytest.raises(ValueError):
        hash_password("ك" * 40)

    # 30 حرفاً = 60 بايت، مقبولة
    hashed = hash_password("ك" * 30)
    assert verify_password("ك" * 30, hashed)


def test_verify_handles_corrupt_hash():
    """التجزئة التالفة تُعامَل كفشل تحقق لا كخطأ نظام."""
    assert not verify_password("anything", "not-a-real-hash")
    assert not verify_password("anything", "")


def test_needs_rehash_detects_weak_cost():
    """التجزئة بعامل تكلفة أقل تُعلَّم لإعادة التجزئة."""
    import bcrypt

    weak = bcrypt.hashpw(b"pass", bcrypt.gensalt(rounds=4)).decode()
    strong = hash_password("pass")

    assert needs_rehash(weak)
    assert not needs_rehash(strong)


@pytest.mark.parametrize(
    "password,should_pass",
    [
        ("Str0ng@Password", True),
        ("short1@A", False),          # قصيرة
        ("alllowercase1@", False),    # بلا حرف كبير
        ("ALLUPPERCASE1@", False),    # بلا حرف صغير
        ("NoDigitsHere@", False),     # بلا رقم
        ("NoSymbols12345", False),    # بلا رمز
    ],
)
def test_password_policy(password, should_pass):
    """سياسة كلمات المرور تُطبَّق على كل الحالات."""
    problems = check_password_policy(password)
    assert (problems == []) is should_pass


# ---------------------------------------------------------------------------
# التشفير
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_roundtrip():
    """التشفير وفكّه يعيدان النص الأصلي."""
    for text in ["JBSWY3DPEHPK3PXP", "نص عربي حسّاس", ""]:
        assert decrypt_field(encrypt_field(text)) == text


def test_encryption_output_differs_each_time():
    """تشفير القيمة نفسها مرتين يعطي ناتجين مختلفين."""
    first = encrypt_field("same-secret")
    second = encrypt_field("same-secret")

    assert first != second
    assert decrypt_field(first) == decrypt_field(second) == "same-secret"


def test_encrypt_none_passthrough():
    """القيمة الفارغة تمرّ كما هي."""
    assert encrypt_field(None) is None
    assert decrypt_field(None) is None


def test_decrypt_invalid_returns_none():
    """النص المشفّر التالف يُرجع None لا يرفع استثناءً."""
    assert decrypt_field("not-valid-ciphertext") is None


def test_hash_token_is_deterministic_and_irreversible():
    """تجزئة الرمز ثابتة، ولا تحتوي الرمز الأصلي."""
    token = "some-refresh-token-value"
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != hash_token(token + "x")
    assert token not in hash_token(token)


# ---------------------------------------------------------------------------
# رموز JWT
# ---------------------------------------------------------------------------

def test_access_token_roundtrip():
    """رمز الوصول يُفكّ ويحمل البيانات الصحيحة."""
    import uuid

    user_id = uuid.uuid4()
    token, expires = create_access_token(user_id, "tester")
    payload = decode_token(token, expected_type="access")

    assert payload.user_id == user_id
    assert payload.username == "tester"
    assert payload.token_type == "access"


def test_token_type_confusion_rejected():
    """لا يُقبل رمز من نوع غير المتوقَّع."""
    import uuid

    access, _ = create_access_token(uuid.uuid4(), "tester")
    refresh, _ = create_refresh_token(uuid.uuid4(), "tester")

    with pytest.raises(TokenError):
        decode_token(access, expected_type="refresh")

    with pytest.raises(TokenError):
        decode_token(refresh, expected_type="access")


def test_token_signed_with_other_key_rejected():
    """رمز موقّع بمفتاح آخر يُرفض."""
    import jwt as pyjwt

    forged = pyjwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000000",
            "type": "access",
            "jti": "x",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        "attacker-key",
        algorithm="HS256",
    )

    with pytest.raises(TokenError):
        decode_token(forged, expected_type="access")


def test_token_without_signature_rejected():
    """رمز بخوارزمية none يُرفض — ثغرة كلاسيكية في JWT."""
    import jwt as pyjwt

    unsigned = pyjwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000000",
            "type": "access",
            "jti": "x",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        key="",
        algorithm="none",
    )

    with pytest.raises(TokenError):
        decode_token(unsigned, expected_type="access")


def test_token_missing_required_claims_rejected():
    """رمز ناقص الحقول الإلزامية يُرفض."""
    import jwt as pyjwt

    from app.config import settings

    incomplete = pyjwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )

    with pytest.raises(TokenError):
        decode_token(incomplete, expected_type="access")


# ---------------------------------------------------------------------------
# المصادقة الثنائية
# ---------------------------------------------------------------------------

def test_totp_verify_correct_code():
    """الرمز الصحيح يُقبل."""
    secret = generate_secret()
    code = pyotp.TOTP(secret).now()
    assert verify_totp(secret, code)


def test_totp_rejects_wrong_code():
    """الرمز الخاطئ يُرفض."""
    secret = generate_secret()
    assert not verify_totp(secret, "000000")
    assert not verify_totp(secret, "abcdef")
    assert not verify_totp(secret, "")


def test_totp_accepts_formatted_code():
    """الرمز بمسافات أو شرطات يُقبل كما يكتبه المستخدم."""
    secret = generate_secret()
    code = pyotp.TOTP(secret).now()

    assert verify_totp(secret, f"{code[:3]} {code[3:]}")
    assert verify_totp(secret, f"{code[:3]}-{code[3:]}")


def test_totp_full_setup_flow(client, db, admin_user):
    """دورة تفعيل المصادقة الثنائية كاملة ثم الدخول بها."""
    headers = auth_headers(client, "admin")

    # 1) البدء: يولّد سرّاً ورمز QR لكن لا يفعّل بعد
    setup = client.post("/api/v1/auth/totp/setup", headers=headers).json()
    assert setup["secret"]
    assert setup["qr_code"].startswith("data:image/png;base64,")

    db.refresh(admin_user)
    assert admin_user.totp_enabled is False
    # السرّ مخزَّن مشفّراً لا صريحاً
    assert admin_user.totp_secret_encrypted != setup["secret"]
    assert decrypt_field(admin_user.totp_secret_encrypted) == setup["secret"]

    # 2) رمز خاطئ لا يفعّل
    bad = client.post(
        "/api/v1/auth/totp/confirm", json={"code": "000000"}, headers=headers
    )
    assert bad.status_code == 400
    db.refresh(admin_user)
    assert admin_user.totp_enabled is False

    # 3) الرمز الصحيح يفعّل
    code = pyotp.TOTP(setup["secret"]).now()
    ok = client.post(
        "/api/v1/auth/totp/confirm", json={"code": code}, headers=headers
    )
    assert ok.status_code == 200
    db.refresh(admin_user)
    assert admin_user.totp_enabled is True

    # 4) الدخول الآن يتطلّب الرمز
    without = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": PASSWORD}
    )
    assert without.status_code == 401
    assert without.json()["detail"]["الرمز"] == "totp_required"

    # 5) الدخول برمز خاطئ يُرفض
    wrong = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": PASSWORD, "totp_code": "000000"},
    )
    assert wrong.status_code == 401

    # 6) الدخول بالرمز الصحيح ينجح
    good = client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": PASSWORD,
            "totp_code": pyotp.TOTP(setup["secret"]).now(),
        },
    )
    assert good.status_code == 200


def test_totp_disable_requires_password(client, db, admin_user):
    """تعطيل المصادقة الثنائية يتطلّب تأكيد كلمة المرور."""
    headers = auth_headers(client, "admin")
    setup = client.post("/api/v1/auth/totp/setup", headers=headers).json()
    client.post(
        "/api/v1/auth/totp/confirm",
        json={"code": pyotp.TOTP(setup["secret"]).now()},
        headers=headers,
    )

    # كلمة مرور خاطئة لا تعطّل
    assert client.post(
        "/api/v1/auth/totp/disable",
        json={"password": "Wrong@123"},
        headers=headers,
    ).status_code == 400

    db.refresh(admin_user)
    assert admin_user.totp_enabled is True

    # الصحيحة تعطّل وتمحو السرّ
    assert client.post(
        "/api/v1/auth/totp/disable",
        json={"password": PASSWORD},
        headers=headers,
    ).status_code == 200

    db.refresh(admin_user)
    assert admin_user.totp_enabled is False
    assert admin_user.totp_secret_encrypted is None


# ---------------------------------------------------------------------------
# ترويسات الأمان
# ---------------------------------------------------------------------------

def test_security_headers_present(client):
    """ترويسات الأمان موجودة في كل استجابة."""
    response = client.get("/health")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_db_errors_do_not_leak_details(client, db, admin_user, monkeypatch):
    """أخطاء قاعدة البيانات لا تكشف تفاصيلها للمستخدم."""
    from sqlalchemy.exc import IntegrityError

    def boom(*args, **kwargs):
        raise IntegrityError("SECRET SQL DETAIL", {}, Exception("internal"))

    monkeypatch.setattr("app.services.auth.authenticate", boom)

    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": PASSWORD}
    )

    assert response.status_code == 500
    assert "SECRET SQL DETAIL" not in response.text
    assert response.json()["الرسالة"] == "حدث خطأ أثناء معالجة الطلب"
