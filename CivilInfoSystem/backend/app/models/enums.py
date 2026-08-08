"""الأنواع المعدودة — قيمها بالعربية لتطابق أنواع ENUM في مخطط PostgreSQL.

أسماء الأعضاء بالإنجليزية (لأنها معرّفات بايثون)، وقيمها بالعربية لأنها
هي ما يُخزَّن في قاعدة البيانات ويُعرض للمستخدم.
"""

from __future__ import annotations

import enum


class Gender(str, enum.Enum):
    """الجنس."""

    MALE = "ذكر"
    FEMALE = "أنثى"


class LifeStatus(str, enum.Enum):
    """حالة الحياة."""

    ALIVE = "حي"
    DECEASED = "متوفى"
    MISSING = "مفقود"


class MaritalStatus(str, enum.Enum):
    """الحالة الاجتماعية."""

    SINGLE = "أعزب"
    MARRIED = "متزوج"
    DIVORCED = "مطلق"
    WIDOWED = "أرمل"


class BloodType(str, enum.Enum):
    """فصيلة الدم."""

    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


class RelationType(str, enum.Enum):
    """نوع العلاقة الأُسرية."""

    FATHER = "أب"
    MOTHER = "أم"
    SON = "ابن"
    DAUGHTER = "ابنة"
    HUSBAND = "زوج"
    WIFE = "زوجة"
    BROTHER = "أخ"
    SISTER = "أخت"


class DocumentType(str, enum.Enum):
    """نوع الوثيقة."""

    NATIONAL_CARD = "بطاقة وطنية"
    PASSPORT = "جواز سفر"
    CITIZENSHIP = "شهادة جنسية"
    FAMILY_CARD = "بطاقة عائلية"


class DocumentStatus(str, enum.Enum):
    """حالة الوثيقة."""

    VALID = "سارية"
    EXPIRED = "منتهية"
    LOST = "مفقودة"
    REPLACEMENT = "بدل فاقد"
    CANCELLED = "ملغاة"


class RequestType(str, enum.Enum):
    """نوع المعاملة."""

    ISSUE = "إصدار"
    AMEND = "تعديل"
    REPLACEMENT = "بدل ضائع"
    RENEW = "تجديد"
    CANCEL = "إلغاء"


class RequestStatus(str, enum.Enum):
    """حالة المعاملة."""

    SUBMITTED = "مقدَّم"
    UNDER_REVIEW = "قيد المراجعة"
    APPROVED = "مقبول"
    REJECTED = "مرفوض"
    CANCELLED = "ملغى"


class AuditAction(str, enum.Enum):
    """نوع العملية في سجل التدقيق."""

    CREATE = "إنشاء"
    READ = "قراءة"
    UPDATE = "تعديل"
    DELETE = "حذف"
    APPROVE = "اعتماد"
    LOGIN = "دخول"
    LOGOUT = "خروج"
    FAILED_ATTEMPT = "محاولة فاشلة"


# ---------------------------------------------------------------------------
# ربط الأنواع بأسماء ENUM في PostgreSQL
# ---------------------------------------------------------------------------
#  أسماء الأنواع هنا يجب أن تطابق ما في database/schema.sql حرفياً،
#  وإلا أنشأ SQLAlchemy نوعاً ثانياً مكرراً عند الترحيل.

ENUM_TYPE_NAMES: dict[type[enum.Enum], str] = {
    Gender: "gender_enum",
    LifeStatus: "life_status_enum",
    MaritalStatus: "marital_status_enum",
    BloodType: "blood_type_enum",
    RelationType: "relation_type_enum",
    DocumentType: "document_type_enum",
    DocumentStatus: "document_status_enum",
    RequestType: "request_type_enum",
    RequestStatus: "request_status_enum",
    AuditAction: "audit_action_enum",
}
