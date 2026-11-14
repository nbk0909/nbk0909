"""نماذج التقسيمات الإدارية: المحافظة، القضاء، الناحية."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class Governorate(Base, TimestampMixin, SoftDeleteMixin):
    """المحافظة."""

    __tablename__ = "governorates"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name_en: Mapped[str | None] = mapped_column(String(100))

    districts: Mapped[list[District]] = relationship(
        back_populates="governorate", cascade="save-update"
    )

    def __repr__(self) -> str:
        return f"<Governorate {self.code} {self.name_ar}>"


class District(Base, TimestampMixin, SoftDeleteMixin):
    """القضاء / المنطقة."""

    __tablename__ = "districts"
    __table_args__ = (UniqueConstraint("governorate_id", "code", name="uq_district_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    governorate_id: Mapped[int] = mapped_column(
        ForeignKey("governorates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))

    governorate: Mapped[Governorate] = relationship(back_populates="districts")
    subdistricts: Mapped[list[Subdistrict]] = relationship(back_populates="district")

    def __repr__(self) -> str:
        return f"<District {self.name_ar}>"


class Subdistrict(Base, TimestampMixin, SoftDeleteMixin):
    """الناحية."""

    __tablename__ = "subdistricts"
    __table_args__ = (UniqueConstraint("district_id", "code", name="uq_subdistrict_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    district_id: Mapped[int] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)

    district: Mapped[District] = relationship(back_populates="subdistricts")

    def __repr__(self) -> str:
        return f"<Subdistrict {self.name_ar}>"
