from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.events import EventBus
from app.models.need import Need
from app.models.user import User
from app.schemas.need import NeedCreate, NeedResponse, NeedUpdate, SelectUsersRequest
from app.skills.registry import SkillRegistry


async def create_need(
    db: AsyncSession, user: User, data: NeedCreate, event_bus: EventBus | None = None
) -> NeedResponse:
    tag_skill = SkillRegistry.get("tag_extraction")
    tags_result = await tag_skill.execute({"text": data.description})
    tags = tags_result.get("tags", [])

    embed_skill = SkillRegistry.get("embedding")
    emb_result = await embed_skill.execute({"text": " ".join(tags)})

    need = Need(
        user_id=user.id,
        type=data.type,
        title=data.title,
        description=data.description,
        req_tags=tags,
        need_embedding=emb_result["embedding"],
        selection_mode=data.selection_mode,
    )

    db.add(need)
    await db.commit()
    await db.refresh(need)

    if event_bus:
        await event_bus.emit_background("need_published", {
            "need_id": need.id, "user_id": user.id, "type": data.type
        })

    resp = NeedResponse.model_validate(need)
    resp.username = user.username
    return resp


async def get_needs(
    db: AsyncSession, page: int = 1, page_size: int = 20,
    status: str | None = None, need_type: str | None = None,
    user_id: int | None = None,
) -> tuple[list[NeedResponse], int]:
    base = select(Need).options(selectinload(Need.user))
    count_query = select(Need)

    query = base
    if status:
        query = query.where(Need.status == status)
        count_query = count_query.where(Need.status == status)
    if need_type:
        query = query.where(Need.type == need_type)
        count_query = count_query.where(Need.type == need_type)
    if user_id is not None:
        query = query.where(Need.user_id == user_id)
        count_query = count_query.where(Need.user_id == user_id)

    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    query = query.order_by(Need.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    needs = result.unique().scalars().all()

    responses = []
    for n in needs:
        resp = NeedResponse.model_validate(n)
        resp.username = n.user.username if n.user else ""
        responses.append(resp)
    return responses, total


async def get_need_detail(db: AsyncSession, need_id: int) -> NeedResponse | None:
    result = await db.execute(
        select(Need).options(selectinload(Need.user)).where(Need.id == need_id)
    )
    need = result.unique().scalar_one_or_none()
    if need is None:
        return None
    resp = NeedResponse.model_validate(need)
    resp.username = need.user.username if need.user else ""
    return resp


async def update_need(
    db: AsyncSession, need: Need, data: NeedUpdate
) -> NeedResponse:
    if data.title is not None:
        need.title = data.title
    if data.description is not None:
        need.description = data.description
    if data.status is not None:
        need.status = data.status
    await db.commit()
    await db.refresh(need)
    resp = NeedResponse.model_validate(need)
    resp.username = need.user.username if need.user else ""
    return resp


async def delete_need(db: AsyncSession, need: Need) -> None:
    await db.delete(need)
    await db.commit()


async def select_users(
    db: AsyncSession, need: Need, data: SelectUsersRequest
) -> NeedResponse:
    """选择匹配用户（单选/多选）。多选追加，单选替换。"""
    if need.selection_mode == "single":
        need.selected_user_ids = data.user_ids[:1]
    else:
        existing = set(need.selected_user_ids or [])
        existing.update(data.user_ids)
        need.selected_user_ids = list(existing)

    # Auto-close if selection mode single (once someone is picked)
    if need.selection_mode == "single" and need.selected_user_ids:
        need.status = "已匹配"

    await db.commit()
    await db.refresh(need)
    resp = NeedResponse.model_validate(need)
    resp.username = need.user.username if need.user else ""
    return resp


async def deselect_user(
    db: AsyncSession, need: Need, user_id: int
) -> NeedResponse:
    """取消选择某个用户。"""
    existing = set(need.selected_user_ids or [])
    existing.discard(user_id)
    need.selected_user_ids = list(existing)
    if not need.selected_user_ids and need.status == "已匹配":
        need.status = "开放"
    await db.commit()
    await db.refresh(need)
    resp = NeedResponse.model_validate(need)
    resp.username = need.user.username if need.user else ""
    return resp


async def get_my_needs(
    db: AsyncSession, user_id: int,
) -> list[NeedResponse]:
    result = await db.execute(
        select(Need).options(selectinload(Need.user))
        .where(Need.user_id == user_id)
        .order_by(Need.created_at.desc())
    )
    needs = result.unique().scalars().all()
    responses = []
    for n in needs:
        resp = NeedResponse.model_validate(n)
        resp.username = n.user.username if n.user else ""
        responses.append(resp)
    return responses
