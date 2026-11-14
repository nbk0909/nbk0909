"""اختبارات البحث العربي المتقدم."""

from __future__ import annotations

from datetime import date

import pytest

from app.models import Gender, LifeStatus, Person
from app.utils.validators import generate_national_id
from tests.conftest import auth_headers

SEARCH = "/api/v1/persons/search"


@pytest.fixture
def population(db, governorate) -> list[Person]:
    """مجموعة أشخاص بأسماء متنوّعة للبحث فيها."""
    specs = [
        ("أحمد", "عباس", "حسين", "العباسي", "زهراء كاظم", date(1990, 5, 15), Gender.MALE),
        ("فاطمة", "عباس", "حسين", "العباسي", "زهراء كاظم", date(1993, 2, 20), Gender.FEMALE),
        ("مصطفى", "إبراهيم", "علي", "الجبوري", "آمنة طه", date(1985, 7, 3), Gender.MALE),
        ("عائشة", "مصطفى", "إبراهيم", "الجبوري", "ليلى صالح", date(2005, 11, 8), Gender.FEMALE),
        ("عبد الله", "يوسف", "كريم", "البصري", "مريم كريم", date(1999, 4, 9), Gender.MALE),
        ("خديجة", "يوسف", "كريم", "البصري", "مريم كريم", date(2002, 10, 27), Gender.FEMALE),
    ]

    people = []
    for index, (first, father, grand, family, mother, birth, gender) in enumerate(
        specs, start=1
    ):
        person = Person(
            national_id=generate_national_id(birth, 10, index),
            first_name=first,
            father_name=father,
            grandfather_name=grand,
            family_name=family,
            mother_full_name=mother,
            birth_date=birth,
            gender=gender,
            birth_governorate_id=governorate.id,
        )
        db.add(person)
        people.append(person)

    db.commit()
    return people


def _search(client, headers, **params) -> dict:
    response = client.get(SEARCH, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _names(body: dict) -> list[str]:
    return [item["full_name"] for item in body["items"]]


# ---------------------------------------------------------------------------
# المطابقة التامة
# ---------------------------------------------------------------------------

def test_search_by_national_id(client, viewer_user, population):
    """البحث بالرقم الوطني يعطي مطابقة واحدة."""
    headers = auth_headers(client, "viewer")
    body = _search(client, headers, national_id=population[0].national_id)

    assert body["total"] == 1
    assert body["items"][0]["national_id"] == population[0].national_id


def test_search_free_text_detects_national_id(client, viewer_user, population):
    """النص الحر المكوّن من 12 رقماً يُعامَل كرقم وطني."""
    headers = auth_headers(client, "viewer")
    body = _search(client, headers, q=population[2].national_id)

    assert body["total"] == 1
    assert body["items"][0]["full_name"].startswith("مصطفى")


# ---------------------------------------------------------------------------
# البحث بالاسم المُطبَّع
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query",
    [
        "أحمد عباس",      # كما هو
        "احمد عباس",      # بلا همزة
        "أَحْمَد عَبَّاس",   # بالتشكيل
        "احمد عبّاس",      # شدّة فقط
    ],
)
def test_search_ignores_diacritics_and_hamza(client, viewer_user, population, query):
    """صور الألف والتشكيل لا تمنع العثور على الاسم."""
    headers = auth_headers(client, "viewer")
    body = _search(client, headers, q=query)

    assert "أحمد عباس حسين العباسي" in _names(body), f"فشل مع: {query}"


@pytest.mark.parametrize("query", ["فاطمة", "فاطمه"])
def test_search_normalizes_taa_marbuta(client, viewer_user, population, query):
    """التاء المربوطة والهاء متساويتان في البحث."""
    headers = auth_headers(client, "viewer")
    assert any("فاطمة" in n for n in _names(_search(client, headers, q=query)))


@pytest.mark.parametrize("query", ["مصطفى", "مصطفي"])
def test_search_normalizes_alef_maqsura(client, viewer_user, population, query):
    """الألف المقصورة والياء متساويتان."""
    headers = auth_headers(client, "viewer")
    assert any("مصطفى" in n for n in _names(_search(client, headers, q=query)))


def test_search_by_family_name(client, viewer_user, population):
    """البحث باللقب يُرجع كل أفراد العائلة."""
    headers = auth_headers(client, "viewer")
    body = _search(client, headers, family_name="العباسي")

    assert body["total"] == 2
    assert all("العباسي" in n for n in _names(body))


def test_search_by_mother_name(client, viewer_user, population):
    """البحث باسم الأم يُرجع الإخوة."""
    headers = auth_headers(client, "viewer")
    body = _search(client, headers, mother_name="مريم كريم")

    assert body["total"] == 2
    assert set(_names(body)) == {
        "عبد الله يوسف كريم البصري",
        "خديجة يوسف كريم البصري",
    }


def test_search_combined_criteria(client, viewer_user, population):
    """الجمع بين معايير متعددة يضيّق النتيجة."""
    headers = auth_headers(client, "viewer")
    body = _search(client, headers, family_name="العباسي", gender=Gender.FEMALE.value)

    assert body["total"] == 1
    assert body["items"][0]["full_name"].startswith("فاطمة")


