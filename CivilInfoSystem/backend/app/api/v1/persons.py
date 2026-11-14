"""مسارات الأشخاص: الإنشاء والقراءة والتعديل والبحث وشجرة العائلة."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.deps import (
    DbSession,
    RequirePermission,
    enforce_governorate_scope,
)
from app.core.rate_limit import SEARCH_LIMIT, limiter
from app.models import Gender, LifeStatus, User
from app.schemas.common import MessageResponse, Page
from app.schemas.person import (
    AddressCreate,
    AddressRead,
    ConsistencyReport,
    FamilyTree,
    PersonCreate,
    PersonRead,
    PersonSearchResult,
    PersonSummary,
    PersonUpdate,
    RelationCreate,
    RelationRead,
)
from app.services import family as family_service
from app.services import persons as person_service
from app.services import search as search_service
from app.services.family import FamilyError
from app.services.persons import PersonError

router = APIRouter(prefix="/persons", tags=["الأشخاص"])


def _http_error(exc: PersonError | FamilyError) -> HTTPException:
    """يحوّل خطأ الخدمة إلى استجابة HTTP بالرمز المناسب."""
    status_map = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "duplicate_national_id": status.HTTP_409_CONFLICT,
        "duplicate_relation": status.HTTP_409_CONFLICT,
        "already_deleted": status.HTTP_409_CONFLICT,
        "has_dependents": status.HTTP_409_CONFLICT,
        "deceased_record": status.HTTP_409_CONFLICT,
    }
    return HTTPException(
        status_code=status_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"نجاح": False, "الرسالة": exc.message, "الرمز": exc.code},
    )


# ---------------------------------------------------------------------------
# البحث
# ---------------------------------------------------------------------------

@router.get(
    "/search",
    response_model=Page[PersonSearchResult],
    summary="البحث المتقدم عن الأشخاص",
)
@limiter.limit(SEARCH_LIMIT)
async def search_persons(
    request: Request,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.read"))],
    q: str | None = Query(None, description="نص حر: اسم أو رقم وطني أو رقم وثيقة"),
    national_id: str | None = Query(None, min_length=12, max_length=12),
    first_name: str | None = Query(None, description="الاسم الأول"),
    father_name: str | None = Query(None, description="اسم الأب"),
    family_name: str | None = Query(None, description="اللقب"),
    mother_name: str | None = Query(None, description="اسم الأم"),
    birth_date_from: str | None = Query(None, description="من تاريخ ميلاد"),
    birth_date_to: str | None = Query(None, description="إلى تاريخ ميلاد"),
    gender: Gender | None = Query(None),
    life_status: LifeStatus | None = Query(None),
    governorate_id: int | None = Query(None),
    fuzzy: bool = Query(True, description="السماح بالبحث التقريبي عند غياب النتائج"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[PersonSearchResult]:
    """يبحث عن الأشخاص بمعايير متعددة.

    يجرّب المطابقة التامة على الرقم الوطني أولاً، ثم المطابقة على الاسم
    المُطبَّع (تتجاهل التشكيل وصور الألف والتاء المربوطة)، ثم البحث التقريبي
    الذي يلتقط الأخطاء الإملائية.
    """
    from datetime import date as date_type

    def _parse(value: str | None) -> date_type | None:
        if not value:
            return None
        try:
            return date_type.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"نجاح": False, "الرسالة": f"تاريخ غير صالح: {value}"},
            ) from exc

    criteria = search_service.SearchCriteria(
        query=q,
        national_id=national_id,
        first_name=first_name,
        father_name=father_name,
        family_name=family_name,
        mother_name=mother_name,
        birth_date_from=_parse(birth_date_from),
        birth_date_to=_parse(birth_date_to),
        gender=gender,
        life_status=life_status,
        governorate_id=governorate_id,
        fuzzy=fuzzy,
    )

    if criteria.is_empty():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "نجاح": False,
                "الرسالة": "حدّد معياراً واحداً على الأقل للبحث",
            },
        )

    outcome = search_service.search_persons(
        db, criteria, limit=page_size, offset=(page - 1) * page_size
    )

    items = []
    for person in outcome.persons:
        result = PersonSearchResult.model_validate(person)
        result.similarity = outcome.similarities.get(str(person.id))
        items.append(result)

    return Page[PersonSearchResult](
        items=items, total=outcome.total, page=page, page_size=page_size
    )


@router.get(
    "/suggest",
    response_model=list[str],
    summary="اقتراح أسماء للإكمال التلقائي",
)
@limiter.limit(SEARCH_LIMIT)
async def suggest(
    request: Request,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.read"))],
    prefix: str = Query(..., min_length=2, description="بداية الاسم"),
) -> list[str]:
    """يقترح أسماء تبدأ بالبادئة المعطاة."""
    return search_service.suggest_names(db, prefix)


# ---------------------------------------------------------------------------
# القراءة
# ---------------------------------------------------------------------------

@router.get(
    "/by-national-id/{national_id}",
    response_model=PersonRead,
    summary="جلب شخص بالرقم الوطني",
)
async def get_by_national_id(
    national_id: str,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.read"))],
) -> PersonRead:
    """يجلب سجل شخص بالرقم الوطني."""
    try:
        person = person_service.get_by_national_id(db, national_id)
    except PersonError as exc:
        raise _http_error(exc) from exc

    return _to_read(person)


@router.get("/{person_id}", response_model=PersonRead, summary="جلب سجل شخص")
async def get_person(
    person_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.read"))],
) -> PersonRead:
    """يجلب سجل شخص بمعرّفه."""
    try:
        person = person_service.get_person(db, person_id)
    except PersonError as exc:
        raise _http_error(exc) from exc

    return _to_read(person)


def _to_read(person) -> PersonRead:
    """يبني استجابة الشخص مع عنوانه الحالي."""
    data = PersonRead.model_validate(person)
    current = person.current_address
    if current is not None:
        data.current_address = AddressRead.model_validate(current)
    return data


# ---------------------------------------------------------------------------
# الإنشاء والتعديل
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=PersonRead,
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل شخص جديد",
)
async def create_person(
    request: Request,
    payload: PersonCreate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.create"))],
) -> PersonRead:
    """ينشئ سجل شخص جديداً مع عنوانه الاختياري."""
    data = payload.model_dump(exclude={"address"})
    address = payload.address.model_dump() if payload.address else None

    if address:
        enforce_governorate_scope(user, address["governorate_id"])

    try:
        person = person_service.create_person(
            db, data=data, address=address, user=user, request=request
        )
    except PersonError as exc:
        raise _http_error(exc) from exc

    return _to_read(person)


@router.patch("/{person_id}", response_model=PersonRead, summary="تعديل بيانات شخص")
async def update_person(
    request: Request,
    person_id: uuid.UUID,
    payload: PersonUpdate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.update"))],
) -> PersonRead:
    """يعدّل بيانات شخص ويقيّد ما تغيّر في سجل التدقيق."""
    try:
        person = person_service.get_person(db, person_id)
        enforce_governorate_scope(user, person.birth_governorate_id)
        person = person_service.update_person(
            db,
            person=person,
            changes=payload.model_dump(exclude_unset=True),
            user=user,
            request=request,
        )
    except PersonError as exc:
        raise _http_error(exc) from exc

    return _to_read(person)


@router.post(
    "/{person_id}/address",
    response_model=AddressRead,
    summary="تسجيل انتقال إلى عنوان جديد",
)
async def change_address(
    request: Request,
    person_id: uuid.UUID,
    payload: AddressCreate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.update"))],
) -> AddressRead:
    """يسجّل عنواناً جديداً ويُغلق السابق دون حذفه."""
    enforce_governorate_scope(user, payload.governorate_id)

    try:
        person = person_service.get_person(db, person_id)
        address = person_service.change_address(
            db,
            person=person,
            address=payload.model_dump(),
            user=user,
            request=request,
        )
    except PersonError as exc:
        raise _http_error(exc) from exc

    return AddressRead.model_validate(address)


@router.get(
    "/{person_id}/addresses",
    response_model=list[AddressRead],
    summary="سجل تنقّلات السكن",
)
async def address_history(
    person_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.read"))],
) -> list[AddressRead]:
    """يُرجع كل عناوين الشخص مرتّبةً من الأحدث إلى الأقدم."""
    try:
        person = person_service.get_person(db, person_id)
    except PersonError as exc:
        raise _http_error(exc) from exc

    addresses = sorted(
        (a for a in person.addresses if a.deleted_at is None),
        key=lambda a: a.valid_from,
        reverse=True,
    )
    return [AddressRead.model_validate(a) for a in addresses]


@router.delete(
    "/{person_id}",
    response_model=MessageResponse,
    summary="حذف سجل شخص (حذف منطقي)",
)
async def delete_person(
    request: Request,
    person_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.delete"))],
    reason: str = Query(..., min_length=5, description="سبب الحذف — إلزامي"),
) -> MessageResponse:
    """يحذف السجل حذفاً منطقياً.

    لا يُحذف أي سجل مدني حذفاً فعلياً، ويُمنع الحذف إن كان السجل مرتبطاً
    بواقعات أو أبناء.
    """
    try:
        person = person_service.get_person(db, person_id)
        person_service.soft_delete_person(
            db, person=person, reason=reason, user=user, request=request
        )
    except PersonError as exc:
        raise _http_error(exc) from exc

    return MessageResponse(الرسالة="تم حذف السجل حذفاً منطقياً")


@router.post(
    "/{person_id}/restore",
    response_model=PersonRead,
    summary="استعادة سجل محذوف",
)
async def restore_person(
    request: Request,
    person_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.delete"))],
) -> PersonRead:
    """يستعيد سجلاً محذوفاً منطقياً."""
    try:
        person = person_service.restore_person(
            db, person_id=person_id, user=user, request=request
        )
    except PersonError as exc:
        raise _http_error(exc) from exc

    return _to_read(person)


# ---------------------------------------------------------------------------
# العلاقات وشجرة العائلة
# ---------------------------------------------------------------------------

@router.get(
    "/{person_id}/relations",
    response_model=list[RelationRead],
    summary="علاقات الشخص الأُسرية",
)
async def list_relations(
    person_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.read"))],
    active_only: bool = Query(True, description="العلاقات النشطة فقط"),
) -> list[RelationRead]:
    """يُرجع علاقات الشخص الأُسرية."""
    try:
        person_service.get_person(db, person_id)
    except PersonError as exc:
        raise _http_error(exc) from exc

    relations = family_service.get_relations(db, person_id, active_only=active_only)
    return [RelationRead.model_validate(r) for r in relations]


@router.post(
    "/{person_id}/relations",
    response_model=RelationRead,
    status_code=status.HTTP_201_CREATED,
    summary="إضافة علاقة أُسرية",
)
async def add_relation(
    request: Request,
    person_id: uuid.UUID,
    payload: RelationCreate,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.update"))],
) -> RelationRead:
    """يضيف علاقة أُسرية مع نظيرتها العكسية بعد فحص التعارضات المنطقية."""
    try:
        person = person_service.get_person(db, person_id)
        related = person_service.get_person(db, payload.related_person_id)
        relation = family_service.add_relation(
            db,
            person=person,
            related_person=related,
            relation_type=payload.relation_type,
            start_date=payload.start_date,
            user=user,
            request=request,
        )
    except (PersonError, FamilyError) as exc:
        raise _http_error(exc) from exc

    return RelationRead.model_validate(relation)


@router.get(
    "/{person_id}/family-tree",
    response_model=FamilyTree,
    summary="شجرة العائلة حتى ثلاثة أجيال",
)
async def family_tree(
    person_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.read"))],
) -> FamilyTree:
    """يبني شجرة عائلة الشخص: الأجداد والوالدان والإخوة والأزواج والأبناء والأحفاد."""
    try:
        person = person_service.get_person(db, person_id)
    except PersonError as exc:
        raise _http_error(exc) from exc

    return FamilyTree.model_validate(family_service.build_family_tree(db, person))


@router.get(
    "/{person_id}/consistency",
    response_model=ConsistencyReport,
    summary="فحص تماسك العلاقات الأُسرية",
)
async def check_consistency(
    person_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(RequirePermission("persons.read"))],
) -> ConsistencyReport:
    """يكشف التعارضات المنطقية: تعدّد الوالدين، والفوارق العمرية المستحيلة،
    والجنس المخالف لنوع العلاقة، والزوجية النشطة مع متوفى."""
    try:
        person_service.get_person(db, person_id)
    except PersonError as exc:
        raise _http_error(exc) from exc

    conflicts = family_service.check_consistency(db, person_id)

    return ConsistencyReport(
        سليم=not conflicts,
        عدد_التعارضات=len(conflicts),
        التعارضات=conflicts,
    )
