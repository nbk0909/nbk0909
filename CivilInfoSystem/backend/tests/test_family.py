"""اختبارات شجرة العائلة وكشف التعارضات المنطقية."""

from __future__ import annotations

from datetime import date

import pytest

from app.models import FamilyRelation, Gender, LifeStatus, Person, RelationType
from app.utils.validators import generate_national_id
from tests.conftest import auth_headers

BASE = "/api/v1/persons"


def _person(db, governorate, *, first, family, birth, gender, serial):
    person = Person(
        national_id=generate_national_id(birth, 10, serial),
        first_name=first,
        father_name="عبد الله",
        grandfather_name="محمد",
        family_name=family,
        mother_full_name="فاطمة علي",
        birth_date=birth,
        gender=gender,
        birth_governorate_id=governorate.id,
    )
    db.add(person)
    return person


@pytest.fixture
def three_generations(db, governorate) -> dict[str, Person]:
    """ثلاثة أجيال مترابطة: جدّ وأب وأم وابن وبنت وحفيد."""
    people = {
        "grandfather": _person(
            db, governorate, first="عباس", family="العباسي",
            birth=date(1940, 1, 1), gender=Gender.MALE, serial=1,
        ),
        "grandmother": _person(
            db, governorate, first="زهراء", family="الموسوي",
            birth=date(1945, 1, 1), gender=Gender.FEMALE, serial=2,
        ),
        "father": _person(
            db, governorate, first="أحمد", family="العباسي",
            birth=date(1968, 1, 1), gender=Gender.MALE, serial=3,
        ),
        "mother": _person(
            db, governorate, first="ليلى", family="الجبوري",
            birth=date(1972, 1, 1), gender=Gender.FEMALE, serial=4,
        ),
        "son": _person(
            db, governorate, first="كريم", family="العباسي",
            birth=date(1998, 1, 1), gender=Gender.MALE, serial=5,
        ),
        "daughter": _person(
            db, governorate, first="سارة", family="العباسي",
            birth=date(2001, 1, 1), gender=Gender.FEMALE, serial=6,
        ),
        "grandson": _person(
            db, governorate, first="أمير", family="العباسي",
            birth=date(2022, 1, 1), gender=Gender.MALE, serial=7,
        ),
    }
    db.commit()

    def link(child, parent, relation, child_relation):
        db.add(
            FamilyRelation(
                person_id=child.id,
                related_person_id=parent.id,
                relation_type=relation,
            )
        )
        db.add(
            FamilyRelation(
                person_id=parent.id,
                related_person_id=child.id,
                relation_type=child_relation,
            )
        )

    link(people["father"], people["grandfather"], RelationType.FATHER, RelationType.SON)
    link(people["father"], people["grandmother"], RelationType.MOTHER, RelationType.SON)
    link(people["son"], people["father"], RelationType.FATHER, RelationType.SON)
    link(people["son"], people["mother"], RelationType.MOTHER, RelationType.SON)
    link(
        people["daughter"], people["father"], RelationType.FATHER, RelationType.DAUGHTER
    )
    link(
        people["daughter"], people["mother"], RelationType.MOTHER, RelationType.DAUGHTER
    )
    link(people["grandson"], people["son"], RelationType.FATHER, RelationType.SON)

    # الأخوّة
    db.add(
        FamilyRelation(
            person_id=people["son"].id,
            related_person_id=people["daughter"].id,
            relation_type=RelationType.SISTER,
        )
    )
    db.add(
        FamilyRelation(
            person_id=people["daughter"].id,
            related_person_id=people["son"].id,
            relation_type=RelationType.BROTHER,
        )
    )

    # الزوجية
    db.add(
        FamilyRelation(
            person_id=people["father"].id,
            related_person_id=people["mother"].id,
            relation_type=RelationType.WIFE,
        )
    )
    db.add(
        FamilyRelation(
            person_id=people["mother"].id,
            related_person_id=people["father"].id,
            relation_type=RelationType.HUSBAND,
        )
    )

    db.commit()
    return people


# ---------------------------------------------------------------------------
# شجرة العائلة
# ---------------------------------------------------------------------------

def test_family_tree_three_generations(client, viewer_user, three_generations):
    """الشجرة تُرجع ثلاثة أجيال حول الشخص."""
    headers = auth_headers(client, "viewer")
    father = three_generations["father"]

    response = client.get(f"{BASE}/{father.id}/family-tree", headers=headers)
    assert response.status_code == 200, response.text
    tree = response.json()

    assert tree["person"]["full_name"].startswith("أحمد")
    assert tree["father"]["person"]["full_name"].startswith("عباس")
    assert tree["mother"]["person"]["full_name"].startswith("زهراء")

    children = {c["person"]["first_name"] for c in tree["children"]}
    assert children == {"كريم", "سارة"}

    grandchildren = {g["person"]["first_name"] for g in tree["grandchildren"]}
    assert grandchildren == {"أمير"}

    spouses = {s["person"]["first_name"] for s in tree["spouses"]}
    assert spouses == {"ليلى"}


