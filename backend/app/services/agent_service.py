"""Agent 会话/消息/任务/文件 CRUD。"""

import os

from sqlalchemy import delete, desc, select as _s
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentFile, AgentMessage, AgentSession, AgentTask
from app.models.user import User


# ── Session ──

async def create_session(db: AsyncSession, user: User, title: str = "新对话") -> AgentSession:
    s = AgentSession(user_id=user.id, title=title)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def get_session(db: AsyncSession, session_id: int) -> AgentSession | None:
    r = await db.execute(_s(AgentSession).where(AgentSession.id == session_id))
    return r.scalar_one_or_none()


async def list_sessions(db: AsyncSession, user_id: int) -> list[AgentSession]:
    r = await db.execute(
        _s(AgentSession).where(AgentSession.user_id == user_id)
        .order_by(desc(AgentSession.updated_at))
    )
    return list(r.scalars().all())


async def delete_session(db: AsyncSession, session_id: int) -> None:
    """删除会话及其所有关联数据。"""
    # Break self-referencing FK first, then cascade
    from sqlalchemy import update
    await db.execute(update(AgentTask).where(AgentTask.session_id == session_id).values(parent_task_id=None))
    await db.flush()
    await db.execute(delete(AgentTask).where(AgentTask.session_id == session_id))
    await db.execute(delete(AgentMessage).where(AgentMessage.session_id == session_id))
    await db.execute(delete(AgentFile).where(AgentFile.session_id == session_id))
    await db.execute(delete(AgentSession).where(AgentSession.id == session_id))
    await db.commit()


# ── Messages ──

async def add_message(
    db: AsyncSession, session_id: int, role: str, content: str,
    token_count: int | None = None, extra_metadata: dict | None = None,
) -> AgentMessage:
    m = AgentMessage(session_id=session_id, role=role, content=content, token_count=token_count, extra_metadata=extra_metadata)
    db.add(m)
    await db.commit()
    await db.refresh(m)
    # touch session
    r = await db.execute(_s(AgentSession).where(AgentSession.id == session_id))
    s = r.scalar_one_or_none()
    if s:
        s.updated_at = m.created_at
        await db.commit()
    return m


async def get_messages(db: AsyncSession, session_id: int, limit: int = 50) -> list[AgentMessage]:
    r = await db.execute(
        _s(AgentMessage).where(AgentMessage.session_id == session_id)
        .order_by(desc(AgentMessage.created_at), desc(AgentMessage.id)).limit(limit)
    )
    messages = list(r.scalars().all())
    messages.reverse()
    return messages


async def get_recent_messages(db: AsyncSession, session_id: int, limit: int = 10) -> list[AgentMessage]:
    return await get_messages(db, session_id, limit)


async def count_messages(db: AsyncSession, session_id: int) -> int:
    from sqlalchemy import func
    r = await db.execute(
        _s(func.count()).select_from(AgentMessage).where(AgentMessage.session_id == session_id)
    )
    return r.scalar() or 0


# ── Tasks ──

async def create_task(
    db: AsyncSession, session_id: int, goal: str,
    parent_id: int | None = None, agent: str = "",
) -> AgentTask:
    t = AgentTask(session_id=session_id, parent_task_id=parent_id, goal=goal, assigned_agent=agent)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def update_task(db: AsyncSession, task_id: int, status: str, result: dict | None = None, error: str | None = None) -> AgentTask | None:
    r = await db.execute(_s(AgentTask).where(AgentTask.id == task_id))
    t = r.scalar_one_or_none()
    if t:
        t.status = status
        if result is not None:
            t.result = result
        if error is not None:
            t.error = error
        await db.commit()
        await db.refresh(t)
    return t


async def get_tasks(db: AsyncSession, session_id: int) -> list[AgentTask]:
    r = await db.execute(
        _s(AgentTask).where(AgentTask.session_id == session_id).order_by(AgentTask.created_at)
    )
    return list(r.scalars().all())


# ── Files ──

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _write_file(filepath: str, data: bytes) -> None:
    with open(filepath, "wb") as fh:
        fh.write(data)


async def save_file(
    db: AsyncSession, session_id: int, filename: str,
    file_type: str, content_text: str, raw_bytes: bytes,
) -> AgentFile:
    # Save to disk (non-blocking via executor)
    import asyncio
    filepath = os.path.join(UPLOAD_DIR, f"{session_id}_{filename}")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _write_file, filepath, raw_bytes)

    f = AgentFile(session_id=session_id, filename=filename, file_type=file_type, content_text=content_text)
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


async def get_file(db: AsyncSession, file_id: int) -> AgentFile | None:
    r = await db.execute(_s(AgentFile).where(AgentFile.id == file_id))
    return r.scalar_one_or_none()


async def update_file_info(
    db: AsyncSession, file_id: int, extracted_info: dict | None = None,
    embedding: list | None = None,
) -> AgentFile | None:
    r = await db.execute(_s(AgentFile).where(AgentFile.id == file_id))
    f = r.scalar_one_or_none()
    if f:
        if extracted_info:
            f.extracted_info = extracted_info
        if embedding:
            f.embedding = embedding
        await db.commit()
        await db.refresh(f)
    return f
