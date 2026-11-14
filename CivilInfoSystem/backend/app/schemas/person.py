"""مخططات الأشخاص والعناوين والعلاقات الأُسرية."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.enums import (
    BloodType,
    Gender,
    LifeStatus,
    MaritalStatus,
    RelationType,
)
from app.utils.validators import validate_national_id


# ---------------------------------------------------------------------------
# العناوين
# ---------------------------------------------------------------------------

class AddressBase(BaseModel):
    """حقول العنوان المشتركة."""

    governorate_id: int = Field(..., description="المحافظة")
    district_id: int | None = Field(None, description="القضاء")
    subdistrict_id: int | None = Field(None, description="الناحية")
    quarter: str | None = Field(None, max_length=100, description="المحلة")
    street: str | None = Field(None, max_length=100, description="الزقاق")
    house_number: str | None = Field(None, max_length=20, description="رقم الدار")
    postal_code: str | None = Field(None, max_length=10, description="الرمز البريدي")
    details: str | None = Field(None, description="تفاصيل إضافية")


class AddressCreate(AddressBase):
    """إنشاء عنوان جديد."""

    valid_from: date = Field(default_factory=date.today, description="ساري من")


class AddressRead(AddressBase):
    """عنوان معروض."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    valid_from: date
    valid_to: date | None = None
    is_current: bool

    @computed_field
    @property
    def formatted(self) -> str:
        """العنوان بصيغة نصّية."""
        parts = [self.quarter, self.street, self.house_number]
        return " - ".join(p for p in parts if p) or "غير محدد"


# ---------------------------------------------------------------------------
# الأشخاص
# ---------------------------------------------------------------------------

class PersonBase(BaseModel):
    """حقول الشخص القابلة للتعديل."""

    first_name: str = Field(..., min_length=2, max_length=50, description="الاسم الأول")
    father_name: str = Field(..., min_length=2, max_length=50, description="اسم الأب")
    grandfather_name: str = Field(
        ..., min_length=2, max_length=50, description="اسم الجد"
    )
    family_name: str = Field(..., min_length=2, max_length=50, description="اللقب")
    mother_full_name: str = Field(
        ..., min_length=2, max_length=150, description="اسم الأم الكامل"
    )

    birth_date: date = Field(..., description="تاريخ الميلاد")
    birth_governorate_id: int | None = Field(None, description="محافظة الميلاد")
    birth_place_detail: str | None = Field(None, max_length=200)

    gender: Gender = Field(..., description="الجنس")
    nationality: str = Field("عراقي", max_length=60, description="الجنسية")
    religion: str | None = Field(None, max_length=50)
    blood_type: BloodType | None = Field(None, description="فصيلة الدم")
    marital_status: MaritalStatus = Field(
        MaritalStatus.SINGLE, description="الحالة الاجتماعية"
    )
    occupation: str | None = Field(None, max_length=100)
    education_level: str | None = Field(None, max_length=100)
    notes: str | None = None

    @field_validator("birth_date")
    @classmethod
    def _birth_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("تاريخ الميلاد لا يمكن أن يكون في المستقبل")
        # حدّ أعلى معقول للعمر — يلتقط أخطاء الإدخال الجسيمة (سنة بأربع خانات مقلوبة)
        if v.year < date.today().year - 130:
            raise ValueError("تاريخ الميلاد غير معقول")
        return v

    @field_validator(
        "first_name", "father_name", "grandfather_name", "family_name",
        "mother_full_name",
    )
    @classmethod
    def _clean_name(cls, v: str) -> str:
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("الاسم لا يمكن أن يكون فارغاً")
        return cleaned


class PersonCreate(PersonBase):
    """إنشاء شخص جديد."""

    national_id: str = Field(
        ..., min_length=12, max_length=12, description="الرقم الوطني (12 خانة)"
    )
    address: AddressCreate | None = Field(None, description="العنوان الحالي")

    @field_validator("national_id")
    @classmethod
    def _check_national_id(cls, v: str) -> str:
        if not validate_national_id(v):
            raise ValueError("الرقم الوطني غير صالح — تحقّق من الخانات وخانة التدقيق")
        return v