def test_search_by_birth_date_range(client, viewer_user, population):
    """البحث بمدى تاريخ ميلاد."""
    headers = auth_headers(client, "viewer")
    body = _search(
        client, headers, birth_date_from="2000-01-01", birth_date_to="2010-12-31"
    )

    assert body["total"] == 2
    assert set(_names(body)) == {
        "عائشة مصطفى إبراهيم الجبوري",
        "خديجة يوسف كريم البصري",
    }


def test_search_by_life_status(client, db, viewer_user, population):
    """التصفية بحالة الحياة."""
    population[0].life_status = LifeStatus.DECEASED
    db.commit()

    headers = auth_headers(client, "viewer")
    body = _search(client, headers, q="العباسي", life_status=LifeStatus.ALIVE.value)

    assert body["total"] == 1
    assert body["items"][0]["full_name"].startswith("فاطمة")


# ---------------------------------------------------------------------------
# البحث التقريبي
# ---------------------------------------------------------------------------

def test_fuzzy_search_finds_misspelled_name(client, viewer_user, population):
    """خطأ إملائي في اللقب لا يمنع العثور على الشخص."""
    headers = auth_headers(client, "viewer")
    # «العبسي» بدل «العباسي» — حرف ناقص
    body = _search(client, headers, q="احمد عباس حسين العبسي")

    assert body["total"] > 0
    assert any("العباسي" in n for n in _names(body))
    assert body["items"][0]["similarity"] is not None


def test_fuzzy_can_be_disabled(client, viewer_user, population):
    """إيقاف البحث التقريبي يمنع النتائج التقريبية."""
    headers = auth_headers(client, "viewer")
    body = _search(client, headers, q="احمد عباس حسين العبسي", fuzzy=False)

    assert body["total"] == 0


def test_exact_match_has_no_similarity_score(client, viewer_user, population):
    """المطابقة التامة لا تحمل درجة تشابه — التشابه للبحث التقريبي وحده."""
    headers = auth_headers(client, "viewer")
    body = _search(client, headers, q="أحمد عباس")

    assert body["total"] >= 1
    assert body["items"][0]["similarity"] is None


# ---------------------------------------------------------------------------
# الترقيم والحماية
# ---------------------------------------------------------------------------

def test_search_pagination(client, viewer_user, population):
    """الترقيم يقسّم النتائج ويحسب الصفحات."""
    headers = auth_headers(client, "viewer")

    first = _search(client, headers, q="ال", page=1, page_size=2)
    assert len(first["items"]) <= 2
    assert first["page"] == 1
    assert first["total_pages"] == -(-first["total"] // 2)

    if first["total"] > 2:
        assert first["has_next"] is True
        second = _search(client, headers, q="ال", page=2, page_size=2)
        assert _names(first) != _names(second)


def test_empty_search_rejected(client, viewer_user, population):
    """البحث بلا معايير يُرفض بدل إعادة السجل كاملاً."""
    headers = auth_headers(client, "viewer")
    response = client.get(SEARCH, headers=headers)

    assert response.status_code == 400
    assert "معياراً" in response.json()["detail"]["الرسالة"]


def test_search_excludes_deleted(client, db, viewer_user, population):
    """السجلات المحذوفة منطقياً لا تظهر في البحث."""
    from app.utils.dates import utcnow

    headers = auth_headers(client, "viewer")
    assert _search(client, headers, family_name="العباسي")["total"] == 2

    population[0].deleted_at = utcnow()
    db.commit()

    assert _search(client, headers, family_name="العباسي")["total"] == 1


def test_search_requires_permission(client, db, roles):
    """البحث يتطلّب صلاحية قراءة الأشخاص."""
    from app.core.security import hash_password
    from app.models import Role, User

    empty_role = Role(code="nobody", name_ar="بلا صلاحيات")
    db.add(empty_role)
    user = User(
        username="nobody",
        password_hash=hash_password("TestPass@2026"),
        full_name_ar="بلا صلاحيات",
        must_change_password=False,
    )
    user.roles = [empty_role]
    db.add(user)
    db.commit()

    headers = auth_headers(client, "nobody")
    assert client.get(SEARCH, params={"q": "أحمد"}, headers=headers).status_code == 403


def test_search_invalid_date_rejected(client, viewer_user, population):
    """تاريخ بصيغة خاطئة يُرفض برسالة واضحة."""
    headers = auth_headers(client, "viewer")
    response = client.get(
        SEARCH, params={"q": "أحمد", "birth_date_from": "15-05-1990"}, headers=headers
    )

    assert response.status_code == 422
    assert "تاريخ غير صالح" in response.json()["detail"]["الرسالة"]


# ---------------------------------------------------------------------------
# الاقتراحات
# ---------------------------------------------------------------------------

def test_suggest_names(client, viewer_user, population):
    """الإكمال التلقائي يقترح أسماء تبدأ بالبادئة."""
    headers = auth_headers(client, "viewer")
    response = client.get(
        "/api/v1/persons/suggest", params={"prefix": "اح"}, headers=headers
    )

    assert response.status_code == 200
    assert "أحمد" in response.json()


def test_suggest_requires_min_length(client, viewer_user, population):
    """بادئة من حرف واحد تُرفض — لا فائدة من اقتراح على كل السجل."""
    headers = auth_headers(client, "viewer")
    response = client.get(
        "/api/v1/persons/suggest", params={"prefix": "ا"}, headers=headers
    )
    assert response.status_code == 422
