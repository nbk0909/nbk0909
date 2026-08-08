"""أنواع أعمدة تعمل على PostgreSQL و SQLite معاً.

PostgreSQL يملك أنواعاً متخصّصة (UUID, JSONB, INET) لا وجود لها في SQLite.
هذه المحوّلات تختار النوع الأصلي عند توفّره، وتتراجع إلى نوع نصّي مكافئ
في SQLite، فيبقى الكود واحداً في البيئتين.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CHAR, JSON, String
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """معرّف فريد عالمي: UUID أصلي في PostgreSQL، ونص من 36 حرفاً في SQLite."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect) -> Any:
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return value if dialect.name == "postgresql" else str(value)

    def process_result_value(self, value: Any, dialect) -> uuid.UUID | None:
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class JSONType(TypeDecorator):
    """بيانات JSON: JSONB في PostgreSQL (مفهرس وسريع)، وJSON نصّي في SQLite.

    none_as_null يجعل القيمة None تُخزَّن NULL حقيقياً لا قيمة JSON نصّية
    ('null')، وإلا فشلت استعلامات ‎IS NULL‎ على الأعمدة الفارغة.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB(none_as_null=True))
        return dialect.type_descriptor(JSON(none_as_null=True))


class IPAddress(TypeDecorator):
    """عنوان IP: نوع INET في PostgreSQL، ونص في SQLite."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(INET())
        return dialect.type_descriptor(String(45))  # يكفي لعناوين IPv6

    def process_bind_param(self, value: Any, dialect) -> Any:
        return str(value) if value is not None else None
