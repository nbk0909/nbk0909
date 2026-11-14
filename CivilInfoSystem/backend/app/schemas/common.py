"""مخططات مشتركة: الترقيم، والاستجابات العامة، وتسميات الحقول العربية.

قرار في تسمية الحقول
--------------------
مفاتيح JSON تبقى بأحرف لاتينية (first_name لا الاسم_الأول) لأنها معرّفات
برمجية تُستعمل في الكود والمسارات والفهارس. أمّا ما يراه المستخدم — عناوين
الحقول في النماذج ورسائل الأخطاء — فبالعربية، عبر خريطة FIELD_LABELS أدناه
التي يستعملها معالج أخطاء التحقق وواجهة المستخدم على حد سواء.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# تسميات الحقول بالعربية
# ---------------------------------------------------------------------------

FIELD_LABELS: dict[str, str] = {
    # الشخص
    "national_id": "الرقم الوطني",
    "first_name": "الاسم الأول",
    "father_name": "اسم الأب",
    "grandfather_name": "اسم الجد",
    "family_name": "اللقب",
    "mother_full_name": "اسم الأم الكامل",
    "birth_date": "تاريخ الميلاد",
    "birth_date_hijri": "تاريخ الميلاد الهجري",
    "birth_governorate_id": "محافظة الميلاد",
    "birth_place_detail": "مكان الميلاد",
    "gender": "الجنس",
    "nationality": "الجنسية",
    "religion": "الديانة",
    "blood_type": "فصيلة الدم",
    "marital_status": "الحالة الاجتماعية",
    "occupation": "المهنة",
    "education_level": "المؤهل العلمي",
    "life_status": "حالة الحياة",
    "notes": "ملاحظات",
    # العنوان
    "governorate_id": "المحافظة",
    "district_id": "القضاء",
    "subdistrict_id": "الناحية",
    "quarter": "المحلة",
    "street": "الزقاق",
    "house_number": "رقم الدار",
    "postal_code": "الرمز البريدي",
    # الواقعات
    "record_number": "رقم السجل",
    "person_id": "الشخص",
    "father_id": "الأب",
    "mother_id": "الأم",
    "hospital_name": "المستشفى",
    "birth_weight_grams": "وزن المولود",
    "delivery_type": "نوع الولادة",
    "attending_physician": "الطبيب المشرف",
    "informant_name": "اسم المبلِّغ",
    "informant_relation": "صلة المبلِّغ",
    "registration_date": "تاريخ التسجيل",
    "death_date": "تاريخ الوفاة",
    "death_place": "مكان الوفاة",
    "cause_of_death": "سبب الوفاة",
    "cause_category": "تصنيف السبب",
    "reporting_authority": "الجهة المبلِّغة",
    "burial_place": "مكان الدفن",
    # الزواج والطلاق
    "contract_number": "رقم العقد",
    "husband_id": "الزوج",
    "wife_id": "الزوجة",
    "contract_date": "تاريخ العقد",
    "court_name": "المحكمة",
    "officiant_name": "المأذون",
    "witness1_name": "الشاهد الأول",
    "witness2_name": "الشاهد الثاني",
    "dowry_prompt": "المهر المعجّل",
    "dowry_deferred": "المهر المؤجّل",
    "divorce_date": "تاريخ الطلاق",
    "divorce_type": "نوع الطلاق",
    "custody_notes": "ترتيبات الحضانة",
    # الوثائق
    "document_type": "نوع الوثيقة",
    "document_number": "رقم الوثيقة",
    "issue_date": "تاريخ الإصدار",
    "expiry_date": "تاريخ الانتهاء",
    "issuing_authority": "جهة الإصدار",
    "status": "الحالة",
    # المعاملات
    "reference_number": "الرقم المرجعي",
    "request_type": "نوع المعاملة",
    "subject": "الموضوع",
    "details": "التفاصيل",
    "rejection_reason": "سبب الرفض",
    "fee_amount": "الرسوم",
    # المستخدم
    "username": "اسم المستخدم",
    "password": "كلمة المرور",
    "new_password": "كلمة المرور الجديدة",
    "current_password": "كلمة المرور الحالية",
    "full_name_ar": "الاسم الكامل",
    "email": "البريد الإلكتروني",
    "phone": "رقم الهاتف",
}


def field_label(name: str) -> str:
    """يُرجع التسمية العربية للحقل، أو اسمه كما هو إن لم تُعرَّف."""
    return FIELD_LABELS.get(name, name)


# ---------------------------------------------------------------------------
# الترقيم
# ---------------------------------------------------------------------------

class PaginationParams(BaseModel):
    """معاملات الترقيم المشتركة بين مسارات القوائم."""

    page: int = Field(1, ge=1, description="رقم الصفحة")
    page_size: int = Field(
        20, ge=1, le=100, description="عدد السجلات في الصفحة (الحد الأقصى 100)"
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    """صفحة نتائج مع بيانات الترقيم."""

    items: list[T] = Field(default_factory=list, description="السجلات")
    total: int = Field(0, description="إجمالي السجلات المطابقة")
    page: int = Field(1, description="رقم الصفحة الحالية")
    page_size: int = Field(20, description="عدد السجلات في الصفحة")

    @computed_field
    @property
    def total_pages(self) -> int:
        """عدد الصفحات الكلي."""
        if self.page_size <= 0:
            return 0
        return -(-self.total // self.page_size)  # قسمة لأعلى

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


# ---------------------------------------------------------------------------
# استجابات عامة
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    """استجابة عامة بنجاح العملية."""

    نجاح: bool = True
    الرسالة: str


class ErrorResponse(BaseModel):
    """استجابة خطأ."""

    نجاح: bool = False
    الرسالة: str
    الرمز: str | None = None
