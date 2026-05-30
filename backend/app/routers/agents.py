"""Agent page APIs: sessions, upload, chat, planning, publish, and suggestions."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.events import get_event_bus
from app.models.user import User
from app.schemas.agent import (
    ChatRequest,
    ConfirmPublishRequest,
    PlanRequest,
    SearchKnowledgeRequest,
    SessionCreate,
)
from app.services import agent_memory, agent_planner, agent_service

router = APIRouter(prefix="/api/agent", tags=["agent"])


async def ensure_session_owner(db: AsyncSession, session_id: int, user_id: int):
    session = await agent_service.get_session(db, session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(404, "会话不存在")
    return session


@router.post("/sessions")
async def create_session(
    data: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await agent_service.create_session(db, user, data.title)
    return {"id": s.id, "title": s.title, "status": s.status, "created_at": str(s.created_at)}


@router.get("/sessions")
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sessions = await agent_service.list_sessions(db, user.id)
    return [
        {
            "id": s.id,
            "title": s.title,
            "status": s.status,
            "summary": s.summary[:100] if s.summary else None,
            "created_at": str(s.created_at),
            "updated_at": str(s.updated_at),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await ensure_session_owner(db, session_id, user.id)
    messages = await agent_service.get_messages(db, session_id)
    tasks = await agent_service.get_tasks(db, session_id)
    return {
        "session": {
            "id": s.id,
            "title": s.title,
            "summary": s.summary,
            "planning_state": s.planning_state,
            "status": s.status,
            "user_id": s.user_id,
            "created_at": str(s.created_at),
            "updated_at": str(s.updated_at),
        },
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "extra_metadata": m.extra_metadata,
                "created_at": str(m.created_at),
            }
            for m in messages
        ],
        "tasks": [
            {
                "id": t.id,
                "goal": t.goal,
                "status": t.status,
                "assigned_agent": t.assigned_agent,
                "parent_task_id": t.parent_task_id,
                "result": t.result,
            }
            for t in tasks
        ],
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_session_owner(db, session_id, user.id)
    await agent_service.delete_session(db, session_id)
    return {"ok": True}


@router.post("/sessions/{session_id}/chat")
async def chat(
    session_id: int,
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_session_owner(db, session_id, user.id)
    result = await agent_planner.handle_chat_message(
        db, session_id, data.message, user, get_event_bus(),
    )
    return {"reply": result["reply"], "intent": result.get("intent"), "drafts": result.get("drafts")}


@router.post("/sessions/{session_id}/upload")
async def upload_file(
    session_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_session_owner(db, session_id, user.id)

    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    if ext not in ("txt", "docx", "pdf"):
        raise HTTPException(400, "仅支持 txt、docx、pdf 文件")

    raw_bytes = await file.read()
    if len(raw_bytes) > 5 * 1024 * 1024:
        raise HTTPException(400, "文件不能超过5MB")

    result = await agent_planner.handle_file_upload(
        db, session_id, raw_bytes, filename, ext, user, get_event_bus(),
    )
    return result


@router.post("/sessions/{session_id}/plan")
async def trigger_plan(
    session_id: int,
    data: PlanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_session_owner(db, session_id, user.id)
    return await agent_planner.handle_plan(db, session_id, data.goal, user, get_event_bus())


@router.post("/sessions/{session_id}/confirm-publish")
async def confirm_publish(
    session_id: int,
    data: ConfirmPublishRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_session_owner(db, session_id, user.id)

    drafts = []
    if data.draft is None:
        raise HTTPException(400, "请提供需求草稿")
    raw = data.draft
    if isinstance(raw, list):
        drafts = [d.model_dump() if hasattr(d, "model_dump") else d for d in raw]
    elif hasattr(raw, "model_dump"):
        drafts = [raw.model_dump()]
    elif isinstance(raw, dict):
        drafts = [raw]

    return await agent_planner.handle_confirm_publish(db, session_id, drafts, user, get_event_bus())


@router.get("/sessions/{session_id}/tasks")
async def get_tasks(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_session_owner(db, session_id, user.id)
    tasks = await agent_service.get_tasks(db, session_id)
    return [
        {
            "id": t.id,
            "goal": t.goal,
            "status": t.status,
            "assigned_agent": t.assigned_agent,
            "parent_task_id": t.parent_task_id,
            "result": t.result,
        }
        for t in tasks
    ]


@router.post("/search-knowledge")
async def search_knowledge(
    data: SearchKnowledgeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = agent_memory.ContextManager(db)
    results = await ctx.search_knowledge(user.id, data.query)
    return {"results": results}


@router.get("/suggestions/{session_id}")
async def get_suggestions(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_session_owner(db, session_id, user.id)

    from app.models.need import Need
    from sqlalchemy import select as _s

    r = await db.execute(_s(Need).where(Need.user_id == user.id, Need.status == "开放"))
    active_needs = r.scalars().all()
    suggestions = [
        f"需求《{n.title}》仍在开放中，需要我帮你查看匹配结果或调整条件吗？"
        for n in active_needs[:3]
    ]
    return {"suggestions": suggestions}


@router.post("/draft-message")
async def draft_message(
    data: dict,
    user: User = Depends(get_current_user),
):
    msg = await agent_planner.handle_draft_message(
        need_title=data.get("need_title", ""),
        match_name=data.get("match_name", ""),
        match_skills=data.get("match_skills", []),
        match_reason=data.get("match_reason", ""),
        user_name=user.username,
    )
    return {"message": msg}