def test_family_tree_siblings(client, viewer_user, three_generations):
    """الإخوة يظهرون في شجرة الابن."""
    headers = auth_headers(client, "viewer")
    son = three_generations["son"]

    tree = client.get(f"{BASE}/{son.id}/family-tree", headers=headers).json()

    siblings = {s["person"]["first_name"] for s in tree["siblings"]}
    assert siblings == {"سارة"}

    grandparents = {g["person"]["first_name"] for g in tree["grandparents"]}
    assert grandparents == {"عباس", "زهراء"}


def test_family_tree_of_isolated_person(client, db, viewer_user, governorate):
    """شخص بلا علاقات يُرجع شجرة فارغة لا خطأً."""
    lone = _person(
        db, governorate, first="وحيد", family="الغريب",
        birth=date(1990, 1, 1), gender=Gender.MALE, serial=99,
    )
    db.commit()

    headers = auth_headers(client, "viewer")
    tree = client.get(f"{BASE}/{lone.id}/family-tree", headers=headers).json()

    assert tree["father"] is None
    assert tree["mother"] is None
    assert tree["children"] == []
    assert tree["siblings"] == []


# ---------------------------------------------------------------------------
# إضافة العلاقات
# ---------------------------------------------------------------------------

def test_add_relation_creates_inverse(client, db, clerk_user, governorate):
    """إضافة علاقة تُنشئ نظيرتها العكسية تلقائياً."""
    parent = _person(
        db, governorate, first="سعد", family="التميمي",
        birth=date(1970, 1, 1), gender=Gender.MALE, serial=60,
    )
    kid = _person(
        db, governorate, first="نور", family="التميمي",
        birth=date(2000, 1, 1), gender=Gender.FEMALE, serial=61,
    )
    db.commit()

    headers = auth_headers(client, "clerk")
    response = client.post(
        f"{BASE}/{kid.id}/relations",
        json={
            "related_person_id": str(parent.id),
            "relation_type": RelationType.FATHER.value,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    from app.services import family

    daughters = family.get_relations(db, parent.id, types=(RelationType.DAUGHTER,))
    assert len(daughters) == 1
    assert daughters[0].related_person_id == kid.id


def test_relation_rejects_gender_mismatch(client, db, clerk_user, governorate):
    """تسجيل امرأة كـ«أب» يُرفض."""
    woman = _person(
        db, governorate, first="هدى", family="الراوي",
        birth=date(1970, 1, 1), gender=Gender.FEMALE, serial=62,
    )
    kid = _person(
        db, governorate, first="علي", family="الراوي",
        birth=date(2000, 1, 1), gender=Gender.MALE, serial=63,
    )
    db.commit()

    headers = auth_headers(client, "clerk")
    response = client.post(
        f"{BASE}/{kid.id}/relations",
        json={
            "related_person_id": str(woman.id),
            "relation_type": RelationType.FATHER.value,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "لا توافق جنس" in response.json()["detail"]["الرسالة"]


def test_relation_rejects_impossible_age_gap(client, db, clerk_user, governorate):
    """أب أصغر من ابنه يُرفض."""
    young = _person(
        db, governorate, first="حسن", family="الكعبي",
        birth=date(2010, 1, 1), gender=Gender.MALE, serial=64,
    )
    older = _person(
        db, governorate, first="جعفر", family="الكعبي",
        birth=date(2005, 1, 1), gender=Gender.MALE, serial=65,
    )
    db.commit()

    headers = auth_headers(client, "clerk")
    response = client.post(
        f"{BASE}/{older.id}/relations",
        json={
            "related_person_id": str(young.id),
            "relation_type": RelationType.FATHER.value,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "فارق العمر" in response.json()["detail"]["الرسالة"]


def test_relation_rejects_second_father(client, db, clerk_user, three_generations, governorate):
    """للشخص أب واحد لا أكثر."""
    another = _person(
        db, governorate, first="كاظم", family="الحلي",
        birth=date(1960, 1, 1), gender=Gender.MALE, serial=66,
    )
    db.commit()

    headers = auth_headers(client, "clerk")
    response = client.post(
        f"{BASE}/{three_generations['son'].id}/relations",
        json={
            "related_person_id": str(another.id),
            "relation_type": RelationType.FATHER.value,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "أب مسجَّل مسبقاً" in response.json()["detail"]["الرسالة"]


def test_relation_rejects_cycle(client, clerk_user, three_generations):
    """جعل الحفيد أباً لجدّه يُنشئ دوراً ويُرفض."""
    headers = auth_headers(client, "clerk")
    grandfather = three_generations["grandfather"]
    grandson = three_generations["grandson"]

    response = client.post(
        f"{BASE}/{grandfather.id}/relations",
        json={
            "related_person_id": str(grandson.id),
            "relation_type": RelationType.FATHER.value,
        },
        headers=headers,
    )

    assert response.status_code == 400
    detail = response.json()["detail"]["الرسالة"]
    assert "دوراً" in detail or "فارق العمر" in detail


def test_relation_rejects_self(client, clerk_user, three_generations):
    """ربط الشخص بنفسه يُرفض."""
    headers = auth_headers(client, "clerk")
    person = three_generations["son"]

    response = client.post(
        f"{BASE}/{person.id}/relations",
        json={
            "related_person_id": str(person.id),
            "relation_type": RelationType.BROTHER.value,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["الرمز"] == "self_relation"


def test_relation_rejects_duplicate(client, clerk_user, three_generations):
    """العلاقة المسجّلة مسبقاً لا تُكرَّر."""
    headers = auth_headers(client, "clerk")

    response = client.post(
        f"{BASE}/{three_generations['son'].id}/relations",
        json={
            "related_person_id": str(three_generations["father"].id),
            "relation_type": RelationType.FATHER.value,
        },
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["الرمز"] == "duplicate_relation"


# ---------------------------------------------------------------------------
# فحص التماسك
# ---------------------------------------------------------------------------

def test_consistency_clean_tree(client, viewer_user, three_generations):
    """شجرة سليمة لا تحمل تعارضات."""
    headers = auth_headers(client, "viewer")
    response = client.get(
        f"{BASE}/{three_generations['son'].id}/consistency", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["سليم"] is True
    assert body["عدد_التعارضات"] == 0


def test_consistency_detects_two_fathers(client, db, viewer_user, three_generations, governorate):
    """تعدّد الآباء يُكتشف — حتى لو أُدخل مباشرةً في قاعدة البيانات."""
    intruder = _person(
        db, governorate, first="مهدي", family="الساعدي",
        birth=date(1955, 1, 1), gender=Gender.MALE, serial=70,
    )
    db.commit()

    # إدخال مباشر يتجاوز فحص الخدمة — يحاكي بيانات مُرحَّلة من نظام قديم
    db.add(
        FamilyRelation(
            person_id=three_generations["son"].id,
            related_person_id=intruder.id,
            relation_type=RelationType.FATHER,
        )
    )
    db.commit()

    headers = auth_headers(client, "viewer")
    body = client.get(
        f"{BASE}/{three_generations['son'].id}/consistency", headers=headers
    ).json()

    assert body["سليم"] is False
    assert any(c["نوع_التعارض"] == "تعدّد الوالدين" for c in body["التعارضات"])


def test_consistency_detects_active_marriage_with_deceased(
    client, db, viewer_user, three_generations
):
    """زوجية نشطة مع متوفى تُكتشف كتعارض."""
    three_generations["mother"].life_status = LifeStatus.DECEASED
    db.commit()

    headers = auth_headers(client, "viewer")
    body = client.get(
        f"{BASE}/{three_generations['father'].id}/consistency", headers=headers
    ).json()

    assert body["سليم"] is False
    assert any(
        c["نوع_التعارض"] == "زوجية نشطة مع متوفى" for c in body["التعارضات"]
    )


def test_consistency_detects_gender_mismatch(client, db, viewer_user, three_generations):
    """جنس لا يوافق نوع العلاقة يُكتشف."""
    # تغيير جنس الأب بعد تسجيل العلاقة يحاكي خطأ إدخال قديماً
    three_generations["grandfather"].gender = Gender.FEMALE
    db.commit()

    headers = auth_headers(client, "viewer")
    body = client.get(
        f"{BASE}/{three_generations['father'].id}/consistency", headers=headers
    ).json()

    assert body["سليم"] is False
    assert any(
        c["نوع_التعارض"] == "جنس لا يوافق العلاقة" for c in body["التعارضات"]
    )


def test_list_relations(client, viewer_user, three_generations):
    """قائمة علاقات الشخص تُرجع الأنواع الصحيحة."""
    headers = auth_headers(client, "viewer")
    response = client.get(
        f"{BASE}/{three_generations['son'].id}/relations", headers=headers
    )

    assert response.status_code == 200
    types = {r["relation_type"] for r in response.json()}
    assert RelationType.FATHER.value in types
    assert RelationType.MOTHER.value in types
    assert RelationType.SISTER.value in types
