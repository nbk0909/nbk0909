"""نماذج بطاقة العائلة (دفتر العائلة)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
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
from app.models.enums import RelationType
from app.models.person import Person
from app.models.types import GUID


class FamilyCard(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """بطاقة العائلة — تجمع رب الأسرة وتابعيه."""

    __tablename__ = "family_cards"

    card_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    head_person_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    governorate_id: Mapped[int] = mapped_column(
        ForeignKey("governorates.id"), nullable=False
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    issuing_office: Mapped[str | None] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    head: Mapped[Person] = relationship(foreign_keys=[head_person_id])
    members: Mapped[list[FamilyCardMember]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )

    @property
    def active_member_count(self) -> int:
        """عدد الأفراد المسجّلين حالياً في البطاقة."""
        return sum(1 for m in self.members if m.removed_at is None)

    def __repr__(self) -> str:
        return f"<FamilyCard {self.card_number}>"


class FamilyCardMember(Base, UUIDPrimaryKeyMixin):
    """فرد مسجّل في بطاقة عائلة."""

    __tablename__ = "family_card_members"
    __table_args__ = (
        UniqueConstraint("family_card_id", "person_id", name="uq_card_member"),
        # الشخص لا ينتمي لأكثر من بطاقة عائلة نشطة في آن واحد: عند الزواج
        # يُرفع الابن/الابنة من بطاقة الأب ويُقيَّد في بطاقة الأسرة الجديدة.
        # فهرس جزئي — يُفرض في PostgreSQL فقط، وSQLite لا يدعم شرط WHERE هنا،
        # فتتكفّل طبقة الخدمات بالتحقق في بيئة التطوير.
        Index(
            "uq_person_active_card",
            "person_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
    )

    family_card_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("family_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    relation_to_head: Mapped[RelationType] = enum_column(RelationType, nullable=False)

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    card: Mapped[FamilyCard] = relationship(back_populates="members")
    person: Mapped[Person] = relationship()

    def __repr__(self) -> str:
        return f"<FamilyCardMember {self.relation_to_head.value}>"
