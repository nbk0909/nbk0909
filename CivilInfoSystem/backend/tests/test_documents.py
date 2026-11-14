"""اختبارات الوثائق والمعاملات والتقسيمات الإدارية."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models import (
    District,
    DocumentStatus,
    DocumentType,
    Gender,
    Person,
    RequestStatus,
    RequestType,
    Subdistrict,
)
from app.utils.validators import generate_national_id
from tests.conftest import auth_headers

API = "/api/v1"


@pytest.fixture
def person(db, governorate) -> Person:
    p = Person(
        national_id=generate_national_id(date(1990, 1, 1), 10, 1),
        first_name="أحمد",
        father_name="عباس",
        grandfather_name="حسين",
        family_name="العباسي",
        mother_full_name="زهراء كاظم",
        birth_date=date(1990, 1, 1),
        gender=Gender.MALE,
        birth_governorate_id=governorate.id,
    )
    db.add(p)
    db.commit()
    return p


def _document_payload(person, **overrides) -> dict:
    payload = {
        "person_id": str(person.id),
        "document_type": DocumentType.NATIONAL_CARD.value,
        "document_number": "NC00000001",
        "issue_date": "2020-01-15",
        "expiry_date": "2030-01-15",
        "issuing_authority": "مديرية أحوال بغداد",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# الوثائق
# ---------------------------------------------------------------------------

def test_issue_document(client, clerk_user, person):
    """إصدار وثيقة ينجح ويحسب الأيام المتبقية."""
    headers = auth_headers(client, "clerk")
    response = client.post(
        f"{API}/documents", json=_document_payload(person), headers=headers
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["document_number"] == "NC00000001"
    assert body["status"] == DocumentStatus.VALID.value
    assert body["is_expired"] is False
    assert body["days_until_expiry"] > 0


def test_only_one_valid_document_per_type(client, clerk_user, person):
    """لا تسري وثيقتان من النوع نفسه للشخص في آن واحد."""
    headers = auth_headers(client, "clerk")
    client.post(f"{API}/documents", json=_document_payload(person), headers=headers)

    response = client.post(
        f"{API}/documents",
        json=_document_payload(person, document_number="NC00000002"),
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "active_document_exists"


def test_replacement_after_marking_lost(client, clerk_user, person):
    """بدل الفاقد يُصدر بعد تعليم الوثيقة القديمة مفقودة."""
    headers = auth_headers(client, "clerk")
    first = client.post(
        f"{API}/documents", json=_document_payload(person), headers=headers
    ).json()

    marked = client.patch(
        f"{API}/documents/{first['id']}/status",
        json={"status": DocumentStatus.LOST.value, "notes": "فُقدت أثناء السفر"},
        headers=headers,
    )
    assert marked.status_code == 200
    assert marked.json()["status"] == DocumentStatus.LOST.value

    replacement = client.post(
        f"{API}/documents",
        json=_document_payload(
            person, document_number="NC00000002", replaces_document_id=first["id"]
        ),
        headers=headers,
    )
    assert replacement.status_code == 201


def test_duplicate_document_number_rejected(client, db, clerk_user, person, governorate):
    """رقم الوثيقة فريد على مستوى النظام لا الشخص."""
    headers = auth_headers(client, "clerk")
    client.post(f"{API}/documents", json=_document_payload(person), headers=headers)

    other = Person(
        national_id=generate_national_id(date(1995, 1, 1), 10, 2),
        first_name="سعد",
        father_name="جاسم",
        grandfather_name="علي",
        family_name="التميمي",
        mother_full_name="نور حسن",
        birth_date=date(1995, 1, 1),
        gender=Gender.MALE,
    )
    db.add(other)
    db.commit()

    response = client.post(
        f"{API}/documents", json=_document_payload(other), headers=headers
    )

    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "duplicate_number"


def test_expiry_must_follow_issue(client, clerk_user, person):
    """تاريخ الانتهاء قبل الإصدار يُرفض."""
    headers = auth_headers(client, "clerk")
    response = client.post(
        f"{API}/documents",
        json=_document_payload(person, issue_date="2020-01-15", expiry_date="2019-01-15"),
        headers=headers,
    )
    assert response.status_code == 422


def test_expiring_documents_report(client, clerk_user, person):
    """تقرير الوثائق التي توشك على الانتهاء يلتقطها."""
    headers = auth_headers(client, "clerk")
    soon = (date.today() + timedelta(days=30)).isoformat()

    client.post(
        f"{API}/documents",
        json=_document_payload(
            person, issue_date="2020-01-15", expiry_date=soon
        ),
        headers=headers,
    )

    response = client.get(
        f"{API}/documents/expiring", params={"days": 60}, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["person"]["full_name"].startswith("أحمد")


def test_expiring_excludes_far_future(client, clerk_user, person):
    """الوثيقة البعيدة الانتهاء لا تظهر في التقرير."""
    headers = auth_headers(client, "clerk")
    client.post(f"{API}/documents", json=_document_payload(person), headers=headers)

    response = client.get(
        f"{API}/documents/expiring", params={"days": 30}, headers=headers
    )
    assert response.json()["total"] == 0


def test_person_documents_list(client, clerk_user, person):
    """قائمة وثائق الشخص."""
    headers = auth_headers(client, "clerk")
    client.post(f"{API}/documents", json=_document_payload(person), headers=headers)
    client.post(
        f"{API}/documents",
        json=_document_payload(
            person,
            document_type=DocumentType.PASSPORT.value,
            document_number="A1234567",
        ),
        headers=headers,
    )

    response = client.get(f"{API}/persons/{person.id}/documents", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# المعاملات
# ---------------------------------------------------------------------------

def test_submit_request_generates_reference(client, clerk_user, person):
    """تقديم معاملة يولّد رقماً مرجعياً."""
    headers = auth_headers(client, "clerk")
    response = client.post(
        f"{API}/requests",
        json={
            "person_id": str(person.id),
            "request_type": RequestType.RENEW.value,
            "subject": "تجديد البطاقة الوطنية",
            "fee_amount": "25000",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["reference_number"].startswith(f"REQ-{date.today().year}-")
    assert body["status"] == RequestStatus.SUBMITTED.value


def test_approve_request(client, registrar_user, person):
    """اعتماد معاملة يسجّل القرار ووقته."""
    headers = auth_headers(client, "registrar")
    created = client.post(
        f"{API}/requests",
        json={
            "person_id": str(person.id),
            "request_type": RequestType.ISSUE.value,
            "subject": "إصدار شهادة جنسية",
        },
        headers=headers,
    ).json()

    response = client.patch(
        f"{API}/requests/{created['id']}/decision",
        json={"status": RequestStatus.APPROVED.value},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == RequestStatus.APPROVED.value
    assert body["decision_at"] is not None


def test_rejection_requires_reason(client, registrar_user, person):
    """رفض معاملة بلا سبب يُرفض."""
    headers = auth_headers(client, "registrar")
    created = client.post(
        f"{API}/requests",
        json={
            "person_id": str(person.id),
            "request_type": RequestType.AMEND.value,
            "subject": "تصحيح اسم الأم في السجل",
        },
        headers=headers,
    ).json()

    response = client.patch(
        f"{API}/requests/{created['id']}/decision",
        json={"status": RequestStatus.REJECTED.value},
        headers=headers,
    )

    assert response.status_code == 422


def test_rejection_with_reason(client, registrar_user, person):
    """الرفض مع سبب ينجح ويحفظ السبب."""
    headers = auth_headers(client, "registrar")
    created = client.post(
        f"{API}/requests",
        json={
            "person_id": str(person.id),
            "request_type": RequestType.AMEND.value,
            "subject": "تصحيح اسم الأم في السجل",
        },
        headers=headers,
    ).json()

    response = client.patch(
        f"{API}/requests/{created['id']}/decision",
        json={
            "status": RequestStatus.REJECTED.value,
            "rejection_reason": "المستمسكات المقدَّمة غير كافية",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["rejection_reason"] == "المستمسكات المقدَّمة غير كافية"


def test_cannot_decide_twice(client, registrar_user, person):
    """المعاملة المنتهية لا يُعاد البتّ فيها."""
    headers = auth_headers(client, "registrar")
    created = client.post(
        f"{API}/requests",
        json={
            "person_id": str(person.id),
            "request_type": RequestType.ISSUE.value,
            "subject": "إصدار بطاقة عائلة",
        },
        headers=headers,
    ).json()

    client.patch(
        f"{API}/requests/{created['id']}/decision",
        json={"status": RequestStatus.APPROVED.value},
        headers=headers,
    )
    response = client.patch(
        f"{API}/requests/{created['id']}/decision",
        json={"status": RequestStatus.REJECTED.value, "rejection_reason": "تراجع"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "request_closed"


def test_clerk_cannot_approve(client, clerk_user, person):
    """موظف الإدخال لا يعتمد المعاملات."""
    headers = auth_headers(client, "clerk")
    created = client.post(
        f"{API}/requests",
        json={
            "person_id": str(person.id),
            "request_type": RequestType.ISSUE.value,
            "subject": "إصدار بطاقة عائلة",
        },
        headers=headers,
    ).json()

    response = client.patch(
        f"{API}/requests/{created['id']}/decision",
        json={"status": RequestStatus.APPROVED.value},
        headers=headers,
    )

    assert response.status_code == 403


def test_filter_requests_by_status(client, registrar_user, person):
    """تصفية المعاملات بالحالة."""
    headers = auth_headers(client, "registrar")
    for subject in ("معاملة أولى للاختبار", "معاملة ثانية للاختبار"):
        client.post(
            f"{API}/requests",
            json={
                "person_id": str(person.id),
                "request_type": RequestType.ISSUE.value,
                "subject": subject,
            },
            headers=headers,
        )

    response = client.get(
        f"{API}/requests",
        params={"status": RequestStatus.SUBMITTED.value},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2


# ---------------------------------------------------------------------------
# التقسيمات الإدارية
# ---------------------------------------------------------------------------

def test_governorates_tree(client, db, viewer_user, governorate):
    """شجرة التقسيمات تُرجع المحافظات مع أقضيتها ونواحيها."""
    district = District(governorate_id=governorate.id, code="1001", name_ar="الكرخ")
    db.add(district)
    db.commit()
    db.add(Subdistrict(district_id=district.id, code="100101", name_ar="المنصور"))
    db.commit()

    headers = auth_headers(client, "viewer")
    response = client.get(f"{API}/locations/governorates", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body[0]["name_ar"] == "بغداد"
    assert body[0]["districts"][0]["name_ar"] == "الكرخ"
    assert body[0]["districts"][0]["subdistricts"][0]["name_ar"] == "المنصور"
