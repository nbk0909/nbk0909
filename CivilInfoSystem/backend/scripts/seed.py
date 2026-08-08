"""تعبئة قاعدة البيانات ببيانات تجريبية مترابطة.

التشغيل من مجلد backend:
    python -m scripts.seed              # تعبئة
    python -m scripts.seed --reset      # حذف البيانات السابقة ثم التعبئة

البيانات مبنية يدوياً لا عشوائياً، لتكون شجرة العائلة منطقية: ثلاثة أجيال
مترابطة بأزواج وأبناء وأحفاد، مع واقعات ميلاد ووفاة وزواج وطلاق متسقة
زمنياً (لا مولود قبل زواج أبويه، ولا وفاة قبل ميلاد).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    Address,
    AuditLog,
    BirthRecord,
    DeathRecord,
    District,
    DivorceRecord,
    Document,
    DocumentStatus,
    DocumentType,
    FamilyCard,
    FamilyCardMember,
    FamilyRelation,
    Gender,
    Governorate,
    LifeStatus,
    MaritalStatus,
    MarriageContract,
    Permission,
    Person,
    RelationType,
    RequestStatus,
    RequestType,
    Role,
    ServiceRequest,
    Subdistrict,
    User,
)
from app.utils.validators import generate_national_id

# ---------------------------------------------------------------------------
# التقسيمات الإدارية
# ---------------------------------------------------------------------------

GOVERNORATES = [
    ("10", "بغداد", "Baghdad"),
    ("20", "البصرة", "Basra"),
    ("30", "نينوى", "Nineveh"),
    ("40", "أربيل", "Erbil"),
    ("50", "النجف", "Najaf"),
]

DISTRICTS = {
    "10": [("1001", "الكرخ"), ("1002", "الرصافة"), ("1003", "الكاظمية"), ("1004", "المحمودية")],
    "20": [("2001", "البصرة المركز"), ("2002", "الزبير"), ("2003", "أبو الخصيب")],
    "30": [("3001", "الموصل"), ("3002", "تلعفر")],
    "40": [("4001", "أربيل المركز"), ("4002", "شقلاوة")],
    "50": [("5001", "النجف المركز"), ("5002", "الكوفة")],
}

SUBDISTRICTS = {
    "1001": [("100101", "المنصور"), ("100102", "اليرموك")],
    "1002": [("100201", "الأعظمية"), ("100202", "الكرادة")],
    "2001": [("200101", "العشار"), ("200102", "المعقل")],
    "3001": [("300101", "الجانب الأيسر")],
    "5001": [("500101", "حي السلام")],
}

# ---------------------------------------------------------------------------
# الأدوار والصلاحيات
# ---------------------------------------------------------------------------

RESOURCES = [
    ("persons", "الأشخاص"),
    ("births", "واقعات الميلاد"),
    ("deaths", "واقعات الوفاة"),
    ("marriages", "عقود الزواج"),
    ("divorces", "واقعات الطلاق"),
    ("documents", "الوثائق"),
    ("family_cards", "بطاقات العائلة"),
    ("requests", "المعاملات"),
    ("reports", "التقارير"),
    ("users", "المستخدمون"),
    ("audit", "سجل التدقيق"),
]

ACTIONS = [
    ("create", "إنشاء"),
    ("read", "قراءة"),
    ("update", "تعديل"),
    ("delete", "حذف"),
    ("approve", "اعتماد"),
]

ROLES = [
    ("admin", "مدير النظام", "صلاحية كاملة على كل وحدات النظام"),
    ("registrar", "مدير سجل", "إدارة السجلات المدنية واعتماد المعاملات"),
    ("clerk", "موظف إدخال", "إدخال وتعديل البيانات دون اعتماد"),
    ("auditor", "مدقّق", "الاطّلاع على السجلات وسجل التدقيق دون تعديل"),
    ("viewer", "مستعلم", "قراءة فقط"),
]

ROLE_MATRIX: dict[str, set[str]] = {
    "admin": {"*"},
    "registrar": {
        f"{r}.{a}"
        for r, _ in RESOURCES
        if r not in ("users", "audit")
        for a in ("create", "read", "update", "approve")
    },
    "clerk": {
        f"{r}.{a}"
        for r, _ in RESOURCES
        if r not in ("users", "audit", "reports")
        for a in ("create", "read", "update")
    },
    "auditor": {f"{r}.read" for r, _ in RESOURCES},
    "viewer": {
        f"{r}.read" for r, _ in RESOURCES if r not in ("users", "audit")
    },
}


# ---------------------------------------------------------------------------
# وصف الأشخاص
# ---------------------------------------------------------------------------

@dataclass
class PersonSpec:
    """وصف مختصر لشخص في البيانات التجريبية."""

    key: str
    first: str
    father: str
    grandfather: str
    family: str
    mother_name: str
    birth: date
    gender: Gender
    gov_code: str
    religion: str = "مسلم"
    blood: str | None = None
    occupation: str | None = None
    education: str | None = None
    death: date | None = None
    death_cause: str | None = None


# --- الجيل الأول: الأجداد (مواليد 1935-1955) --------------------------------

G1 = [
    PersonSpec("g1_abbas", "عباس", "حسين", "علي", "العباسي", "خديجة محمد",
               date(1938, 3, 12), Gender.MALE, "10", occupation="مزارع",
               education="ابتدائية", death=date(2015, 8, 3),
               death_cause="أمراض القلب"),
    PersonSpec("g1_zahra", "زهراء", "كاظم", "جواد", "الموسوي", "سكينة حسن",
               date(1943, 7, 25), Gender.FEMALE, "10", occupation="ربة منزل",
               education="ابتدائية"),

    PersonSpec("g1_saleh", "صالح", "إبراهيم", "محمود", "الجبوري", "نجاة عبد",
               date(1941, 11, 2), Gender.MALE, "30", occupation="معلم",
               education="دار المعلمين", death=date(2019, 2, 14),
               death_cause="سكتة دماغية"),
    PersonSpec("g1_amina", "آمنة", "طه", "ياسين", "النعيمي", "فوزية سالم",
               date(1946, 4, 18), Gender.FEMALE, "30", occupation="ربة منزل",
               education="ابتدائية"),

    PersonSpec("g1_karim", "كريم", "عبد الله", "جاسم", "البصري", "بدرية علي",
               date(1945, 9, 30), Gender.MALE, "20", occupation="بحّار",
               education="متوسطة"),
    PersonSpec("g1_nadia", "نادية", "شاكر", "محسن", "الحلفي", "رحمة جبار",
               date(1950, 1, 8), Gender.FEMALE, "20", occupation="خيّاطة",
               education="ابتدائية"),

    PersonSpec("g1_hasan", "حسن", "مهدي", "صادق", "النجفي", "أمينة رضا",
               date(1948, 6, 14), Gender.MALE, "50", occupation="تاجر",
               education="إعدادية"),
    PersonSpec("g1_rabab", "رباب", "عبد الحسين", "علوان", "الكوفي", "ليلى ناصر",
               date(1953, 12, 3), Gender.FEMALE, "50", occupation="ربة منزل",
               education="متوسطة"),

    PersonSpec("g1_ghazi", "غازي", "رشيد", "سلمان", "الطائي", "حميدة قادر",
               date(1944, 5, 19), Gender.MALE, "40", occupation="موظف حكومي",
               education="إعدادية"),
    PersonSpec("g1_suad", "سعاد", "فاضل", "حمود", "البرزنجي", "شيرين عمر",
               date(1949, 10, 7), Gender.FEMALE, "40", occupation="ربة منزل",
               education="متوسطة"),

    PersonSpec("g1_jabbar", "جبار", "عودة", "مطشر", "السامرائي", "سميرة خضير",
               date(1950, 8, 11), Gender.MALE, "10", occupation="نجّار",
               education="ابتدائية"),
    PersonSpec("g1_wafaa", "وفاء", "نعيم", "داود", "الراوي", "هيفاء عبد",
               date(1955, 3, 26), Gender.FEMALE, "10", occupation="ربة منزل",
               education="ابتدائية"),
]

# --- الجيل الثاني: الآباء (مواليد 1965-1985) --------------------------------

G2 = [
    # أبناء عباس وزهراء
    PersonSpec("g2_ahmad", "أحمد", "عباس", "حسين", "العباسي", "زهراء كاظم",
               date(1968, 2, 20), Gender.MALE, "10", blood="O+",
               occupation="مهندس مدني", education="بكالوريوس هندسة"),
    PersonSpec("g2_mustafa", "مصطفى", "عباس", "حسين", "العباسي", "زهراء كاظم",
               date(1971, 5, 9), Gender.MALE, "10", blood="A+",
               occupation="طبيب", education="بكالوريوس طب"),
    PersonSpec("g2_fatima", "فاطمة", "عباس", "حسين", "العباسي", "زهراء كاظم",
               date(1974, 10, 17), Gender.FEMALE, "10", blood="B+",
               occupation="مدرّسة", education="بكالوريوس تربية"),

    # أبناء صالح وآمنة
    PersonSpec("g2_layla", "ليلى", "صالح", "إبراهيم", "الجبوري", "آمنة طه",
               date(1970, 8, 4), Gender.FEMALE, "30", blood="AB+",
               occupation="صيدلانية", education="بكالوريوس صيدلة"),
    PersonSpec("g2_omar", "عمر", "صالح", "إبراهيم", "الجبوري", "آمنة طه",
               date(1973, 3, 22), Gender.MALE, "30", blood="O-",
               occupation="محاسب", education="بكالوريوس إدارة"),
    PersonSpec("g2_huda", "هدى", "صالح", "إبراهيم", "الجبوري", "آمنة طه",
               date(1977, 12, 11), Gender.FEMALE, "30", blood="A-",
               occupation="ممرّضة", education="دبلوم تمريض"),

    # أبناء كريم ونادية
    PersonSpec("g2_yusuf", "يوسف", "كريم", "عبد الله", "البصري", "نادية شاكر",
               date(1972, 7, 1), Gender.MALE, "20", blood="B-",
               occupation="ربّان سفينة", education="معهد بحري"),
    PersonSpec("g2_maryam", "مريم", "كريم", "عبد الله", "البصري", "نادية شاكر",
               date(1976, 4, 28), Gender.FEMALE, "20", blood="O+",
               occupation="مهندسة حاسوب", education="بكالوريوس حاسوب"),

    # أبناء حسن ورباب
    PersonSpec("g2_ali", "علي", "حسن", "مهدي", "النجفي", "رباب عبد الحسين",
               date(1975, 9, 15), Gender.MALE, "50", blood="A+",
               occupation="أستاذ جامعي", education="دكتوراه"),
    PersonSpec("g2_zainab", "زينب", "حسن", "مهدي", "النجفي", "رباب عبد الحسين",
               date(1979, 6, 7), Gender.FEMALE, "50", blood="AB-",
               occupation="محامية", education="بكالوريوس قانون"),

    # أبناء غازي وسعاد
    PersonSpec("g2_rashid", "رشيد", "غازي", "رشيد", "الطائي", "سعاد فاضل",
               date(1974, 1, 30), Gender.MALE, "40", blood="B+",
               occupation="مهندس زراعي", education="بكالوريوس زراعة"),
    PersonSpec("g2_nasreen", "نسرين", "غازي", "رشيد", "الطائي", "سعاد فاضل",
               date(1978, 9, 16), Gender.FEMALE, "40", blood="O+",
               occupation="طبيبة أسنان", education="بكالوريوس طب أسنان"),
    PersonSpec("g2_sami", "سامي", "غازي", "رشيد", "الطائي", "سعاد فاضل",
               date(1981, 6, 23), Gender.MALE, "40", blood="A+",
               occupation="صحفي", education="بكالوريوس إعلام"),

    # أبناء جبار ووفاء
    PersonSpec("g2_haider", "حيدر", "جبار", "عودة", "السامرائي", "وفاء نعيم",
               date(1976, 12, 8), Gender.MALE, "10", blood="AB+",
               occupation="ضابط شرطة", education="كلية الشرطة"),
    PersonSpec("g2_dalal", "دلال", "جبار", "عودة", "السامرائي", "وفاء نعيم",
               date(1980, 4, 2), Gender.FEMALE, "10", blood="O-",
               occupation="معلّمة", education="دبلوم تربية"),
    PersonSpec("g2_kamal", "كمال", "جبار", "عودة", "السامرائي", "وفاء نعيم",
               date(1983, 11, 14), Gender.MALE, "10", blood="B-",
               occupation="سائق", education="متوسطة"),
]

# --- الجيل الثالث: الأحفاد (مواليد 1995-2020) -------------------------------

G3 = [
    # أبناء أحمد وليلى
    PersonSpec("g3_kareem", "كريم", "أحمد", "عباس", "العباسي", "ليلى صالح",
               date(1998, 1, 12), Gender.MALE, "10", blood="O+",
               occupation="طالب جامعي", education="بكالوريوس جارٍ"),
    PersonSpec("g3_sara", "سارة", "أحمد", "عباس", "العباسي", "ليلى صالح",
               date(2001, 5, 30), Gender.FEMALE, "10", blood="AB+",
               occupation="طالبة", education="بكالوريوس جارٍ"),
    PersonSpec("g3_hussein", "حسين", "أحمد", "عباس", "العباسي", "ليلى صالح",
               date(2005, 11, 8), Gender.MALE, "10", blood="O+",
               education="إعدادية"),
    PersonSpec("g3_noor", "نور", "أحمد", "عباس", "العباسي", "ليلى صالح",
               date(2010, 3, 19), Gender.FEMALE, "10", education="ابتدائية"),

    # أبناء مصطفى ومريم
    PersonSpec("g3_jaafar", "جعفر", "مصطفى", "عباس", "العباسي", "مريم كريم",
               date(2003, 8, 25), Gender.MALE, "10", blood="A+",
               occupation="طالب", education="إعدادية"),
    PersonSpec("g3_ruqaya", "رقية", "مصطفى", "عباس", "العباسي", "مريم كريم",
               date(2007, 2, 14), Gender.FEMALE, "10", blood="O+",
               education="متوسطة"),
    PersonSpec("g3_taha", "طه", "مصطفى", "عباس", "العباسي", "مريم كريم",
               date(2012, 9, 3), Gender.MALE, "10", education="ابتدائية"),

    # أبناء عمر وهدى
    PersonSpec("g3_ibrahim", "إبراهيم", "عمر", "صالح", "الجبوري", "هدى صالح",
               date(2000, 6, 21), Gender.MALE, "30", blood="O-",
               occupation="فنّي حاسوب", education="دبلوم"),
    PersonSpec("g3_aisha", "عائشة", "عمر", "صالح", "الجبوري", "هدى صالح",
               date(2004, 12, 5), Gender.FEMALE, "30", blood="A-",
               education="إعدادية"),
    PersonSpec("g3_yaqoub", "يعقوب", "عمر", "صالح", "الجبوري", "هدى صالح",
               date(2009, 7, 17), Gender.MALE, "30", education="ابتدائية"),

    # أبناء يوسف وفاطمة
    PersonSpec("g3_abdullah", "عبد الله", "يوسف", "كريم", "البصري", "فاطمة عباس",
               date(1999, 4, 9), Gender.MALE, "20", blood="B+",
               occupation="بحّار", education="معهد بحري"),
    PersonSpec("g3_khadija", "خديجة", "يوسف", "كريم", "البصري", "فاطمة عباس",
               date(2002, 10, 27), Gender.FEMALE, "20", blood="O+",
               occupation="طالبة", education="بكالوريوس جارٍ"),
    PersonSpec("g3_salma", "سلمى", "يوسف", "كريم", "البصري", "فاطمة عباس",
               date(2008, 1, 15), Gender.FEMALE, "20", education="متوسطة"),

    # أبناء علي وزينب — (الزوجان مطلّقان لاحقاً)
    PersonSpec("g3_murtadha", "مرتضى", "علي", "حسن", "النجفي", "زينب حسن",
               date(2006, 3, 2), Gender.MALE, "50", blood="A+",
               education="إعدادية"),
    PersonSpec("g3_batool", "بتول", "علي", "حسن", "النجفي", "زينب حسن",
               date(2011, 8, 20), Gender.FEMALE, "50", education="ابتدائية"),

    # الجيل الرابع الناشئ — أبناء كريم بن أحمد
    PersonSpec("g4_amir", "أمير", "كريم", "أحمد", "العباسي", "شهد ماجد",
               date(2022, 5, 11), Gender.MALE, "10"),
    PersonSpec("g4_lina", "لينا", "كريم", "أحمد", "العباسي", "شهد ماجد",
               date(2024, 9, 28), Gender.FEMALE, "10"),

    # زوجات وافدة من خارج العائلات الأربع
    PersonSpec("sp_shahad", "شهد", "ماجد", "عبد الرزاق", "التميمي", "إيمان فاضل",
               date(2000, 2, 4), Gender.FEMALE, "10", blood="B+",
               occupation="مصمّمة", education="بكالوريوس فنون"),
    PersonSpec("sp_hind", "هند", "وليد", "سعدون", "الدليمي", "سعاد حميد",
               date(1980, 11, 22), Gender.FEMALE, "10", blood="O+",
               occupation="مدرّسة", education="بكالوريوس تربية"),
    PersonSpec("sp_bilal", "بلال", "غانم", "خليل", "العبيدي", "نوال ثابت",
               date(1996, 7, 6), Gender.MALE, "30", blood="A+",
               occupation="مهندس كهرباء", education="بكالوريوس هندسة"),

    # أبناء رشيد ودلال (زواج بين عائلتَي الطائي والسامرائي)
    PersonSpec("g3_ghazi2", "غازي", "رشيد", "غازي", "الطائي", "دلال جبار",
               date(2006, 7, 9), Gender.MALE, "40", blood="B+",
               education="إعدادية"),
    PersonSpec("g3_dima", "ديمة", "رشيد", "غازي", "الطائي", "دلال جبار",
               date(2009, 11, 24), Gender.FEMALE, "40", blood="O-",
               education="متوسطة"),
    PersonSpec("g3_mays", "ميس", "رشيد", "غازي", "الطائي", "دلال جبار",
               date(2014, 2, 6), Gender.FEMALE, "40", education="ابتدائية"),

    # أبناء حيدر ونسرين
    PersonSpec("g3_jabbar2", "جبار", "حيدر", "جبار", "السامرائي", "نسرين غازي",
               date(2004, 5, 17), Gender.MALE, "10", blood="AB+",
               occupation="طالب جامعي", education="بكالوريوس جارٍ"),
    PersonSpec("g3_rand", "رند", "حيدر", "جبار", "السامرائي", "نسرين غازي",
               date(2008, 10, 1), Gender.FEMALE, "10", blood="O+",
               education="متوسطة"),
    PersonSpec("g3_mohammed", "محمد", "حيدر", "جبار", "السامرائي", "نسرين غازي",
               date(2013, 3, 29), Gender.MALE, "10", education="ابتدائية"),
]

ALL_SPECS = G1 + G2 + G3

# --- الزيجات: (الزوج، الزوجة، تاريخ العقد، المهر المعجّل، المؤجّل) ----------

MARRIAGES = [
    ("g1_abbas", "g1_zahra", date(1962, 4, 10), 500, 1000),
    ("g1_saleh", "g1_amina", date(1965, 9, 3), 700, 1500),
    ("g1_karim", "g1_nadia", date(1969, 6, 21), 600, 1200),
    ("g1_hasan", "g1_rabab", date(1972, 2, 28), 800, 2000),
    ("g1_ghazi", "g1_suad", date(1971, 10, 5), 550, 1100),
    ("g1_jabbar", "g1_wafaa", date(1974, 7, 19), 650, 1300),

    ("g2_ahmad", "g2_layla", date(1996, 7, 15), 3_000_000, 10_000_000),
    ("g2_mustafa", "g2_maryam", date(2001, 3, 8), 4_000_000, 12_000_000),
    ("g2_omar", "g2_huda", date(1998, 11, 20), 2_500_000, 8_000_000),
    ("g2_yusuf", "g2_fatima", date(1997, 5, 2), 3_500_000, 9_000_000),
    ("g2_ali", "g2_zainab", date(2004, 8, 12), 5_000_000, 15_000_000),
    # مصاهرة بين عائلتَي الطائي والسامرائي
    ("g2_rashid", "g2_dalal", date(2005, 2, 11), 4_500_000, 13_000_000),
    ("g2_haider", "g2_nasreen", date(2003, 9, 26), 3_800_000, 11_000_000),

    ("g3_kareem", "sp_shahad", date(2021, 6, 4), 7_000_000, 20_000_000),
    ("sp_bilal", "g3_aisha", date(2023, 4, 12), 8_000_000, 25_000_000),
]

# طلاق واحد: علي وزينب
DIVORCES = [
    ("g2_ali", "g2_zainab", date(2018, 4, 17), "بائن",
     "خلافات مستمرة تعذّر معها استمرار الحياة الزوجية",
     "حضانة الولدين للأم مع حق المشاهدة الأسبوعي للأب"),
]

# --- الأبوّة: (الأب، الأم، [الأبناء]) ---------------------------------------

PARENTAGE = [
    ("g1_abbas", "g1_zahra", ["g2_ahmad", "g2_mustafa", "g2_fatima"]),
    ("g1_saleh", "g1_amina", ["g2_layla", "g2_omar", "g2_huda"]),
    ("g1_karim", "g1_nadia", ["g2_yusuf", "g2_maryam"]),
    ("g1_hasan", "g1_rabab", ["g2_ali", "g2_zainab"]),
    ("g1_ghazi", "g1_suad", ["g2_rashid", "g2_nasreen", "g2_sami"]),
    ("g1_jabbar", "g1_wafaa", ["g2_haider", "g2_dalal", "g2_kamal"]),

    ("g2_ahmad", "g2_layla", ["g3_kareem", "g3_sara", "g3_hussein", "g3_noor"]),
    ("g2_mustafa", "g2_maryam", ["g3_jaafar", "g3_ruqaya", "g3_taha"]),
    ("g2_omar", "g2_huda", ["g3_ibrahim", "g3_aisha", "g3_yaqoub"]),
    ("g2_yusuf", "g2_fatima", ["g3_abdullah", "g3_khadija", "g3_salma"]),
    ("g2_ali", "g2_zainab", ["g3_murtadha", "g3_batool"]),
    ("g2_rashid", "g2_dalal", ["g3_ghazi2", "g3_dima", "g3_mays"]),
    ("g2_haider", "g2_nasreen", ["g3_jabbar2", "g3_rand", "g3_mohammed"]),

    ("g3_kareem", "sp_shahad", ["g4_amir", "g4_lina"]),
]

HOSPITALS = {
    "10": "مستشفى بغداد التعليمي",
    "20": "مستشفى البصرة العام",
    "30": "مستشفى الموصل العام",
    "40": "مستشفى أربيل التعليمي",
    "50": "مستشفى الحكيم العام",
}

QUARTERS = {
    "10": [("المنصور", "609", "12"), ("اليرموك", "215", "7"), ("الأعظمية", "318", "24")],
    "20": [("العشار", "104", "9"), ("المعقل", "222", "3")],
    "30": [("الجانب الأيسر", "412", "18"), ("الدواسة", "115", "5")],
    "40": [("عنكاوا", "301", "11")],
    "50": [("حي السلام", "502", "20"), ("حي الغري", "511", "6")],
}


# ---------------------------------------------------------------------------
# منطق التعبئة
# ---------------------------------------------------------------------------

class Seeder:
    """يبني البيانات التجريبية داخل معاملة واحدة."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.govs: dict[str, Governorate] = {}
        self.persons: dict[str, Person] = {}
        self.serial = 0

    # -- أدوات مساعدة ---------------------------------------------------

    def _next_national_id(self, birth: date, gov_code: str) -> str:
        """يولّد رقماً وطنياً صحيح خانة التدقيق وفريداً."""
        self.serial += 1
        return generate_national_id(birth, int(gov_code) // 10, self.serial)

    # -- المراحل --------------------------------------------------------

    def seed_locations(self) -> None:
        for code, ar, en in GOVERNORATES:
            gov = Governorate(code=code, name_ar=ar, name_en=en)
            self.db.add(gov)
            self.govs[code] = gov
        self.db.flush()

        districts: dict[str, District] = {}
        for gov_code, items in DISTRICTS.items():
            for code, name in items:
                d = District(
                    governorate_id=self.govs[gov_code].id, code=code, name_ar=name
                )
                self.db.add(d)
                districts[code] = d
        self.db.flush()

        for dist_code, items in SUBDISTRICTS.items():
            for code, name in items:
                self.db.add(
                    Subdistrict(
                        district_id=districts[dist_code].id, code=code, name_ar=name
                    )
                )
        self.db.flush()
        print(f"  ✓ {len(GOVERNORATES)} محافظة، "
              f"{sum(len(v) for v in DISTRICTS.values())} قضاء، "
              f"{sum(len(v) for v in SUBDISTRICTS.values())} ناحية")

    def seed_rbac(self) -> None:
        perms: dict[str, Permission] = {}
        for res, res_ar in RESOURCES:
            for act, act_ar in ACTIONS:
                code = f"{res}.{act}"
                p = Permission(
                    code=code, resource=res, action=act, name_ar=f"{act_ar} {res_ar}"
                )
                self.db.add(p)
                perms[code] = p
        self.db.flush()

        for code, name_ar, desc in ROLES:
            role = Role(code=code, name_ar=name_ar, description_ar=desc, is_system=True)
            wanted = ROLE_MATRIX[code]
            role.permissions = (
                list(perms.values())
                if "*" in wanted
                else [perms[c] for c in sorted(wanted) if c in perms]
            )
            self.db.add(role)
        self.db.flush()
        print(f"  ✓ {len(perms)} صلاحية موزّعة على {len(ROLES)} أدوار")

    def seed_admin(self) -> None:
        """ينشئ حساب المدير الافتراضي.

        كلمة المرور الافتراضية معروفة عمداً، والحساب مُعلَّم بـ
        must_change_password ليُجبَر المستخدم على تغييرها عند أول دخول.
        """
        from app.core.security import hash_password

        admin_role = self.db.scalar(select(Role).where(Role.code == "admin"))
        admin = User(
            username="admin",
            email="admin@civil.gov",
            password_hash=hash_password("Admin@2026!"),
            full_name_ar="مدير النظام",
            governorate_id=self.govs["10"].id,
            is_active=True,
            must_change_password=True,
        )
        admin.roles = [admin_role]
        self.db.add(admin)

        registrar_role = self.db.scalar(select(Role).where(Role.code == "registrar"))
        registrar = User(
            username="registrar",
            email="registrar@civil.gov",
            password_hash=hash_password("Registrar@2026!"),
            full_name_ar="سجّاد عبد الأمير",
            governorate_id=self.govs["10"].id,
            must_change_password=True,
        )
        registrar.roles = [registrar_role]
        self.db.add(registrar)
        self.db.flush()
        print("  ✓ حسابان: admin / registrar (يجب تغيير كلمتَي المرور عند أول دخول)")

    def seed_persons(self) -> None:
        for spec in ALL_SPECS:
            person = Person(
                national_id=self._next_national_id(spec.birth, spec.gov_code),
                first_name=spec.first,
                father_name=spec.father,
                grandfather_name=spec.grandfather,
                family_name=spec.family,
                mother_full_name=spec.mother_name,
                birth_date=spec.birth,
                birth_governorate_id=self.govs[spec.gov_code].id,
                birth_place_detail=HOSPITALS[spec.gov_code],
                gender=spec.gender,
                nationality="عراقي",
                religion=spec.religion,
                blood_type=spec.blood,
                occupation=spec.occupation,
                education_level=spec.education,
                life_status=LifeStatus.ALIVE,
            )
            self.db.add(person)
            self.persons[spec.key] = person
        self.db.flush()
        print(f"  ✓ {len(ALL_SPECS)} شخصاً")

    def seed_addresses(self) -> None:
        count = 0
        for spec in ALL_SPECS:
            options = QUARTERS[spec.gov_code]
            quarter, street, house = options[count % len(options)]
            self.db.add(
                Address(
                    person_id=self.persons[spec.key].id,
                    governorate_id=self.govs[spec.gov_code].id,
                    quarter=quarter,
                    street=street,
                    house_number=house,
                    valid_from=max(spec.birth, date(1990, 1, 1)),
                    is_current=True,
                )
            )
            count += 1
        self.db.flush()
        print(f"  ✓ {count} عنوان سكن")

    def seed_relations(self) -> None:
        """ينشئ علاقات الأبوّة والزوجية والإخوة باتجاهين."""
        created = 0

        def add(a: str, b: str, rel: RelationType, start: date | None = None) -> None:
            nonlocal created
            self.db.add(
                FamilyRelation(
                    person_id=self.persons[a].id,
                    related_person_id=self.persons[b].id,
                    relation_type=rel,
                    start_date=start,
                    is_active=True,
                )
            )
            created += 1

        for father, mother, children in PARENTAGE:
            for child in children:
                child_spec = next(s for s in ALL_SPECS if s.key == child)
                child_rel = (
                    RelationType.SON
                    if child_spec.gender == Gender.MALE
                    else RelationType.DAUGHTER
                )
                # الاتجاهان: الأب/الأم بالنسبة للابن، والابن بالنسبة لهما
                add(child, father, RelationType.FATHER, child_spec.birth)
                add(child, mother, RelationType.MOTHER, child_spec.birth)
                add(father, child, child_rel, child_spec.birth)
                add(mother, child, child_rel, child_spec.birth)

            # الإخوة فيما بينهم
            for i, first in enumerate(children):
                for second in children[i + 1:]:
                    s1 = next(s for s in ALL_SPECS if s.key == first)
                    s2 = next(s for s in ALL_SPECS if s.key == second)
                    add(
                        first,
                        second,
                        RelationType.BROTHER
                        if s2.gender == Gender.MALE
                        else RelationType.SISTER,
                    )
                    add(
                        second,
                        first,
                        RelationType.BROTHER
                        if s1.gender == Gender.MALE
                        else RelationType.SISTER,
                    )

        for husband, wife, contract_date, *_ in MARRIAGES:
            add(husband, wife, RelationType.WIFE, contract_date)
            add(wife, husband, RelationType.HUSBAND, contract_date)

        self.db.flush()
        print(f"  ✓ {created} علاقة أُسرية")

    def seed_marriages(self) -> None:
        self.marriage_objs: dict[tuple[str, str], MarriageContract] = {}

        for idx, (husband, wife, contract_date, prompt, deferred) in enumerate(
            MARRIAGES, start=1
        ):
            h, w = self.persons[husband], self.persons[wife]
            gov_code = next(s.gov_code for s in ALL_SPECS if s.key == husband)

            contract = MarriageContract(
                contract_number=f"M-{contract_date.year}-{idx:04d}",
                husband_id=h.id,
                wife_id=w.id,
                contract_date=contract_date,
                governorate_id=self.govs[gov_code].id,
                court_name=f"محكمة الأحوال الشخصية في {self.govs[gov_code].name_ar}",
                officiant_name="الشيخ عبد الرحمن الحيدري",
                witness1_name="محمد جاسم الطائي",
                witness2_name="عادل نوري الساعدي",
                dowry_prompt=Decimal(prompt),
                dowry_deferred=Decimal(deferred),
                currency="IQD",
                is_active=True,
                document_issued=True,
            )
            self.db.add(contract)
            self.marriage_objs[(husband, wife)] = contract

            h.marital_status = MaritalStatus.MARRIED
            w.marital_status = MaritalStatus.MARRIED

        self.db.flush()
        print(f"  ✓ {len(MARRIAGES)} عقد زواج")

    def seed_divorces(self) -> None:
        for idx, (husband, wife, div_date, div_type, reason, custody) in enumerate(
            DIVORCES, start=1
        ):
            contract = self.marriage_objs[(husband, wife)]
            self.db.add(
                DivorceRecord(
                    record_number=f"D-{div_date.year}-{idx:04d}",
                    marriage_id=contract.id,
                    divorce_date=div_date,
                    divorce_type=div_type,
                    court_name=contract.court_name,
                    judge_name="القاضي حيدر عبد الزهرة",
                    reason=reason,
                    custody_notes=custody,
                    document_issued=True,
                )
            )
            contract.is_active = False
            self.persons[husband].marital_status = MaritalStatus.DIVORCED
            self.persons[wife].marital_status = MaritalStatus.DIVORCED

        self.db.flush()
        print(f"  ✓ {len(DIVORCES)} واقعة طلاق")

    def seed_births(self) -> None:
        count = 0
        for father, mother, children in PARENTAGE:
            for child in children:
                spec = next(s for s in ALL_SPECS if s.key == child)
                count += 1
                self.db.add(
                    BirthRecord(
                        record_number=f"B-{spec.birth.year}-{count:04d}",
                        person_id=self.persons[child].id,
                        father_id=self.persons[father].id,
                        mother_id=self.persons[mother].id,
                        birth_date=spec.birth,
                        hospital_name=HOSPITALS[spec.gov_code],
                        governorate_id=self.govs[spec.gov_code].id,
                        birth_weight_grams=2800 + (count * 37) % 1400,
                        delivery_type="طبيعية" if count % 3 else "قيصرية",
                        attending_physician="د. سعاد عبد الكريم",
                        informant_name=self.persons[father].full_name,
                        informant_relation="الأب",
                        # التسجيل خلال أسبوعين من الولادة
                        registration_date=spec.birth + timedelta(days=(count % 14) + 1),
                        registration_office=f"دائرة أحوال {self.govs[spec.gov_code].name_ar}",
                        certificate_issued=True,
                    )
                )
        self.db.flush()
        print(f"  ✓ {count} واقعة ميلاد")

    def seed_deaths(self) -> None:
        count = 0
        for spec in ALL_SPECS:
            if spec.death is None:
                continue
            count += 1
            person = self.persons[spec.key]
            self.db.add(
                DeathRecord(
                    record_number=f"V-{spec.death.year}-{count:04d}",
                    person_id=person.id,
                    death_date=spec.death,
                    death_place=HOSPITALS[spec.gov_code],
                    governorate_id=self.govs[spec.gov_code].id,
                    cause_of_death=spec.death_cause,
                    cause_category="طبيعية",
                    reporting_authority=HOSPITALS[spec.gov_code],
                    certifying_physician="د. رياض حمزة",
                    registration_date=spec.death + timedelta(days=3),
                    certificate_issued=True,
                )
            )
            # في PostgreSQL يقوم بذلك مُشغّل؛ نضبطه هنا ليصحّ في SQLite أيضاً
            person.life_status = LifeStatus.DECEASED

            # ترمُّل الزوج الباقي على قيد الحياة
            for (husband, wife, *_), contract in zip(MARRIAGES, self.marriage_objs.values()):
                if spec.key == husband and contract.is_active:
                    self.persons[wife].marital_status = MaritalStatus.WIDOWED
                elif spec.key == wife and contract.is_active:
                    self.persons[husband].marital_status = MaritalStatus.WIDOWED

        self.db.flush()
        print(f"  ✓ {count} واقعة وفاة")

    def seed_documents(self) -> None:
        count = 0
        for spec in ALL_SPECS:
            person = self.persons[spec.key]
            # البطاقة الوطنية تُصدر عند بلوغ 15 سنة
            eligible = date.today().year - spec.birth.year >= 15
            if not eligible or spec.death is not None:
                continue

            count += 1
            issue = date(max(spec.birth.year + 18, 2016), 1 + (count % 12), 1 + (count % 27))
            self.db.add(
                Document(
                    person_id=person.id,
                    document_type=DocumentType.NATIONAL_CARD,
                    document_number=f"NC{count:08d}",
                    issue_date=issue,
                    expiry_date=issue.replace(year=issue.year + 10),
                    issuing_authority=f"مديرية أحوال {self.govs[spec.gov_code].name_ar}",
                    issuing_governorate_id=self.govs[spec.gov_code].id,
                    status=DocumentStatus.VALID,
                )
            )

            # جوازات لبعض البالغين
            if count % 3 == 0:
                p_issue = date(2021, 1 + (count % 12), 1 + (count % 27))
                self.db.add(
                    Document(
                        person_id=person.id,
                        document_type=DocumentType.PASSPORT,
                        document_number=f"A{count:07d}",
                        issue_date=p_issue,
                        expiry_date=p_issue.replace(year=p_issue.year + 8),
                        issuing_authority="مديرية الجوازات العامة",
                        issuing_governorate_id=self.govs[spec.gov_code].id,
                        status=DocumentStatus.VALID,
                    )
                )
                count += 1

        self.db.flush()
        print(f"  ✓ {count} وثيقة رسمية")

    def seed_family_cards(self) -> None:
        # من كوّن أسرةً خاصة به لم يعد تابعاً في بطاقة أبيه: عند الزواج
        # يُرفع الابن/الابنة من بطاقة الوالد ويُقيَّد في بطاقة الأسرة الجديدة.
        heads_of_household = {father for father, _, _ in PARENTAGE} | {
            mother for _, mother, _ in PARENTAGE
        }

        count = 0
        for father, mother, children in PARENTAGE:
            count += 1
            head = self.persons[father]
            gov_code = next(s.gov_code for s in ALL_SPECS if s.key == father)

            card = FamilyCard(
                card_number=f"FC-{count:06d}",
                head_person_id=head.id,
                governorate_id=self.govs[gov_code].id,
                issue_date=date(2020, 1 + (count % 12), 1 + (count % 27)),
                issuing_office=f"دائرة أحوال {self.govs[gov_code].name_ar}",
                is_active=True,
            )
            self.db.add(card)
            self.db.flush()

            card.members.append(
                FamilyCardMember(
                    family_card_id=card.id,
                    person_id=self.persons[mother].id,
                    relation_to_head=RelationType.WIFE,
                )
            )
            for child in children:
                if child in heads_of_household:
                    continue  # انتقل إلى بطاقة أسرته الخاصة
                spec = next(s for s in ALL_SPECS if s.key == child)
                card.members.append(
                    FamilyCardMember(
                        family_card_id=card.id,
                        person_id=self.persons[child].id,
                        relation_to_head=RelationType.SON
                        if spec.gender == Gender.MALE
                        else RelationType.DAUGHTER,
                    )
                )

        self.db.flush()
        print(f"  ✓ {count} بطاقة عائلة")

    def seed_requests(self) -> None:
        admin = self.db.scalar(select(User).where(User.username == "admin"))
        samples = [
            ("g2_ahmad", RequestType.RENEW, "تجديد البطاقة الوطنية",
             RequestStatus.APPROVED, None, 25000),
            ("g2_layla", RequestType.REPLACEMENT, "إصدار بدل ضائع لجواز السفر",
             RequestStatus.UNDER_REVIEW, None, 100000),
            ("g3_kareem", RequestType.ISSUE, "إصدار بطاقة عائلة",
             RequestStatus.SUBMITTED, None, 15000),
            ("g3_sara", RequestType.AMEND, "تصحيح اسم الأم في السجل",
             RequestStatus.REJECTED,
             "المستمسكات المقدَّمة غير كافية لإثبات التصحيح المطلوب", 10000),
            ("g2_omar", RequestType.ISSUE, "إصدار شهادة جنسية",
             RequestStatus.APPROVED, None, 20000),
            ("g3_ibrahim", RequestType.ISSUE, "إصدار جواز سفر لأول مرة",
             RequestStatus.UNDER_REVIEW, None, 100000),
        ]

        for idx, (key, rtype, subject, status, reason, fee) in enumerate(samples, start=1):
            self.db.add(
                ServiceRequest(
                    reference_number=f"REQ-2026-{idx:06d}",
                    person_id=self.persons[key].id,
                    request_type=rtype,
                    subject=subject,
                    status=status,
                    rejection_reason=reason,
                    fee_amount=Decimal(fee),
                    fee_paid=status != RequestStatus.SUBMITTED,
                    submitted_by=admin.id,
                )
            )
        self.db.flush()
        print(f"  ✓ {len(samples)} معاملة")

    # -- التشغيل --------------------------------------------------------

    def run(self) -> None:
        print("\nتعبئة البيانات التجريبية:")
        self.seed_locations()
        self.seed_rbac()
        self.seed_admin()
        self.seed_persons()
        self.seed_addresses()
        self.seed_marriages()
        self.seed_divorces()
        self.seed_relations()
        self.seed_births()
        self.seed_deaths()
        self.seed_documents()
        self.seed_family_cards()
        self.seed_requests()


def reset_database() -> None:
    """يحذف كل الجداول ويعيد إنشاءها — للتطوير فقط."""
    print("حذف الجداول السابقة وإعادة إنشائها...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def main() -> int:
    parser = argparse.ArgumentParser(description="تعبئة قاعدة البيانات ببيانات تجريبية")
    parser.add_argument(
        "--reset", action="store_true", help="حذف البيانات السابقة قبل التعبئة"
    )
    args = parser.parse_args()

    if args.reset:
        reset_database()

    db = SessionLocal()
    try:
        if db.scalar(select(Person).limit(1)) is not None:
            print("قاعدة البيانات تحتوي بيانات بالفعل. استخدم --reset لإعادة التعبئة.")
            return 1

        Seeder(db).run()
        # كل شيء داخل معاملة واحدة: إمّا أن تُكتب البيانات كاملة أو لا شيء
        db.commit()
        print("\nاكتملت التعبئة بنجاح.\n")
        return 0
    except Exception:
        db.rollback()
        print("\nفشلت التعبئة — تم التراجع عن كل التغييرات.\n", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
