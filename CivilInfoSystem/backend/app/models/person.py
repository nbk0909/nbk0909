"""نماذج الأشخاص والعناوين والعلاقات الأُسرية."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import (
    AuditMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    enum_column,
)
from app.models.enums import BloodType, Gender, LifeStatus, MaritalStatus, RelationType
from app.models.types import GUID
from app.utils.arabic import normalize_arabic


class Person(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """السجل المدني الأساسي للشخص."""

    __tablename__ = "persons"
    __table_args__ = (
        CheckConstraint("length(national_id) = 12", name="national_id_length"),
        # فهرس ثلاثيات الحروف: يجعل البحث التقريبي عن الأسماء المتشابهة
        # (LIKE '%...%' و similarity) سريعاً بدل مسح الجدول كاملاً
        Index(
            "ix_persons_name_trgm",
            "full_name_normalized",
            postgresql_using="gin",
            postgresql_ops={"full_name_normalized": "gin_trgm_ops"},
        ),
    )

    national_id: Mapped[str] = mapped_column(
        String(12), nullable=False, unique=True, index=True
    )

    # الاسم الرباعي
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    father_name: Mapped[str] = mapped_column(String(50), nullable=False)
    grandfather_name: Mapped[str] = mapped_column(String(50), nullable=False)
    family_name: Mapped[str] = mapped_column(String(50), nullable=False)
    mother_full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # يُملأ تلقائياً — انظر المستمع أسفل الملف
    full_name_normalized: Mapped[str | None] = mapped_column(String(300), index=True)

    # الميلاد
    birth_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    birth_date_hijri: Mapped[str | None] = mapped_column(String(12))
    birth_governorate_id: Mapped[int | None] = mapped_column(
        ForeignKey("governorates.id")
    )
    birth_place_detail: Mapped[str | None] = mapped_column(String(200))

    gender: Mapped[Gender] = enum_column(Gender, nullable=False)
    nationality: Mapped[str] = mapped_column(
        String(60), nullable=False, default="عراقي"
    )
    religion: Mapped[str | None] = mapped_column(String(50))
    blood_type: Mapped[BloodType | None] = enum_column(BloodType, nullable=True)
    marital_status: Mapped[MaritalStatus] = enum_column(
        MaritalStatus, nullable=False, default=MaritalStatus.SINGLE
    )
    occupation: Mapped[str | None] = mapped_column(String(100))
    education_level: Mapped[str | None] = mapped_column(String(100))

    life_status: Mapped[LifeStatus] = enum_column(
        LifeStatus, nullable=False, default=LifeStatus.ALIVE, index=True
    )

    # مسارات الملفات — لا تُخزَّن الصور داخل قاعدة البيانات
    photo_path: Mapped[str | None] = mapped_column(String(300))
    fingerprint_path: Mapped[str | None] = mapped_column(String(300))

    notes: Mapped[str | None] = mapped_column(Text)

    # ------------------------------------------------------------------
    # العلاقات
    # ------------------------------------------------------------------
    addresses: Mapped[list[Address]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    relations: Mapped[list[FamilyRelation]] = relationship(
        back_populates="person",
        foreign_keys="FamilyRelation.person_id",
        cascade="all, delete-orphan",
    )
    # الأسماء تُحلّ من سجل SQLAlchemy عند تهيئة المُخطِّطات، فلا حاجة للاستيراد.
    # foreign_keys إلزامي هنا لأن birth_records يرتبط بـ persons بثلاثة مفاتيح
    # (المولود، الأب، الأم) فلا يستطيع SQLAlchemy تخمين المقصود.
    birth_record: Mapped["BirthRecord | None"] = relationship(
        back_populates="person",
        foreign_keys="BirthRecord.person_id",
        uselist=False,
    )
    death_record: Mapped["DeathRecord | None"] = relationship(
        back_populates="person",
        foreign_keys="DeathRecord.person_id",
        uselist=False,
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="person", foreign_keys="Document.person_id"
    )

    # ------------------------------------------------------------------

    @property
    def full_name(self) -> str:
        """الاسم الرباعي كاملاً."""
        return (
            f"{self.first_name} {self.father_name} "
            f"{self.grandfather_name} {self.family_name}"
        )

    @property
    def age(self) -> int | None:
        """العمر بالسنوات — يُحسب حتى تاريخ الوفاة إن كان الشخص متوفى."""
        if self.birth_date is None:
            return None

        end = date.today()
        # الأشخاص المتوفون: العمر يتوقف عند الوفاة، لا يستمر بالزيادة
        if self.life_status == LifeStatus.DECEASED and self.death_record:
            end = self.death_record.death_date

        return end.year - self.birth_date.year - (
            (end.month, end.day) < (self.birth_date.month, self.birth_date.day)
        )

    @property
    def current_address(self) -> Address | None:
        """العنوان الحالي، أو None إن لم يُسجَّل عنوان."""
        return next(
            (a for a in self.addresses if a.is_current and a.deleted_at is None), None
        )

    def __repr__(self) -> str:
        return f"<Person {self.national_id} {self.full_name}>"


# ---------------------------------------------------------------------------
# ملء الاسم المطبَّع تلقائياً
# ---------------------------------------------------------------------------
#  في PostgreSQL يقوم بذلك مُشغّل (Trigger) في قاعدة البيانات.
#  هذا المستمع يضمن السلوك نفسه في SQLite، وفي حالة استخدام ORM قبل الحفظ
#  (مثلاً للبحث في الجلسة قبل الالتزام). النتيجة متطابقة في الحالتين.

def _fill_normalized_name(_mapper, _connection, target: Person) -> None:
    target.full_name_normalized = normalize_arabic(
        f"{target.first_name} {target.father_name} "
        f"{target.grandfather_name} {target.family_name}"
    )


event.listen(Person, "before_insert", _fill_normalized_name)
event.listen(Person, "before_update", _fill_normalized_name)


# ---------------------------------------------------------------------------
# العناوين
# ---------------------------------------------------------------------------

class Address(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """عنوان سكن — مع سجل تاريخي للتنقّلات."""

    __tablename__ = "addresses"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from", name="address_period"
        ),
        # عنوان حالي واحد فقط لكل شخص — فهرس جزئي يُفرض في PostgreSQL
        Index(
            "uq_address_current",
            "person_id",
            unique=True,
            postgresql_where=text("is_current AND deleted_at IS NULL"),
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    governorate_id: Mapped[int] = mapped_column(
        ForeignKey("governorates.id"), nullable=False, index=True
    )
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id"))
    subdistrict_id: Mapped[int | None] = mapped_column(ForeignKey("subdistricts.id"))

    quarter: Mapped[str | None] = mapped_column(String(100))       # المحلة
    street: Mapped[str | None] = mapped_column(String(100))        # الزقاق
    house_number: Mapped[str | None] = mapped_column(String(20))   # رقم الدار
    postal_code: Mapped[str | None] = mapped_column(String(10))
    details: Mapped[str | None] = mapped_column(Text)

    valid_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    valid_to: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    person: Mapped[Person] = relationship(back_populates="addresses")

    @property
    def formatted(self) -> str:
        """العنوان بصيغة نصّية عربية."""
        parts = [self.quarter, self.street, self.house_number]
        return " - ".join(p for p in parts if p) or "غير محدد"

    def __repr__(self) -> str:
        return f"<Address {self.formatted}>"


# ---------------------------------------------------------------------------
# العلاقات الأُسرية
# ---------------------------------------------------------------------------

class FamilyRelation(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """علاقة أُسرية بين شخصين.

    التخزين باتجاهين: عند إضافة «س أبٌ لـ ص» يُنشأ سجل مقابل «ص ابنٌ لـ س»،
    ما يجعل استعلام أقارب أي شخص عملية بحث في عمود واحد مفهرس.
    """

    __tablename__ = "family_relations"
    __table_args__ = (
        CheckConstraint("person_id <> related_person_id", name="no_self_relation"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name="relation_period"
        ),
        UniqueConstraint(
            "person_id", "related_person_id", "relation_type", name="uq_relation"
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    related_person_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    relation_type: Mapped[RelationType] = enum_column(RelationType, nullable=False)

    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))

    person: Mapped[Person] = relationship(
        back_populates="relations", foreign_keys=[person_id]
    )
    related_person: Mapped[Person] = relationship(foreign_keys=[related_person_id])

    def __repr__(self) -> str:
        return f"<FamilyRelation {self.relation_type.value}>"


# العلاقة العكسية لكل نوع — تُستخدم عند إنشاء السجل المقابل
INVERSE_RELATION: dict[tuple[RelationType, Gender], RelationType] = {
    (RelationType.FATHER, Gender.MALE): RelationType.SON,
    (RelationType.FATHER, Gender.FEMALE): RelationType.DAUGHTER,
    (RelationType.MOTHER, Gender.MALE): RelationType.SON,
    (RelationType.MOTHER, Gender.FEMALE): RelationType.DAUGHTER,
    (RelationType.HUSBAND, Gender.FEMALE): RelationType.WIFE,
    (RelationType.WIFE, Gender.MALE): RelationType.HUSBAND,
    (RelationType.BROTHER, Gender.MALE): RelationType.BROTHER,
    (RelationType.BROTHER, Gender.FEMALE): RelationType.SISTER,
    (RelationType.SISTER, Gender.MALE): RelationType.BROTHER,
    (RelationType.SISTER, Gender.FEMALE): RelationType.SISTER,
}
