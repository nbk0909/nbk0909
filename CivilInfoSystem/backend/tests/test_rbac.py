"""اختبارات الصلاحيات والأدوار ونطاق العمل الجغرافي."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.deps import (
    RequirePermission,
    RequireRole,
    enforce_governorate_scope,
    get_current_user,
)
from app.database import get_db
from app.main import app
from app.models import Governorate, User
from tests.conftest import PASSWORD, auth_headers


# ---------------------------------------------------------------------------
# مسارات اختبار تُركَّب على التطبيق نفسه
# ---------------------------------------------------------------------------

@pytest.fixture
def protected_client(client):
    """يضيف مسارات محمية مؤقتة لاختبار فرض الصلاحيات."""
    from fastapi import APIRouter

    router = APIRouter(prefix="/_test", tags=["اختبار"])

    @router.get("/read")
    async def read_route(user: User = Depends(RequirePermission("persons.read"))):
        return {"ok": True, "user": user.username}

    @router.post("/create")
    async def create_route(user: User = Depends(RequirePermission("persons.create"))):
        return {"ok": True}

    @router.delete("/delete")
    async def delete_route(user: User = Depends(RequirePermission("persons.delete"))):
        return {"ok": True}

    @router.get("/any")
    async def any_route(
        user: User = Depends(RequirePermission("persons.delete", "persons.read")),
    ):
        return {"ok": True}

    @router.get("/all")
    async def all_route(
        user: User = Depends(
            RequirePermission("persons.delete", "persons.read", require_all=True)
        ),
    ):
        return {"ok": True}

    @router.get("/admin-only")
    async def admin_route(user: User = Depends(RequireRole("admin"))):
        return {"ok": True}

    app.include_router(router)
    yield client
    app.router.routes = [
        r for r in app.router.routes if not getattr(r, "path", "").startswith("/_test")
    ]


# ---------------------------------------------------------------------------
# فرض الصلاحيات
# ---------------------------------------------------------------------------

def test_permission_granted(protected_client, admin_user):
    """المستخدم صاحب الصلاحية يمرّ."""
    headers = auth_headers(protected_client, "admin")
    response = protected_client.get("/_test/read", headers=headers)
    assert response.status_code == 200


def test_permission_denied(protected_client, viewer_user):
    """المستخدم بلا الصلاحية يُرفض بـ 403 لا 401."""
    headers = auth_headers(protected_client, "viewer")
    response = protected_client.post("/_test/create", headers=headers)

    assert response.status_code == 403
    assert "صلاحية" in response.json()["detail"]["الرسالة"]


def test_viewer_can_read_but_not_write(protected_client, viewer_user):
    """المستعلم يقرأ ولا يكتب."""
    headers = auth_headers(protected_client, "viewer")

    assert protected_client.get("/_test/read", headers=headers).status_code == 200
    assert protected_client.post("/_test/create", headers=headers).status_code == 403
    assert protected_client.delete("/_test/delete", headers=headers).status_code == 403


def test_clerk_can_create_but_not_delete(protected_client, clerk_user):
    """موظف الإدخال ينشئ ويعدّل لكنه لا يحذف.

    الحذف في السجل المدني عملية لا يقوم بها موظف الإدخال بحال.
    """
    headers = auth_headers(protected_client, "clerk")

    assert protected_client.post("/_test/create", headers=headers).status_code == 200
    assert protected_client.delete("/_test/delete", headers=headers).status_code == 403


def test_any_permission_mode(protected_client, viewer_user):
    """وضع «أي صلاحية»: امتلاك واحدة يكفي."""
    headers = auth_headers(protected_client, "viewer")
    assert protected_client.get("/_test/any", headers=headers).status_code == 200


def test_all_permissions_mode(protected_client, viewer_user, admin_user):
    """وضع «كل الصلاحيات»: نقص واحدة يمنع."""
    viewer_headers = auth_headers(protected_client, "viewer")
    admin_headers = auth_headers(protected_client, "admin")

    assert protected_client.get("/_test/all", headers=viewer_headers).status_code == 403
    assert protected_client.get("/_test/all", headers=admin_headers).status_code == 200


def test_role_check(protected_client, admin_user, viewer_user):
    """التحقق بالدور يعمل مستقلاً عن الصلاحيات."""
    assert protected_client.get(
        "/_test/admin-only", headers=auth_headers(protected_client, "admin")
    ).status_code == 200

    assert protected_client.get(
        "/_test/admin-only", headers=auth_headers(protected_client, "viewer")
    ).status_code == 403


def test_unauthenticated_gets_401_not_403(protected_client):
    """الطلب بلا مصادقة يُرفض بـ 401 لا 403.

    الفرق مهم للعميل: 401 تعني «سجّل الدخول»، و403 تعني «لا تحاول».
    """
    assert protected_client.get("/_test/read").status_code == 401


def test_revoked_role_removes_permission(protected_client, db, viewer_user, roles):
    """حذف الدور منطقياً يُسقط صلاحياته فوراً."""
    headers = auth_headers(protected_client, "viewer")
    assert protected_client.get("/_test/read", headers=headers).status_code == 200

    from datetime import datetime, timezone

    roles["viewer"].deleted_at = datetime.now(timezone.utc)
    db.commit()

    assert protected_client.get("/_test/read", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# نطاق العمل الجغرافي
# ---------------------------------------------------------------------------

def test_scope_blocks_other_governorate(db, roles, governorate):
    """الموظف لا يعمل خارج محافظته."""
    other = Governorate(code="20", name_ar="البصرة")
    db.add(other)
    db.commit()

    clerk = User(
        username="scoped",
        password_hash="x",
        full_name_ar="موظف",
        governorate_id=governorate.id,
    )
    clerk.roles = [roles["clerk"]]

    # محافظته: مسموح
    enforce_governorate_scope(clerk, governorate.id)

    # محافظة أخرى: ممنوع
    with pytest.raises(HTTPException) as exc:
        enforce_governorate_scope(clerk, other.id)
    assert exc.value.status_code == 403


def test_scope_allows_admin_everywhere(db, roles, governorate):
    """مدير النظام يعمل على كل المحافظات."""
    other = Governorate(code="20", name_ar="البصرة")
    db.add(other)
    db.commit()

    admin = User(
        username="boss",
        password_hash="x",
        full_name_ar="مدير",
        governorate_id=governorate.id,
    )
    admin.roles = [roles["admin"]]

    # لا يرفع استثناءً على أي محافظة
    enforce_governorate_scope(admin, other.id)


def test_scope_allows_central_employee(db, roles, governorate):
    """الموظف غير المرتبط بمحافظة يُعامَل كموظف مركزي."""
    central = User(
        username="central",
        password_hash="x",
        full_name_ar="موظف مركزي",
        governorate_id=None,
    )
    central.roles = [roles["clerk"]]

    enforce_governorate_scope(central, governorate.id)


# ---------------------------------------------------------------------------
# نموذج الصلاحيات
# ---------------------------------------------------------------------------

def test_has_permission_ignores_deleted_roles(db, viewer_user, roles):
    """has_permission يتجاهل الأدوار المحذوفة منطقياً."""
    assert viewer_user.has_permission("persons.read")

    from datetime import datetime, timezone

    roles["viewer"].deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(viewer_user)

    assert not viewer_user.has_permission("persons.read")


def test_require_permission_rejects_empty_list():
    """إنشاء تبعية بلا صلاحيات خطأ برمجي يُكشف فوراً."""
    with pytest.raises(ValueError):
        RequirePermission()

    with pytest.raises(ValueError):
        RequireRole()
