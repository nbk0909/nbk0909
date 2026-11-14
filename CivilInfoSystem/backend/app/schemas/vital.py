"""مخططات الواقعات المدنية: الميلاد، الوفاة، الزواج، الطلاق."""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.person import PersonSummary


# ---------------------------------------------------------------------------
# الميلاد
# ---------------------------------------------------------------------------

class BirthRecordCreate(BaseModel):
    """تسجيل واقعة ميلاد."""

    person_id: uuid.UUID = Field(..., description="سجل المولود")
    father_id: uuid.UUID | None = Field(None, description="الأب")
    mother_id: uuid.UUID | None = Field(None, description="الأم")

    birth_date: date = Field(..., description="تاريخ الولادة")
    birth_time: time | None = None
    hospital_name: str | None = Field(None, max_length=200)
    governorate_id: int = Field(..., description="محافظة الواقعة")
    birth_weight_grams: int | None = Field(
        None, ge=200, le=8000, description="وزن المولود بالغرام"
    )
    delivery_type: str | None = Field(None, max_length=50)
    attending_physician: str | None = Field(None, max_length=150)
    informant_name: str | None = Field(None, max_length=200)
    informant_relation: str | None = Field(None, max_length=50)
    registration_office: str | None = Field(None, max_length=150)

    @field_validator("birth_date")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("تاريخ الولادة لا يمكن أن يكون في المستقبل")
        return v

    @model_validator(mode="after")
    def _parents_differ(self):
        if self.father_id and self.mother_id and self.father_id == self.mother_id:
            raise ValueError("لا يمكن أن يكون الأب والأم الشخص نفسه")
        return self


class BirthRecordRead(BaseModel):
    """واقعة ميلاد معروضة."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    record_number: str
    birth_date: date
    birth_time: time | None = None
    hospital_name: str | None = None
    governorate_id: int
    birth_weight_grams: int | None = None
    delivery_type: str | None = None
    registration_date: date
    certificate_issued: bool
    person: PersonSummary
    father: PersonSummary | None = None
    mother: PersonSummary | None = None


# ---------------------------------------------------------------------------
# الوفاة
# ---------------------------------------------------------------------------

class DeathRecordCreate(BaseModel):
    """تسجيل واقعة وفاة."""

    person_id: uuid.UUID = Field(..., description="سجل المتوفى")
    death_date: date = Field(..., description="تاريخ الوفاة")
    death_time: time | None = None
    death_place: str | None = Field(None, max_length=200)
    governorate_id: int = Field(..., description="محافظة الواقعة")
    cause_of_death: str | None = Field(None, max_length=300)
    cause_category: str | None = Field(None, max_length=100)
    reporting_authority: str | None = Field(None, max_length=200)
    certifying_physician: str | None = Field(None, max_length=150)
    burial_place: str | None = Field(None, max_length=200)

    @field_validator("death_date")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("تاريخ الوفاة لا يمكن أن يكون في المستقبل")
        return v


class DeathRecordRead(BaseModel):
    """واقعة وفاة معروضة."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    record_number: str
    death_date: date
    death_place: str | None = None
    governorate_id: int
    cause_of_death: str | None = None
    cause_category: str | None = None
    reporting_authority: str | None = None
    registration_date: date
    certificate_issued: bool
    person: PersonSummary


# ---------------------------------------------------------------------------
# الزواج
# ---------------------------------------------------------------------------

class MarriageCreate(BaseModel):
    """تسجيل عقد زواج."""

    husband_id: uuid.UUID = Field(..., description="الزوج")
    wife_id: uuid.UUID = Field(..., description="الزوجة")
    contract_date: date = Field(..., description="تاريخ العقد")
    governorate_id: int = Field(..., description="محافظة العقد")
    court_name: str | None = Field(None, max_length=200)
    officiant_name: str = Field(..., min_length=3, max_length=150, description="المأذون")

    witness1_name: str = Field(..., min_length=3, max_length=150)
    witness1_national_id: str | None = Field(None, min_length=12, max_length=12)
    witness2_name: str = Field(..., min_length=3, max_length=150)
    witness2_national_id: str | None = Field(None, min_length=12, max_length=12)

    dowry_prompt: Decimal | None = Field(None, ge=0, description="المهر المعجّل")
    dowry_deferred: Decimal | None = Field(None, ge=0, description="المهر المؤجّل")
    currency: str = Field("IQD", max_length=10)

    @field_validator("contract_date")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("تاريخ العقد لا يمكن أن يكون في المستقبل")
        return v

    @model_validator(mode="after")
    def _spouses_differ(self):
        if self.husband_id == self.wife_id:
            raise ValueError("لا يمكن أن يكون الزوجان الشخص نفسه")
        return self

    @model_validator(mode="after")
    def _witnesses_differ(self):
        both = self.witness1_national_id, self.witness2_national_id
        if all(both) and both[0] == both[1]:
            raise ValueError("لا يصحّ أن يكون الشاهدان شخصاً واحداً")
        return self


class MarriageRead(BaseModel):
    """عقد زواج معروض."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_number: str
    contract_date: date
    governorate_id: int
    court_name: str | None = None
    officiant_name: str
    witness1_name: str
    witness2_name: str
    dowry_prompt: Decimal | None = None
    dowry_deferred: Decimal | None = None
    currency: str
    is_active: bool
    husband: PersonSummary
    wife: PersonSummary


# ---------------------------------------------------------------------------
# الطلاق
# ---------------------------------------------------------------------------

class DivorceCreate(BaseModel):
    """تسجيل واقعة طلاق."""

    marriage_id: uuid.UUID = Field(..., description="عقد الزواج المرتبط")
    divorce_date: date = Field(..., description="تاريخ الطلاق")
    divorce_type: str | None = Field(
        None, max_length=50, description="رجعي / بائن / خُلع"
    )
    court_name: str | None = Field(None, max_length=200)
    judge_name: str | None = Field(None, max_length=150)
    reason: str | None = None
    custody_notes: str | None = Field(None, description="ترتيبات الحضانة")

    @field_validator("divorce_date")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("تاريخ الطلاق لا يمكن أن يكون في المستقبل")
        return v


class DivorceRead(BaseModel):
    """واقعة طلاق معروضة."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    record_number: str
    divorce_date: date
    divorce_type: str | None = None
    court_name: str | None = None
    judge_name: str | None = None
    custody_notes: str | None = None
    marriage: MarriageRead
