"""اختبارات الواقعات المدنية وشجرة العائلة."""

from __future__ import annotations

from datetime import date

import pytest

from app.models import (
    Gender,
    LifeStatus,
    MaritalStatus,
    MarriageContract,
    Person,
    RelationType,
)
from app.utils.validators import generate_national_id
from tests.conftest import auth_headers

API = "/api/v1"


def _person(db, governorate, *, first, family, birth, gender, serial, mother="فاطمة علي"):
    person = Person(
        national_id=generate_national_id(birth, 10, serial),
        first_name=first,
        father_name="عبد الله",
        grandfather_name="محمد",
        family_name=family,
        mother_full_name=mother,
        birth_date=birth,
        gender=gender,
        birth_governorate_id=governorate.id,
    )
    db.add(person)
    return person


@pytest.fixture
def couple(db, governorate) -> tuple[Person, Person]:
    """زوجان في سن الزواج من عائلتين مختلفتين."""
    husband = _person(
        db, governorate, first="أحمد", family="العباسي",
        birth=date(1985, 3, 10), gender=Gender.MALE, serial=1,
    )
    wife = _person(
        db, governorate, first="ليلى", family="الجبوري",
        birth=date(1990, 7, 22), gender=Gender.FEMALE, serial=2, mother="آمنة طه",
    )
    db.commit()
    return husband, wife


@pytest.fixture
def child(db, governorate) -> Person:
    """طفل بلا واقعة ميلاد مسجّلة."""
    person = _person(
        db, governorate, first="كريم", family="العباسي",
        birth=date(2015, 4, 5), gender=Gender.MALE, serial=3,
    )
    db.commit()
    return person


# ---------------------------------------------------------------------------
# الزواج
# ---------------------------------------------------------------------------

def _marriage_payload(husband, wife, governorate, **overrides) -> dict:
    payload = {
        "husband_id": str(husband.id),
        "wife_id": str(wife.id),
        "contract_date": "2014-06-01",
        "governorate_id": governorate.id,
        "officiant_name": "الشيخ عبد الرحمن",
        "witness1_name": "محمد جاسم الطائي",
        "witness2_name": "عادل نوري الساعدي",
        "dowry_prompt": "3000000",
        "dowry_deferred": "10000000",
    }
    payload.update(overrides)
    return payload


def test_register_marriage(client, db, registrar_user, governorate, couple):
    """تسجيل عقد زواج يُحدِّث الحالة الاجتماعية للطرفين."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")

    response = client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate),
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["contract_number"].startswith("M-2014-")
    assert body["is_active"] is True

    db.refresh(husband)
    db.refresh(wife)
    assert husband.marital_status == MaritalStatus.MARRIED
    assert wife.marital_status == MaritalStatus.MARRIED


def test_marriage_creates_spouse_relations(client, db, registrar_user, governorate, couple):
    """عقد الزواج يُنشئ علاقة الزوجية باتجاهيها."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")
    client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate),
        headers=headers,
    )

    from app.services import family

    wives = family.get_relations(db, husband.id, types=(RelationType.WIFE,))
    husbands = family.get_relations(db, wife.id, types=(RelationType.HUSBAND,))

    assert len(wives) == 1 and wives[0].related_person_id == wife.id
    assert len(husbands) == 1 and husbands[0].related_person_id == husband.id


def test_marriage_rejects_underage(client, db, registrar_user, governorate):
    """عقد زواج لمن دون السن القانونية يُرفض."""
    husband = _person(
        db, governorate, first="سعد", family="التميمي",
        birth=date(1990, 1, 1), gender=Gender.MALE, serial=10,
    )
    wife = _person(
        db, governorate, first="نور", family="الدليمي",
        birth=date(2012, 1, 1), gender=Gender.FEMALE, serial=11,
    )
    db.commit()

    headers = auth_headers(client, "registrar")
    response = client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate, contract_date="2026-01-01"),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "underage"


