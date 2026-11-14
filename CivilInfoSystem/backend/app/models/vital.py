"""نماذج الواقعات المدنية: الميلاد، الوفاة، الزواج، الطلاق."""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import (
    AuditMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.person import Person
from app.models.types import GUID


class BirthRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """واقعة ميلاد."""

    __tablename__ = "birth_records"
    __table_args__ = (
        CheckConstraint(
            "birth_weight_grams IS NULL OR "
            "(birth_weight_grams >= 200 AND birth_weight_grams <= 8000)",
            name="birth_weight",
        ),
        CheckConstraint("registration_date >= birth_date", name="birth_reg"),
        CheckConstraint(
            "father_id IS NULL OR mother_id IS NULL OR father_id <> mother_id",
            name="parents_differ",
        ),
    )

    record_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    person_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    father_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("persons.id"), index=True
    )
    mother_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("persons.id"), index=True
    )

    birth_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    birth_time: Mapped[time | None] = mapped_column(Time)
    hospital_name: Mapped[str | None] = mapped_column(String(200))
    governorate_id: Mapped[int] = mapped_column(
        ForeignKey("governorates.id"), nullable=False, index=True
    )
    birth_weight_grams: Mapped[int | None] = mapped_column(Integer)
    delivery_type: Mapped[str | None] = mapped_column(String(50))
    attending_physician: Mapped[str | None] = mapped_column(String(150))
    informant_name: Mapped[str | None] = mapped_column(String(200))
    informant_relation: Mapped[str | None] = mapped_column(String(50))

    registration_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today
    )
    registration_office: Mapped[str | None] = mapped_column(String(150))
    certificate_issued: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    person: Mapped[Person] = relationship(
        back_populates="birth_record", foreign_keys=[person_id]
    )
    father: Mapped[Person | None] = relationship(foreign_keys=[father_id])
    mother: Mapped[Person | None] = relationship(foreign_keys=[mother_id])

    def __repr__(self) -> str:
        return f"<BirthRecord {self.record_number}>"


class DeathRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """واقعة وفاة.

    تسجيل الوفاة يُحدِّث حالة الشخص إلى «متوفى» ويُنهي علاقات الزوجية
    النشطة — يُنفَّذ ذلك بمُشغّل في PostgreSQL وبطبقة الخدمات في SQLite.
    """

    __tablename__ = "death_records"
    __table_args__ = (
        CheckConstraint("registration_date >= death_date", name="death_reg"),
    )

    record_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    person_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, unique=True
    )

    death_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    death_time: Mapped[time | None] = mapped_column(Time)
    death_place: Mapped[str | None] = mapped_column(String(200))
    governorate_id: Mapped[int] = mapped_column(
        ForeignKey("governorates.id"), nullable=False, index=True
    )
    cause_of_death: Mapped[str | None] = mapped_column(String(300))
    cause_category: Mapped[str | None] = mapped_column(String(100))
    reporting_authority: Mapped[str | None] = mapped_column(String(200))
    certifying_physician: Mapped[str | None] = mapped_column(String(150))
    burial_place: Mapped[str | None] = mapped_column(String(200))

    registration_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today
    )
    certificate_issued: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    person: Mapped[Person] = relationship(back_populates="death_record")

    def __repr__(self) -> str:
        return f"<DeathRecord {self.record_number}>"


class MarriageContract(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin
):
    """عقد زواج."""

    __tablename__ = "marriage_contracts"
    __table_args__ = (
        CheckConstraint("husband_id <> wife_id", name="spouses_differ"),
        CheckConstraint(
            "(dowry_prompt IS NULL OR dowry_prompt >= 0) AND "
            "(dowry_deferred IS NULL OR dowry_deferred >= 0)",
            name="dowry_positive",
        ),
    )

    contract_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    husband_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    wife_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    contract_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    contract_date_hijri: Mapped[str | None] = mapped_column(String(12))
    governorate_id: Mapped[int] = mapped_column(
        ForeignKey("governorates.id"), nullable=False
    )
    court_name: Mapped[str | None] = mapped_column(String(200))
    officiant_name: Mapped[str] = mapped_column(String(150), nullable=False)

    witness1_name: Mapped[str] = mapped_column(String(150), nullable=False)
    witness1_national_id: Mapped[str | None] = mapped_column(String(12))
    witness2_name: Mapped[str] = mapped_column(String(150), nullable=False)
    witness2_national_id: Mapped[str | None] = mapped_column(String(12))

    dowry_prompt: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    dowry_deferred: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="IQD")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    document_issued: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    husband: Mapped[Person] = relationship(foreign_keys=[husband_id])
    wife: Mapped[Person] = relationship(foreign_keys=[wife_id])
    divorce: Mapped[DivorceRecord | None] = relationship(
        back_populates="marriage", uselist=False
    )

    def __repr__(self) -> str:
        return f"<MarriageContract {self.contract_number}>"


class DivorceRecord(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin
):
    """واقعة طلاق."""

    __tablename__ = "divorce_records"

    record_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    marriage_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("marriage_contracts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    divorce_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    divorce_date_hijri: Mapped[str | None] = mapped_column(String(12))
    divorce_type: Mapped[str | None] = mapped_column(String(50))
    court_name: Mapped[str | None] = mapped_column(String(200))
    judge_name: Mapped[str | None] = mapped_column(String(150))
    reason: Mapped[str | None] = mapped_column(Text)
    custody_notes: Mapped[str | None] = mapped_column(Text)
    document_issued: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    marriage: Mapped[MarriageContract] = relationship(back_populates="divorce")

    def __repr__(self) -> str:
        return f"<DivorceRecord {self.record_number}>"
