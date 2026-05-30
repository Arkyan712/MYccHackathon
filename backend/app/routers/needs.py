from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.events import get_event_bus
from app.guardrails.rate_limiter import get_rate_limiter
from app.models.user import User
from sqlalchemy.orm import selectinload

from app.schemas.need import NeedCreate, NeedListResponse, NeedResponse, NeedUpdate, SelectUsersRequest
from app.schemas.match import FeedbackRequest
from app.services import need_service, match_engine

router = APIRouter(prefix="/api/needs", tags=["needs"])


@router.post("", response_model=NeedResponse)
async def create_need(
    data: NeedCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limiter = get_rate_limiter()
    if not limiter.check_ip(request.client.host if request.client else "unknown"):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    need = await need_service.create_need(db, user, data, get_event_bus())
    # 后台独立 session 执行匹配，避免父 session 关闭后访问
    import asyncio as _a
    _a.create_task(_run_matching_bg(need.id))
    return need


async def _run_matching_bg(need_id: int):
    from app.core.database import async_session
    from app.models.message import Message
    async with async_session() as bg_db:
        await match_engine.run_matching(bg_db, need_id, get_event_bus())
        # Send notification message
        from app.models.need import Need as _N
        from sqlalchemy import select as _s
        r = await bg_db.execute(_s(_N).where(_N.id == need_id))
        need = r.scalar_one_or_none()
        if need:
            matches_r = await match_engine.get_matches(bg_db, need_id)
            count = len(matches_r)
            bg_db.add(Message(
                need_id=need_id,
                sender_id=need.user_id,
                receiver_id=need.user_id,
                content=f"你的需求『{need.title}』匹配完成，共{count}位候选人，点击查看结果。",
                is_read=False,
            ))
            await bg_db.commit()


@router.get("", response_model=NeedListResponse)
async def list_needs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    type: str | None = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await need_service.get_needs(db, page, page_size, status, type)
    return NeedListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/mine", response_model=list[NeedResponse])
async def list_my_needs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await need_service.get_my_needs(db, user.id)


@router.get("/{need_id}", response_model=NeedResponse)
async def get_need(need_id: int, db: AsyncSession = Depends(get_db)):
    need = await need_service.get_need_detail(db, need_id)
    if need is None:
        raise HTTPException(404, "需求不存在")
    return need


@router.put("/{need_id}", response_model=NeedResponse)
async def update_need(
    need_id: int,
    data: NeedUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    need = await need_service.get_need_detail(db, need_id)
    if need is None:
        raise HTTPException(404, "需求不存在")
    if need.user_id != user.id:
        raise HTTPException(403, "只能编辑自己的需求")
    return await need_service.update_need(db, await _get_need_orm(db, need_id), data)


@router.delete("/{need_id}")
async def delete_need(
    need_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    need = await need_service.get_need_detail(db, need_id)
    if need is None:
        raise HTTPException(404, "需求不存在")
    if need.user_id != user.id:
        raise HTTPException(403, "只能删除自己的需求")
    orm_need = await _get_need_orm(db, need_id)
    await need_service.delete_need(db, orm_need)
    return {"ok": True}


@router.post("/{need_id}/close")
async def close_need(
    need_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    need = await need_service.get_need_detail(db, need_id)
    if need is None:
        raise HTTPException(404, "需求不存在")
    if need.user_id != user.id:
        raise HTTPException(403, "只能关闭自己的需求")
    orm_need = await _get_need_orm(db, need_id)
    return await need_service.update_need(db, orm_need, NeedUpdate(status="关闭"))


@router.post("/{need_id}/select", response_model=NeedResponse)
async def select_matched_users(
    need_id: int,
    data: SelectUsersRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    need_detail = await need_service.get_need_detail(db, need_id)
    if need_detail is None:
        raise HTTPException(404, "需求不存在")
    if need_detail.user_id != user.id:
        raise HTTPException(403, "只能为自己的需求选择匹配用户")
    orm_need = await _get_need_orm(db, need_id)
    return await need_service.select_users(db, orm_need, data)


@router.post("/{need_id}/deselect/{target_user_id}", response_model=NeedResponse)
async def deselect_matched_user(
    need_id: int,
    target_user_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    need_detail = await need_service.get_need_detail(db, need_id)
    if need_detail is None:
        raise HTTPException(404, "需求不存在")
    if need_detail.user_id != user.id:
        raise HTTPException(403, "只能为自己的需求取消选择")
    orm_need = await _get_need_orm(db, need_id)
    return await need_service.deselect_user(db, orm_need, target_user_id)


async def _get_need_orm(db: AsyncSession, need_id: int):
    """Get raw ORM Need object for mutations."""
    from sqlalchemy import select as _s
    from app.models.need import Need as _N
    r = await db.execute(_s(_N).options(selectinload(_N.user)).where(_N.id == need_id))
    return r.unique().scalar_one_or_none()


@router.get("/{need_id}/matches")
async def get_matches(
    need_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    need = await need_service.get_need_detail(db, need_id)
    if need is None:
        raise HTTPException(404, "需求不存在")
    if need.user_id != user.id:
        raise HTTPException(403, "只能查看自己需求的匹配结果")

    matches = await match_engine.get_matches(db, need_id)
    if not matches:
        # Fallback: run matching on demand
        await match_engine.run_matching(db, need_id, get_event_bus())
        matches = await match_engine.get_matches(db, need_id)

    return {"need": need.model_dump(), "matches": [m.model_dump() for m in matches]}


@router.get("/{need_id}/matches/stream")
async def stream_matches(need_id: int, token: str = Query(""), db: AsyncSession = Depends(get_db)):
    """SSE 流式匹配进度。支持 token 查询参数（EventSource 不支持自定义 header）。"""
    user_id = None
    if token:
        from app.core.security import decode_access_token
        payload = decode_access_token(token)
        if payload is None:
            raise HTTPException(401, "Invalid token")
        user_id = payload.get("user_id")

    need = await need_service.get_need_detail(db, need_id)
    if need is None:
        raise HTTPException(404, "需求不存在")
    if user_id is not None and need.user_id != user_id:
        raise HTTPException(403, "只能查看自己需求的匹配结果")

    return StreamingResponse(
        match_engine.run_matching_stream(db, need_id, get_event_bus()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{need_id}/matches/refresh")
async def refresh_matches(
    need_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    need = await need_service.get_need_detail(db, need_id)
    if need is None:
        raise HTTPException(404, "需求不存在")
    if need.user_id != user.id:
        raise HTTPException(403, "只能刷新自己需求的匹配结果")

    await match_engine.run_matching(db, need_id, get_event_bus())
    matches = await match_engine.get_matches(db, need_id)
    return {"need": need.model_dump(), "matches": [m.model_dump() for m in matches]}


@router.post("/matches/{match_id}/feedback")
async def submit_feedback(
    match_id: int,
    data: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await match_engine.record_feedback(db, match_id, data.feedback, get_event_bus())
    return {"ok": True}


@router.post("/{need_id}/refine")
async def refine_need(
    need_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ConciergeAgent: 分析需求并返回细化追问。"""
    need = await need_service.get_need_detail(db, need_id)
    if need is None:
        raise HTTPException(404, "需求不存在")
    result = await AgentOrchestrator.run_concierge(need.description, need.req_tags)
    return result


class ChatRequest(BaseModel):
    messages: list[dict] = []  # [{role, content}]


@router.post("/{need_id}/chat")
async def chat_with_concierge(
    need_id: int,
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """多轮对话：与 ConciergeAgent 聊天细化需求（含已匹配结果上下文）。"""
    need = await need_service.get_need_detail(db, need_id)
    if need is None:
        raise HTTPException(404, "需求不存在")
    if need.user_id != user.id:
        raise HTTPException(403, "只能对自己的需求进行AI对话")

    # Fetch existing matches for context
    from app.services.match_engine import get_matches
    match_list = await get_matches(db, need_id)
    match_dicts = [m.model_dump() for m in match_list] if match_list else []

    reply = await AgentOrchestrator.run_concierge_chat(
        need.description, need.req_tags or [], data.messages, match_dicts
    )
    return {"reply": reply}


class PolishRequest(BaseModel):
    need_type: str
    title: str
    description: str


class GenerateRequest(BaseModel):
    need_type: str
    title: str


@router.post("/polish")
async def polish_description(
    data: PolishRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 润色需求描述（含用户个性化上下文）。"""
    from app.adapters.deepseek_adapter import DeepSeekChatAdapter
    from app.integrations.client import get_ai_client
    from app.integrations.model_router import route
    from app.prompts.registry import PromptRegistry
    from app.services.user_context import build_user_context

    user_context = await build_user_context(db, user)

    client = get_ai_client()
    cfg = route("concierge")
    adapter = DeepSeekChatAdapter(client, model=cfg["model"])

    messages = PromptRegistry.render(
        "polish_description",
        {
            "user_context": user_context,
            "need_type": data.need_type,
            "title": data.title,
            "description": data.description,
        },
    )

    polished = await adapter.chat(messages, temperature=0.7, max_tokens=512)
    return {"result": polished}


@router.post("/generate")
async def generate_description(
    data: GenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 根据标题生成需求描述（含用户个性化上下文）。"""
    from app.adapters.deepseek_adapter import DeepSeekChatAdapter
    from app.integrations.client import get_ai_client
    from app.integrations.model_router import route
    from app.prompts.registry import PromptRegistry
    from app.services.user_context import build_user_context

    user_context = await build_user_context(db, user)

    client = get_ai_client()
    cfg = route("concierge")
    adapter = DeepSeekChatAdapter(client, model=cfg["model"])

    messages = PromptRegistry.render(
        "generate_description",
        {
            "user_context": user_context,
            "need_type": data.need_type,
            "title": data.title,
        },
    )

    generated = await adapter.chat(messages, temperature=0.8, max_tokens=512)
    return {"result": generated}


class BehaviorLogRequest(BaseModel):
    event_type: str
    target_user_id: int | None = None
    need_id: int | None = None


@router.post("/behavior/log")
async def log_behavior(
    data: BehaviorLogRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记录用户行为（查看匹配/点击联系等）。"""
    from app.models.behavior import UserBehaviorLog
    log = UserBehaviorLog(
        user_id=user.id,
        event_type=data.event_type,
        target_user_id=data.target_user_id,
        need_id=data.need_id,
    )
    db.add(log)
    await db.commit()

    # Check reflection threshold
    from app.services.reflection_service import check_and_reflect
    await check_and_reflect(db, user.id)

    return {"ok": True}