def test_marriage_rejects_siblings(client, db, registrar_user, governorate):
    """الزواج بين أخ وأخت يُرفض."""
    from app.models import FamilyRelation

    father = _person(
        db, governorate, first="عباس", family="العباسي",
        birth=date(1960, 1, 1), gender=Gender.MALE, serial=20,
    )
    db.commit()

    brother = _person(
        db, governorate, first="حسن", family="العباسي",
        birth=date(1990, 1, 1), gender=Gender.MALE, serial=21,
    )
    sister = _person(
        db, governorate, first="زينب", family="العباسي",
        birth=date(1992, 1, 1), gender=Gender.FEMALE, serial=22,
    )
    db.commit()

    # أب مشترك
    for kid in (brother, sister):
        db.add(
            FamilyRelation(
                person_id=kid.id,
                related_person_id=father.id,
                relation_type=RelationType.FATHER,
            )
        )
    db.commit()

    headers = auth_headers(client, "registrar")
    response = client.post(
        f"{API}/marriages",
        json=_marriage_payload(brother, sister, governorate, contract_date="2020-01-01"),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "prohibited_relation"


def test_marriage_rejects_already_married_wife(
    client, db, registrar_user, governorate, couple
):
    """الزوجة المرتبطة بعقد نشط لا تُعقد ثانيةً."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")
    client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate),
        headers=headers,
    )

    other = _person(
        db, governorate, first="سامي", family="الطائي",
        birth=date(1988, 1, 1), gender=Gender.MALE, serial=30,
    )
    db.commit()

    response = client.post(
        f"{API}/marriages",
        json=_marriage_payload(other, wife, governorate, contract_date="2020-01-01"),
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "wife_already_married"


def test_marriage_rejects_swapped_genders(client, db, registrar_user, governorate, couple):
    """تبديل دورَي الزوج والزوجة يُرفض."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")

    response = client.post(
        f"{API}/marriages",
        json=_marriage_payload(wife, husband, governorate),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "gender_mismatch"


# ---------------------------------------------------------------------------
# الميلاد
# ---------------------------------------------------------------------------

def test_register_birth_links_parents(
    client, db, registrar_user, governorate, couple, child
):
    """واقعة الميلاد تربط المولود بوالديه في شجرة العائلة."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")

    response = client.post(
        f"{API}/births",
        json={
            "person_id": str(child.id),
            "father_id": str(husband.id),
            "mother_id": str(wife.id),
            "birth_date": child.birth_date.isoformat(),
            "governorate_id": governorate.id,
            "hospital_name": "مستشفى بغداد التعليمي",
            "birth_weight_grams": 3200,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["record_number"].startswith("B-2015-")

    from app.services import family

    fathers = family.get_relations(db, child.id, types=(RelationType.FATHER,))
    sons = family.get_relations(db, husband.id, types=(RelationType.SON,))

    assert fathers[0].related_person_id == husband.id
    assert sons[0].related_person_id == child.id


def test_birth_rejects_duplicate(client, registrar_user, governorate, couple, child):
    """واقعة ميلاد ثانية لنفس المولود تُرفض."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")
    payload = {
        "person_id": str(child.id),
        "father_id": str(husband.id),
        "birth_date": child.birth_date.isoformat(),
        "governorate_id": governorate.id,
    }

    assert client.post(f"{API}/births", json=payload, headers=headers).status_code == 201
    response = client.post(f"{API}/births", json=payload, headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "duplicate_birth"


def test_birth_rejects_date_mismatch(client, registrar_user, governorate, child):
    """تاريخ الواقعة يجب أن يطابق تاريخ الميلاد في سجل المولود."""
    headers = auth_headers(client, "registrar")
    response = client.post(
        f"{API}/births",
        json={
            "person_id": str(child.id),
            "birth_date": "2016-01-01",
            "governorate_id": governorate.id,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "date_mismatch"


def test_birth_rejects_impossible_parent_age(client, db, registrar_user, governorate):
    """فارق عمري مستحيل بين الوالد والمولود يُرفض."""
    parent = _person(
        db, governorate, first="علي", family="النجفي",
        birth=date(2010, 1, 1), gender=Gender.MALE, serial=40,
    )
    baby = _person(
        db, governorate, first="حسين", family="النجفي",
        birth=date(2018, 1, 1), gender=Gender.MALE, serial=41,
    )
    db.commit()

    headers = auth_headers(client, "registrar")
    response = client.post(
        f"{API}/births",
        json={
            "person_id": str(baby.id),
            "father_id": str(parent.id),
            "birth_date": "2018-01-01",
            "governorate_id": governorate.id,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "invalid_parent_age"


def test_birth_rejects_same_person_as_both_parents(
    client, registrar_user, governorate, couple, child
):
    """الأب والأم لا يكونان الشخص نفسه."""
    husband, _ = couple
    headers = auth_headers(client, "registrar")

    response = client.post(
        f"{API}/births",
        json={
            "person_id": str(child.id),
            "father_id": str(husband.id),
            "mother_id": str(husband.id),
            "birth_date": child.birth_date.isoformat(),
            "governorate_id": governorate.id,
        },
        headers=headers,
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# الوفاة
# ---------------------------------------------------------------------------

def test_register_death_applies_all_effects(
    client, db, registrar_user, governorate, couple
):
    """الوفاة تُحدِّث الحالة وتُنهي العقد وتُرمِّل الزوجة — في عملية واحدة."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")

    client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate),
        headers=headers,
    )

    response = client.post(
        f"{API}/deaths",
        json={
            "person_id": str(husband.id),
            "death_date": "2024-06-15",
            "governorate_id": governorate.id,
            "cause_of_death": "أمراض القلب",
            "cause_category": "طبيعية",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    db.refresh(husband)
    db.refresh(wife)

    assert husband.life_status == LifeStatus.DECEASED
    assert wife.marital_status == MaritalStatus.WIDOWED

    contract = db.scalar(
        __import__("sqlalchemy").select(MarriageContract).where(
            MarriageContract.husband_id == husband.id
        )
    )
    assert contract.is_active is False

    from app.services import family

    active_spouse_relations = [
        r
        for r in family.get_relations(db, husband.id, types=family.SPOUSE_RELATIONS)
        if r.is_active
    ]
    assert active_spouse_relations == []


def test_death_rejects_before_birth(client, registrar_user, governorate, couple):
    """تاريخ وفاة يسبق الميلاد يُرفض."""
    husband, _ = couple
    headers = auth_headers(client, "registrar")

    response = client.post(
        f"{API}/deaths",
        json={
            "person_id": str(husband.id),
            "death_date": "1980-01-01",
            "governorate_id": governorate.id,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "death_before_birth"


def test_death_rejects_duplicate(client, registrar_user, governorate, couple):
    """تسجيل وفاة لشخص متوفى مسبقاً يُرفض."""
    husband, _ = couple
    headers = auth_headers(client, "registrar")
    payload = {
        "person_id": str(husband.id),
        "death_date": "2024-06-15",
        "governorate_id": governorate.id,
    }

    assert client.post(f"{API}/deaths", json=payload, headers=headers).status_code == 201
    response = client.post(f"{API}/deaths", json=payload, headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "already_deceased"


def test_death_rejects_future_date(client, registrar_user, governorate, couple):
    """تاريخ وفاة في المستقبل يُرفض."""
    husband, _ = couple
    headers = auth_headers(client, "registrar")

    response = client.post(
        f"{API}/deaths",
        json={
            "person_id": str(husband.id),
            "death_date": date(date.today().year + 1, 1, 1).isoformat(),
            "governorate_id": governorate.id,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_marriage_rejects_deceased_party(client, db, registrar_user, governorate, couple):
    """لا يُعقد زواج على متوفى."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")

    client.post(
        f"{API}/deaths",
        json={
            "person_id": str(husband.id),
            "death_date": "2024-01-01",
            "governorate_id": governorate.id,
        },
        headers=headers,
    )

    response = client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "party_deceased"


# ---------------------------------------------------------------------------
# الطلاق
# ---------------------------------------------------------------------------

def test_register_divorce(client, db, registrar_user, governorate, couple):
    """الطلاق يُنهي العقد ويُحدِّث حالة الطرفين."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")

    contract = client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate),
        headers=headers,
    ).json()

    response = client.post(
        f"{API}/divorces",
        json={
            "marriage_id": contract["id"],
            "divorce_date": "2022-03-10",
            "divorce_type": "بائن",
            "custody_notes": "حضانة الأبناء للأم",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    db.refresh(husband)
    db.refresh(wife)
    assert husband.marital_status == MaritalStatus.DIVORCED
    assert wife.marital_status == MaritalStatus.DIVORCED


def test_divorce_rejects_before_marriage(client, registrar_user, governorate, couple):
    """تاريخ طلاق يسبق العقد يُرفض."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")

    contract = client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate),
        headers=headers,
    ).json()

    response = client.post(
        f"{API}/divorces",
        json={"marriage_id": contract["id"], "divorce_date": "2010-01-01"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "divorce_before_marriage"


def test_divorce_rejects_inactive_contract(client, registrar_user, governorate, couple):
    """لا يُطلَّق عقد منتهٍ مسبقاً."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")

    contract = client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate),
        headers=headers,
    ).json()

    payload = {"marriage_id": contract["id"], "divorce_date": "2022-03-10"}
    assert client.post(f"{API}/divorces", json=payload, headers=headers).status_code == 201

    response = client.post(f"{API}/divorces", json=payload, headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "contract_inactive"


def test_wife_can_remarry_after_divorce(client, db, registrar_user, governorate, couple):
    """المطلّقة يجوز عقد زواجها من جديد."""
    husband, wife = couple
    headers = auth_headers(client, "registrar")

    contract = client.post(
        f"{API}/marriages",
        json=_marriage_payload(husband, wife, governorate),
        headers=headers,
    ).json()
    client.post(
        f"{API}/divorces",
        json={"marriage_id": contract["id"], "divorce_date": "2022-03-10"},
        headers=headers,
    )

    other = _person(
        db, governorate, first="كاظم", family="الموسوي",
        birth=date(1986, 5, 5), gender=Gender.MALE, serial=50,
    )
    db.commit()

    response = client.post(
        f"{API}/marriages",
        json=_marriage_payload(other, wife, governorate, contract_date="2023-08-01"),
        headers=headers,
    )

    assert response.status_code == 201, response.text