class PersonUpdate(BaseModel):
    """تعديل بيانات شخص — كل الحقول اختيارية.

    الرقم الوطني وتاريخ الميلاد غير قابلين للتعديل هنا: تغييرهما واقعة
    تصحيح سجل تمرّ بمعاملة معتمَدة لا بتعديل مباشر.
    """

    first_name: str | None = Field(None, min_length=2, max_length=50)
    father_name: str | None = Field(None, min_length=2, max_length=50)
    grandfather_name: str | None = Field(None, min_length=2, max_length=50)
    family_name: str | None = Field(None, min_length=2, max_length=50)
    mother_full_name: str | None = Field(None, min_length=2, max_length=150)
    birth_governorate_id: int | None = None
    birth_place_detail: str | None = Field(None, max_length=200)
    religion: str | None = Field(None, max_length=50)
    blood_type: BloodType | None = None
    marital_status: MaritalStatus | None = None
    occupation: str | None = Field(None, max_length=100)
    education_level: str | None = Field(None, max_length=100)
    notes: str | None = None


class PersonSummary(BaseModel):
    """بيانات شخص مختصرة — تُستعمل في القوائم ونتائج البحث."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    national_id: str
    first_name: str
    father_name: str
    grandfather_name: str
    family_name: str
    birth_date: date
    gender: Gender
    life_status: LifeStatus

    @computed_field
    @property
    def full_name(self) -> str:
        return (
            f"{self.first_name} {self.father_name} "
            f"{self.grandfather_name} {self.family_name}"
        )


class PersonRead(PersonBase):
    """بيانات شخص كاملة."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    national_id: str
    life_status: LifeStatus
    birth_date_hijri: str | None = None
    photo_path: str | None = None
    current_address: AddressRead | None = None

    @computed_field
    @property
    def full_name(self) -> str:
        return (
            f"{self.first_name} {self.father_name} "
            f"{self.grandfather_name} {self.family_name}"
        )


class PersonSearchResult(PersonSummary):
    """نتيجة بحث مع درجة التطابق."""

    similarity: float | None = Field(
        None, description="درجة التشابه بين 0 و1 — تظهر في البحث التقريبي فقط"
    )


# ---------------------------------------------------------------------------
# العلاقات وشجرة العائلة
# ---------------------------------------------------------------------------

class RelationCreate(BaseModel):
    """إنشاء علاقة أُسرية."""

    related_person_id: uuid.UUID = Field(..., description="الطرف الآخر")
    relation_type: RelationType = Field(
        ..., description="نوع علاقة الطرف الآخر بالشخص"
    )
    start_date: date | None = None


class RelationRead(BaseModel):
    """علاقة أُسرية معروضة."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    relation_type: RelationType
    is_active: bool
    start_date: date | None = None
    end_date: date | None = None
    related_person: PersonSummary


class FamilyTreeNode(BaseModel):
    """عقدة في شجرة العائلة."""

    person: PersonSummary
    relation: RelationType | None = Field(
        None, description="صلة هذه العقدة بالشخص المركزي"
    )
    children: list[FamilyTreeNode] = Field(default_factory=list)


class FamilyTree(BaseModel):
    """شجرة عائلة الشخص حتى ثلاثة أجيال."""

    person: PersonSummary
    father: FamilyTreeNode | None = None
    mother: FamilyTreeNode | None = None
    grandparents: list[FamilyTreeNode] = Field(default_factory=list)
    spouses: list[FamilyTreeNode] = Field(default_factory=list)
    siblings: list[FamilyTreeNode] = Field(default_factory=list)
    children: list[FamilyTreeNode] = Field(default_factory=list)
    grandchildren: list[FamilyTreeNode] = Field(default_factory=list)


class TreeConflict(BaseModel):
    """تعارض منطقي مكتشَف في شجرة العائلة."""

    نوع_التعارض: str
    الوصف: str
    الأشخاص: list[str] = Field(default_factory=list)


class ConsistencyReport(BaseModel):
    """تقرير فحص تماسك العلاقات."""

    سليم: bool
    عدد_التعارضات: int
    التعارضات: list[TreeConflict] = Field(default_factory=list)


FamilyTreeNode.model_rebuild()
