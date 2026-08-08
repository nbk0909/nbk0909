"""تبعيات FastAPI: المستخدم الحالي، وفرض الصلاحيات، ونطاق العمل."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.tokens import TokenError, decode_token
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

# auto_error=False ليصدر معالجنا رسالة عربية بدل رسالة Starlette الإنجليزية
_bearer = HTTPBearer(auto_error=False, description="رمز الوصول بصيغة Bearer")

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"نجاح": False, "الرسالة": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"نجاح": False, "الرسالة": detail},
    )


async def get_current_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """يستخرج المستخدم الحالي من رمز الوصول ويتحقق من أهليته."""
    if credentials is None:
        raise _unauthorized("مطلوب تسجيل الدخول")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError as exc:
        raise _unauthorized(str(exc)) from exc

    user = db.scalar(
        select(User).where(User.id == payload.user_id, User.deleted_at.is_(None))
    )

    if user is None:
        raise _unauthorized("الحساب غير موجود")

    if not user.is_active:
        raise _forbidden("الحساب معطّل")

    if user.is_locked:
        raise _forbidden("الحساب مقفل مؤقتاً")

    # الرموز الصادرة قبل آخر إبطال تُرفض ولو بقيت صالحة زمنياً: تغيير
    # كلمة المرور أو إنهاء كل الجلسات يزيد جيل الرموز، فتسقط كل الرموز
    # القديمة دفعةً واحدة بينما يبقى الرمز الجديد صالحاً.
    if payload.generation != user.token_generation:
        raise _unauthorized("انتهت صلاحية الجلسة. سجّل الدخول من جديد")

    # يُتاح الكائن للطبقات اللاحقة (سجل التدقيق مثلاً) دون إعادة استعلام
    request.state.current_user = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_active_user(user: CurrentUser) -> User:
    """المستخدم الحالي بشرط ألا يكون مُلزَماً بتغيير كلمة المرور.

    الحساب المُنشأ حديثاً يحمل كلمة مرور يعرفها من أنشأه، فلا يُسمح له
    بأي عملية قبل تغييرها.
    """
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "نجاح": False,
                "الرسالة": "يجب تغيير كلمة المرور قبل استخدام النظام",
                "الإجراء": "change_password",
            },
        )
    return user


ActiveUser = Annotated[User, Depends(get_active_user)]


# ---------------------------------------------------------------------------
# فرض الصلاحيات
# ---------------------------------------------------------------------------

class RequirePermission:
    """تبعية تتحقق من امتلاك المستخدم صلاحية معيّنة.

    الاستخدام:
        @router.post("/persons", dependencies=[Depends(RequirePermission("persons.create"))])

    أو للحصول على المستخدم في آن واحد:
        def create(user: User = Depends(RequirePermission("persons.create"))):
    """

    def __init__(self, *permission_codes: str, require_all: bool = False) -> None:
        if not permission_codes:
            raise ValueError("يجب تحديد صلاحية واحدة على الأقل")

        self.permission_codes = permission_codes
        self.require_all = require_all

    async def __call__(self, user: ActiveUser) -> User:
        checker = all if self.require_all else any
        granted = checker(user.has_permission(code) for code in self.permission_codes)

        if not granted:
            logger.info(
                "رُفض وصول المستخدم %s إلى صلاحية %s",
                user.username,
                ", ".join(self.permission_codes),
            )
            raise _forbidden("ليست لديك صلاحية تنفيذ هذه العملية")

        return user


class RequireRole:
    """تبعية تتحقق من انتماء المستخدم إلى دور معيّن."""

    def __init__(self, *role_codes: str) -> None:
        if not role_codes:
            raise ValueError("يجب تحديد دور واحد على الأقل")
        self.role_codes = set(role_codes)

    async def __call__(self, user: ActiveUser) -> User:
        user_roles = {
            role.code for role in user.roles if role.deleted_at is None
        }

        if not (user_roles & self.role_codes):
            raise _forbidden("ليست لديك صلاحية تنفيذ هذه العملية")

        return user


# اختصار شائع: عمليات لا يقوم بها إلا مدير النظام
require_admin = RequireRole("admin")


# ---------------------------------------------------------------------------
# نطاق العمل الجغرافي
# ---------------------------------------------------------------------------

def enforce_governorate_scope(user: User, governorate_id: int | None) -> None:
    """يمنع الموظف من العمل خارج محافظته.

    مدير النظام والمدقّق يريان كل المحافظات؛ الموظف المرتبط بمحافظة
    لا يتجاوزها. الموظف غير المرتبط بمحافظة يُعامَل كموظف مركزي.
    """
    privileged = {"admin", "auditor"}
    if any(role.code in privileged for role in user.roles):
        return

    if user.governorate_id is None or governorate_id is None:
        return

    if user.governorate_id != governorate_id:
        raise _forbidden("لا تملك صلاحية العمل على سجلات خارج محافظتك")
