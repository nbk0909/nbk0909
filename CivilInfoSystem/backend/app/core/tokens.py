"""إنشاء رموز JWT والتحقق منها.

نوعان من الرموز:
  * رمز الوصول (Access):  قصير العمر، يُحمل مع كل طلب، لا يُخزَّن في الخادم.
  * رمز التحديث (Refresh): طويل العمر، يُخزَّن مجزّأً في قاعدة البيانات
    ليمكن إبطاله، ويُستبدل بآخر عند كل استعمال (تدوير الرموز).
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt

from app.config import settings

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """رمز غير صالح — منتهٍ أو مزوَّر أو من نوع غير متوقَّع."""


@dataclass(frozen=True)
class TokenPayload:
    """محتوى رمز تم التحقق منه."""

    user_id: uuid.UUID
    username: str
    token_type: TokenType
    jti: str
    issued_at: datetime
    expires_at: datetime
    generation: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: uuid.UUID,
    username: str,
    generation: int = 0,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    """ينشئ رمز وصول قصير العمر.

    يُرجع: (الرمز، وقت انتهائه)
    """
    now = _now()
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        # جيل الرموز وقت الإصدار — يُقارن بجيل المستخدم عند كل طلب
        "gen": generation,
        # معرّف فريد لكل رمز — يسمح بتتبّعه في سجل التدقيق
        "jti": secrets.token_urlsafe(16),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if extra_claims:
        claims.update(extra_claims)

    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def create_refresh_token(user_id: uuid.UUID, username: str) -> tuple[str, datetime]:
    """ينشئ رمز تحديث طويل العمر."""
    now = _now()
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    claims = {
        "sub": str(user_id),
        "username": username,
        "type": "refresh",
        "jti": secrets.token_urlsafe(32),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def decode_token(token: str, expected_type: TokenType | None = None) -> TokenPayload:
    """يفكّ الرمز ويتحقق من توقيعه وصلاحيته ونوعه.

    يرفع TokenError برسالة عربية عامة — لا تُكشف تفاصيل سبب الرفض للمهاجم.
    """
    try:
        claims = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "type", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("انتهت صلاحية الجلسة") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("رمز غير صالح") from exc

    token_type = claims.get("type")

    # التحقق من النوع إلزامي: بدونه يصلح رمز التحديث كرمز وصول،
    # فيتحوّل رمز عمره أسبوع إلى مفتاح وصول دائم عملياً.
    if expected_type is not None and token_type != expected_type:
        raise TokenError("رمز غير صالح")

    try:
        user_id = uuid.UUID(claims["sub"])
    except (ValueError, KeyError) as exc:
        raise TokenError("رمز غير صالح") from exc

    return TokenPayload(
        user_id=user_id,
        username=claims.get("username", ""),
        token_type=token_type,
        jti=claims["jti"],
        issued_at=datetime.fromtimestamp(claims["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc),
        generation=int(claims.get("gen", 0)),
    )
