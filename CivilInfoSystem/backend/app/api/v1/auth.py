"""مسارات المصادقة وإدارة الجلسة."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.core.deps import ActiveUser, CurrentUser, DbSession
from app.core.rate_limit import LOGIN_LIMIT, limiter
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
    TotpConfirmRequest,
    TotpDisableRequest,
    TotpSetupResponse,
    UserInfo,
    build_user_info,
)
from app.services import auth as auth_service
from app.services.auth import AuthError

router = APIRouter(prefix="/auth", tags=["المصادقة"])


def _auth_http_error(exc: AuthError) -> HTTPException:
    """يحوّل خطأ المصادقة إلى استجابة HTTP بالرمز المناسب."""
    # القفل والتعطيل ليسا فشل مصادقة بل منع وصول: 403 لا 401،
    # وإلا حاول العميل تجديد الرمز تلقائياً في حلقة لا تنتهي.
    forbidden_codes = {"account_locked", "account_disabled", "account_unavailable"}
    status_code = (
        status.HTTP_403_FORBIDDEN
        if exc.code in forbidden_codes
        else status.HTTP_401_UNAUTHORIZED
    )

    return HTTPException(
        status_code=status_code,
        detail={"نجاح": False, "الرسالة": exc.message, "الرمز": exc.code},
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="تسجيل الدخول",
    responses={
        401: {"description": "بيانات دخول غير صحيحة"},
        403: {"description": "الحساب مقفل أو معطّل"},
        429: {"description": "تجاوز حد المحاولات"},
    },
)
@limiter.limit(LOGIN_LIMIT)
async def login(
    request: Request,
    payload: LoginRequest,
    db: DbSession,
) -> TokenResponse:
    """يتحقق من بيانات الدخول ويُصدر رمزَي الوصول والتحديث.

    يُقفل الحساب مؤقتاً بعد عدد من المحاولات الفاشلة، وتُسجَّل كل محاولة
    في سجل التدقيق سواء نجحت أو فشلت.
    """
    try:
        pair = auth_service.authenticate(
            db,
            username=payload.username,
            password=payload.password,
            totp_code=payload.totp_code,
            request=request,
        )
    except AuthError as exc:
        raise _auth_http_error(exc) from exc

    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_at=pair.expires_at,
        must_change_password=pair.must_change_password,
        user=build_user_info(pair.user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="تجديد رمز الوصول",
)
@limiter.limit(LOGIN_LIMIT)
async def refresh(
    request: Request,
    payload: RefreshRequest,
    db: DbSession,
) -> TokenResponse:
    """يستبدل رمز تحديث صالح بزوج رموز جديد.

    الرمز القديم يُبطَل فور استعماله. تقديم رمز مُبطَل يُعدّ مؤشّر سرقة
    فتُبطَل كل جلسات المستخدم.
    """
    try:
        pair = auth_service.refresh_tokens(
            db, refresh_token=payload.refresh_token, request=request
        )
    except AuthError as exc:
        raise _auth_http_error(exc) from exc

    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_at=pair.expires_at,
        must_change_password=pair.must_change_password,
        user=build_user_info(pair.user),
    )


@router.post("/logout", response_model=MessageResponse, summary="تسجيل الخروج")
async def logout(
    request: Request,
    payload: LogoutRequest,
    db: DbSession,
    user: CurrentUser,
) -> MessageResponse:
    """ينهي الجلسة الحالية ويُبطل رمز التحديث المرافق."""
    auth_service.logout(
        db, user=user, refresh_token=payload.refresh_token, request=request
    )
    return MessageResponse(الرسالة="تم تسجيل الخروج بنجاح")


@router.post(
    "/logout-all", response_model=MessageResponse, summary="إنهاء كل الجلسات"
)
async def logout_all(
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> MessageResponse:
    """يُبطل كل جلسات المستخدم على جميع الأجهزة."""
    count = auth_service.revoke_all_sessions(db, user.id)
    auth_service.logout(db, user=user, request=request)
    return MessageResponse(الرسالة=f"تم إنهاء {count} جلسة")


@router.get("/me", response_model=UserInfo, summary="بيانات المستخدم الحالي")
async def me(user: CurrentUser) -> UserInfo:
    """يُرجع بيانات المستخدم الحالي مع أدواره وصلاحياته."""
    return build_user_info(user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="تغيير كلمة المرور",
)
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    db: DbSession,
    user: CurrentUser,
) -> MessageResponse:
    """يغيّر كلمة المرور وينهي كل الجلسات الأخرى.

    متاح للمستخدم المُلزَم بتغيير كلمة مروره (يستعمل CurrentUser لا
    ActiveUser)، وإلا تعذّر عليه الخروج من هذا الإلزام.
    """
    try:
        auth_service.change_password(
            db,
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            request=request,
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"نجاح": False, "الرسالة": exc.message, "الرمز": exc.code},
        ) from exc

    return MessageResponse(
        الرسالة="تم تغيير كلمة المرور. أُنهيت الجلسات الأخرى، سجّل الدخول من جديد"
    )


# ---------------------------------------------------------------------------
# المصادقة الثنائية
# ---------------------------------------------------------------------------

@router.post(
    "/totp/setup",
    response_model=TotpSetupResponse,
    summary="بدء تفعيل المصادقة الثنائية",
)
async def totp_setup(db: DbSession, user: ActiveUser) -> TotpSetupResponse:
    """يولّد سرّاً ورمز QR — لا يكتمل التفعيل إلا بتأكيد رمز صحيح."""
    secret, qr_code = auth_service.begin_totp_setup(db, user=user)
    return TotpSetupResponse(secret=secret, qr_code=qr_code)


@router.post(
    "/totp/confirm",
    response_model=MessageResponse,
    summary="تأكيد تفعيل المصادقة الثنائية",
)
async def totp_confirm(
    request: Request,
    payload: TotpConfirmRequest,
    db: DbSession,
    user: ActiveUser,
) -> MessageResponse:
    """يفعّل المصادقة الثنائية بعد التحقق من رمز صحيح."""
    try:
        auth_service.confirm_totp_setup(
            db, user=user, code=payload.code, request=request
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"نجاح": False, "الرسالة": exc.message, "الرمز": exc.code},
        ) from exc

    return MessageResponse(الرسالة="تم تفعيل المصادقة الثنائية")


@router.post(
    "/totp/disable",
    response_model=MessageResponse,
    summary="تعطيل المصادقة الثنائية",
)
async def totp_disable(
    request: Request,
    payload: TotpDisableRequest,
    db: DbSession,
    user: ActiveUser,
) -> MessageResponse:
    """يعطّل المصادقة الثنائية بعد تأكيد كلمة المرور."""
    try:
        auth_service.disable_totp(
            db, user=user, password=payload.password, request=request
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"نجاح": False, "الرسالة": exc.message, "الرمز": exc.code},
        ) from exc

    return MessageResponse(الرسالة="تم تعطيل المصادقة الثنائية")
