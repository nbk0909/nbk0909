"""نماذج قاعدة البيانات.

يجب استيراد كل النماذج هنا حتى تُسجَّل في Base.metadata، فيراها Alembic
عند توليد الترحيلات وتراها create_all عند إنشاء قاعدة اختبار.
"""

from app.database import Base
from app.models.audit import AuditLog
from app.models.document import Document
from app.models.enums import (
    AuditAction,
    BloodType,
    DocumentStatus,
    DocumentType,
    Gender,
    LifeStatus,
    MaritalStatus,
    RelationType,
    RequestStatus,
    RequestType,
)
from app.models.family import FamilyCard, FamilyCardMember
from app.models.location import District, Governorate, Subdistrict
from app.models.person import (
    INVERSE_RELATION,
    Address,
    FamilyRelation,
    Person,
)
from app.models.request import RequestAttachment, ServiceRequest
from app.models.user import (
    Permission,
    RefreshToken,
    Role,
    User,
    role_permissions,
    user_roles,
)
from app.models.vital import (
    BirthRecord,
    DeathRecord,
    DivorceRecord,
    MarriageContract,
)

__all__ = [
    "Base",
    # التقسيمات الإدارية
    "Governorate",
    "District",
    "Subdistrict",
    # المستخدمون والصلاحيات
    "User",
    "Role",
    "Permission",
    "RefreshToken",
    "role_permissions",
    "user_roles",
    # الأشخاص
    "Person",
    "Address",
    "FamilyRelation",
    "INVERSE_RELATION",
    # بطاقة العائلة
    "FamilyCard",
    "FamilyCardMember",
    # الواقعات
    "BirthRecord",
    "DeathRecord",
    "MarriageContract",
    "DivorceRecord",
    # الوثائق والمعاملات
    "Document",
    "ServiceRequest",
    "RequestAttachment",
    # التدقيق
    "AuditLog",
    # الأنواع المعدودة
    "Gender",
    "LifeStatus",
    "MaritalStatus",
    "BloodType",
    "RelationType",
    "DocumentType",
    "DocumentStatus",
    "RequestType",
    "RequestStatus",
    "AuditAction",
]
