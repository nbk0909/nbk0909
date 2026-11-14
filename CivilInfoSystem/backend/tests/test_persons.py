"""اختبارات مسارات الأشخاص: الإنشاء والتعديل والبحث والعناوين."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models import Address, AuditAction, AuditLog, Gender, LifeStatus, Person
from app.utils.validators import generate_national_id
from tests.conftest import auth_headers

BASE = "/api/v1/persons"


def make_person_payload(**overrides) -> dict:
    """يبني حمولة إنشاء شخص صالحة."""
    birth = overrides.pop("birth_date", date(1990, 5, 15))
    serial = overrides.pop("serial", 1)

    payload = {
        "national_id": generate_national_id(birth, 10, serial),
        "first_name": "أحمد",
        "father_name": "عباس",
        "grandfather_name": "حسين",
        "family_name": "العباسي",
        "mother_full_name": "زهراء كاظم",
        "birth_date": birth.isoformat(),
        "gender": Gender.MALE.value,
        "nationality": "عراقي",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def created_person(client, clerk_user, governorate) -> dict:
    """شخص منشأ عبر الواجهة."""
    headers = auth_headers(client, "clerk")
    response = client.post(BASE, json=make_person_payload(), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# الإنشاء
# ---------------------------------------------------------------------------

def test_create_person(client, clerk_user, governorate):
    """إنشاء شخص بحمولة صالحة ينجح."""
    headers = auth_headers(client, "clerk")
    response = client.post(BASE, json=make_person_payload(), headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "أحمد عباس حسين العباسي"
    assert body["life_status"] == LifeStatus.ALIVE.value


def test_create_person_with_address(client, clerk_user, governorate):
    """إنشاء شخص مع عنوانه يسجّل العنوان كحالي."""
    headers = auth_headers(client, "clerk")
    payload = make_person_payload()
    payload["address"] = {
        "governorate_id": governorate.id,
        "quarter": "المنصور",
        "street": "609",
        "house_number": "12",
    }

    response = client.post(BASE, json=payload, headers=headers)

    assert response.status_code == 201
    address = response.json()["current_address"]
    assert address["quarter"] == "المنصور"
    assert address["is_current"] is True
    assert address["formatted"] == "المنصور - 609 - 12"


def test_create_rejects_invalid_national_id(client, clerk_user):
    """الرقم الوطني بخانة تدقيق خاطئة يُرفض."""
    headers = auth_headers(client, "clerk")
    payload = make_person_payload()
    # قلب آخر خانة يُبطل خانة التدقيق
    last = int(payload["national_id"][-1])
    payload["national_id"] = payload["national_id"][:-1] + str((last + 1) % 10)

    response = client.post(BASE, json=payload, headers=headers)
    assert response.status_code == 422


def test_create_rejects_duplicate_national_id(client, clerk_user, created_person):
    """الرقم الوطني المكرّر يُرفض بـ 409."""
    headers = auth_headers(client, "clerk")
    payload = make_person_payload()
    payload["national_id"] = created_person["national_id"]
    payload["first_name"] = "شخص"
    payload["family_name"] = "آخر"

    response = client.post(BASE, json=payload, headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "duplicate_national_id"


def test_create_rejects_future_birth_date(client, clerk_user):
    """تاريخ ميلاد في المستقبل يُرفض."""
    headers = auth_headers(client, "clerk")
    payload = make_person_payload()
    payload["birth_date"] = date(date.today().year + 1, 1, 1).isoformat()

    response = client.post(BASE, json=payload, headers=headers)
    assert response.status_code == 422


def test_create_requires_permission(client, viewer_user):
    """المستعلم لا ينشئ سجلات."""
    headers = auth_headers(client, "viewer")
    response = client.post(BASE, json=make_person_payload(), headers=headers)
    assert response.status_code == 403


def test_validation_error_uses_arabic_field_label(client, clerk_user):
    """رسالة خطأ التحقق تحمل اسم الحقل بالعربية."""
    headers = auth_headers(client, "clerk")
    payload = make_person_payload()
    payload["first_name"] = "أ"  # أقصر من الحد الأدنى

    response = client.post(BASE, json=payload, headers=headers)

    assert response.status_code == 422
    fields = [e["الحقل"] for e in response.json()["الأخطاء"]]
    assert "الاسم الأول" in fields


# ---------------------------------------------------------------------------
# القراءة
# ---------------------------------------------------------------------------

def test_get_person(client, clerk_user, created_person):
    """جلب شخص بمعرّفه."""
    headers = auth_headers(client, "clerk")
    response = client.get(f"{BASE}/{created_person['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["national_id"] == created_person["national_id"]


def test_get_by_national_id(client, clerk_user, created_person):
    """جلب شخص بالرقم الوطني."""
    headers = auth_headers(client, "clerk")
    response = client.get(
        f"{BASE}/by-national-id/{created_person['national_id']}", headers=headers
    )
    assert response.status_code == 200


def test_get_missing_person_404(client, clerk_user):
    """السجل غير الموجود يُرجع 404."""
    import uuid

    headers = auth_headers(client, "clerk")
    response = client.get(f"{BASE}/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# التعديل
# ---------------------------------------------------------------------------

def test_update_person(client, db, clerk_user, created_person):
    """تعديل بيانات شخص يُحدِّثها ويقيّدها في سجل التدقيق."""
    headers = auth_headers(client, "clerk")
    response = client.patch(
        f"{BASE}/{created_person['id']}",
        json={"occupation": "مهندس", "education_level": "بكالوريوس"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["occupation"] == "مهندس"

    entry = db.scalar(
        select(AuditLog).where(
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.resource_type == "persons",
        )
    )
    assert entry is not None
    assert entry.new_values["occupation"] == "مهندس"
    assert entry.old_values["occupation"] is None


def test_update_records_only_actual_changes(client, db, clerk_user, created_person):
    """إرسال القيم نفسها لا يُنشئ قيد تدقيق."""
    headers = auth_headers(client, "clerk")

    before = db.scalar(
        select(AuditLog).where(AuditLog.resource_type == "persons")
    )
    client.patch(
        f"{BASE}/{created_person['id']}",
        json={"nationality": created_person["nationality"]},
        headers=headers,
    )

    updates = db.scalars(
        select(AuditLog).where(
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.resource_type == "persons",
        )
    ).all()
    assert updates == []


def test_cannot_update_deceased_record(client, db, clerk_user, created_person):
    """سجل المتوفى لا يُعدَّل مباشرةً."""
    person = db.get(Person, __import__("uuid").UUID(created_person["id"]))
    person.life_status = LifeStatus.DECEASED
    db.commit()

    headers = auth_headers(client, "clerk")
    response = client.patch(
        f"{BASE}/{created_person['id']}",
        json={"occupation": "مهندس"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "deceased_record"


# ---------------------------------------------------------------------------
# العناوين
# ---------------------------------------------------------------------------

def test_change_address_keeps_history(client, db, clerk_user, governorate, created_person):
    """الانتقال إلى عنوان جديد يُغلق السابق ولا يحذفه."""
    headers = auth_headers(client, "clerk")
    person_id = created_person["id"]

    first = client.post(
        f"{BASE}/{person_id}/address",
        json={
            "governorate_id": governorate.id,
            "quarter": "المنصور",
            "valid_from": "2020-01-01",
        },
        headers=headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"{BASE}/{person_id}/address",
        json={
            "governorate_id": governorate.id,
            "quarter": "الكرادة",
            "valid_from": "2024-06-01",
        },
        headers=headers,
    )
    assert second.status_code == 200

    history = client.get(f"{BASE}/{person_id}/addresses", headers=headers).json()
    assert len(history) == 2

    current = [a for a in history if a["is_current"]]
    assert len(current) == 1
    assert current[0]["quarter"] == "الكرادة"

    previous = [a for a in history if not a["is_current"]][0]
    assert previous["quarter"] == "المنصور"
    assert previous["valid_to"] == "2024-06-01"


def test_address_date_must_not_precede_current(
    client, clerk_user, governorate, created_person
):
    """عنوان جديد بتاريخ يسبق الحالي يُرفض."""
    headers = auth_headers(client, "clerk")
    person_id = created_person["id"]

    client.post(
        f"{BASE}/{person_id}/address",
        json={
            "governorate_id": governorate.id,
            "quarter": "المنصور",
            "valid_from": "2024-01-01",
        },
        headers=headers,
    )
    response = client.post(
        f"{BASE}/{person_id}/address",
        json={
            "governorate_id": governorate.id,
            "quarter": "الكرادة",
            "valid_from": "2020-01-01",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "invalid_address_date"


# ---------------------------------------------------------------------------
# الحذف المنطقي
# ---------------------------------------------------------------------------

def test_soft_delete_hides_but_keeps_record(client, db, admin_user, created_person):
    """الحذف منطقي: السجل يختفي من الواجهة ويبقى في قاعدة البيانات."""
    import uuid

    headers = auth_headers(client, "admin")
    person_id = created_person["id"]

    response = client.delete(
        f"{BASE}/{person_id}?reason=سجل مكرر تم دمجه", headers=headers
    )
    assert response.status_code == 200

    assert client.get(f"{BASE}/{person_id}", headers=headers).status_code == 404

    # السجل ما زال في قاعدة البيانات
    row = db.get(Person, uuid.UUID(person_id))
    assert row is not None
    assert row.deleted_at is not None


def test_delete_requires_reason(client, admin_user, created_person):
    """الحذف بلا سبب يُرفض."""
    headers = auth_headers(client, "admin")
    response = client.delete(f"{BASE}/{created_person['id']}", headers=headers)
    assert response.status_code == 422


def test_deleted_national_id_stays_reserved(client, admin_user, created_person):
    """الرقم الوطني لسجل محذوف لا يُعاد استعماله."""
    headers = auth_headers(client, "admin")
    client.delete(f"{BASE}/{created_person['id']}?reason=اختبار الحجز", headers=headers)

    payload = make_person_payload()
    payload["national_id"] = created_person["national_id"]

    response = client.post(BASE, json=payload, headers=headers)
    assert response.status_code == 409


def test_restore_deleted_person(client, admin_user, created_person):
    """السجل المحذوف يمكن استعادته."""
    headers = auth_headers(client, "admin")
    person_id = created_person["id"]

    client.delete(f"{BASE}/{person_id}?reason=حذف بالخطأ", headers=headers)
    response = client.post(f"{BASE}/{person_id}/restore", headers=headers)

    assert response.status_code == 200
    assert client.get(f"{BASE}/{person_id}", headers=headers).status_code == 200


def test_clerk_cannot_delete(client, clerk_user, created_person):
    """موظف الإدخال لا يملك صلاحية الحذف."""
    headers = auth_headers(client, "clerk")
    response = client.delete(
        f"{BASE}/{created_person['id']}?reason=محاولة غير مصرّحة", headers=headers
    )
    assert response.status_code == 403
