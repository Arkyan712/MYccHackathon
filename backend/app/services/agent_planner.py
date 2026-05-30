"""Agent 规划执行器: 编排父Agent调度子Agent执行任务链。"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.file_reader_agent import FileReaderAgent
from app.agents.intent_analyzer_agent import IntentAnalyzerAgent
from app.agents.need_creator_agent import NeedCreatorAgent
from app.agents.match_watcher_agent import MatchWatcherAgent
from app.agents.planner_agent import PlannerAgent
from app.models.user import User
from app.services import agent_service, agent_memory
from app.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


async def handle_chat_message(
    db: AsyncSession, session_id: int, message: str, user: User,
    event_bus=None,
) -> dict:
    """处理用户消息，返回 AI 回复和动作。"""
    # Save user message
    await agent_service.add_message(db, session_id, "user", message)

    # Build context
    ctx_mgr = agent_memory.ContextManager(db)
    ctx = await ctx_mgr.get_chat_context(session_id)
    user_context = await ctx_mgr.load_user_memory(user.id)

    # Analyze intent
    intent_agent = IntentAnalyzerAgent()
    intent_result = await intent_agent.execute({
        "message": message, "user_context": user_context,
    })

    intent = intent_result.get("intent", "chat")

    # If file was uploaded recently, check and process
    file_info = ""
    if ctx.get("file_context") and ctx["file_context"] != "（无上传文件）":
        file_info = ctx["file_context"]

    # Generate AI reply using agent_chat prompt
    from app.adapters.deepseek_adapter import DeepSeekChatAdapter
    from app.integrations.client import get_ai_client
    from app.integrations.model_router import route
    from app.prompts.registry import PromptRegistry

    client = get_ai_client()
    cfg = route("agent_chat")
    adapter = DeepSeekChatAdapter(client, model=cfg["model"])

    chat_messages = PromptRegistry.render("agent_chat", {
        "user_context": user_context[:500],
        "session_summary": ctx["session_summary"],
        "file_context": file_info,
        "history": ctx["history"][-1500:],
        "message": message,
    })

    reply = await adapter.chat(chat_messages, temperature=cfg["temperature"], max_tokens=cfg["max_tokens"])

    # Save assistant message
    await agent_service.add_message(db, session_id, "assistant", reply)

    # If intent is publish_need and files exist, load actual extracted_info
    drafts = None
    if intent == "publish_need":
        # Load actual extracted_info from latest file
        extracted = {}
        from app.models.agent import AgentFile
        from sqlalchemy import select as _s, desc
        fr = await db.execute(
            _s(AgentFile).where(AgentFile.session_id == session_id)
            .order_by(desc(AgentFile.created_at)).limit(1)
        )
        latest_file = fr.scalar_one_or_none()
        if latest_file and latest_file.extracted_info:
            extracted = latest_file.extracted_info

        if extracted:
            creator = NeedCreatorAgent()
            draft_result = await creator.execute({
                "extracted_info": extracted,
                "user": user, "db": db,
            })
            drafts = draft_result.get("drafts")

    return {
        "reply": reply,
        "intent": intent,
        "drafts": drafts,
    }


async def handle_file_upload(
    db: AsyncSession, session_id: int, file_bytes: bytes,
    filename: str, file_type: str, user: User, event_bus=None,
) -> dict:
    """处理文件上传：保存 → 提取文本 → AI分析。"""
    # Extract text
    content_text = _extract_text(file_bytes, filename, file_type)

    # Save file
    af = await agent_service.save_file(db, session_id, filename, file_type, content_text, file_bytes)

    # Generate embedding for knowledge memory
    try:
        embed_skill = SkillRegistry.get("embedding")
        emb_result = await embed_skill.execute({"text": content_text[:2000]})
        af.embedding = emb_result["embedding"]
    except Exception:
        logger.exception("File embedding failed")

    # AI analysis
    reader = FileReaderAgent()
    result = await reader.execute({"file_id": af.id, "db": db}, {"event_bus": event_bus})
    extracted = result.get("extracted", {})

    await agent_service.update_file_info(db, af.id, extracted_info=extracted)

    drafts = None
    if extracted and (extracted.get("potential_needs") or extracted.get("summary")):
        try:
            creator = NeedCreatorAgent()
            draft_result = await creator.execute({
                "extracted_info": extracted,
                "user": user,
                "db": db,
            })
            drafts = draft_result.get("drafts")
        except Exception:
            logger.exception("Need draft generation after upload failed")

    # Build response
    if extracted and extracted.get("summary"):
        ai_msg = (
            f"我分析了文件「{filename}」，主要内容是：\n\n"
            f"**{extracted.get('title', '')}**\n"
            f"{extracted.get('summary', '')[:300]}\n"
        )
        if extracted.get("skills_needed"):
            ai_msg += f"\n所需技能：{', '.join(extracted['skills_needed'])}"
        if extracted.get("deadline"):
            ai_msg += f"\n截止日期：{extracted['deadline']}"
        if extracted.get("potential_needs"):
            ai_msg += "\n\n我发现可以发布以下需求，需要我帮你创建吗？"
            for n in extracted["potential_needs"][:3]:
                ai_msg += f"\n- [{n.get('type','')}] {n.get('title','')}"
    else:
        ai_msg = f"已收到文件「{filename}」（{file_type}），但未能自动提取关键信息。你可以告诉我文件的核心内容，我来帮你分析。"

    await agent_service.add_message(
        db,
        session_id,
        "assistant",
        ai_msg,
        extra_metadata={"type": "file_analysis", "drafts": drafts} if drafts else {"type": "file_analysis"},
    )

    return {"reply": ai_msg, "file_id": af.id, "extracted": extracted, "drafts": drafts}


async def handle_plan(
    db: AsyncSession, session_id: int, goal: str, user: User, event_bus=None,
) -> dict:
    """触发PlannerAgent进行任务规划。"""
    planner = PlannerAgent()
    result = await planner.execute({"goal": goal, "session_id": session_id, "db": db, "user": user})

    tasks = result.get("plan", [])
    plan_msg = f"已为「{goal}」制定执行计划：\n"
    for i, t in enumerate(tasks):
        g = t.get("goal", t) if isinstance(t, dict) else str(t)
        a = t.get("assigned_agent", "") if isinstance(t, dict) else ""
        plan_msg += f"{i+1}. {g}" + (f" ({a})" if a else "") + "\n"

    await agent_service.add_message(db, session_id, "system", plan_msg, extra_metadata={"type": "plan"})
    return {"reply": plan_msg, "tasks": tasks}


async def handle_confirm_publish(
    db: AsyncSession, session_id: int, drafts: list[dict], user: User, event_bus=None,
) -> dict:
    """用户确认发布需求草稿。"""
    from app.schemas.need import NeedCreate
    from app.services import need_service, match_engine

    created = []
    for d in drafts:
        data = NeedCreate(
            type=d.get("type", "组队"),
            title=d.get("title", ""),
            description=d.get("description", ""),
            selection_mode=d.get("selection_mode", "single"),
        )
        need = await need_service.create_need(db, user, data, event_bus)
        created.append({"id": need.id, "title": need.title, "type": need.type})

        # Background matching
        import asyncio as _a
        from app.core.database import async_session

        async def _match(nid):
            async with async_session() as bg_db:
                await match_engine.run_matching(bg_db, nid, event_bus)

        _a.create_task(_match(need.id))

        # Start watcher
        watcher = MatchWatcherAgent()
        await watcher.execute({
            "need_id": need.id,
            "session_id": session_id,
            "db_factory": async_session,
        }, {"event_bus": event_bus})

    summary = f"已成功发布 {len(created)} 个需求：\n"
    for c in created:
        summary += f"- [{c['type']}] {c['title']} (ID: {c['id']})\n"
    summary += "\n匹配已启动，结果出来后我会通知你！"

    await agent_service.add_message(db, session_id, "system", summary, extra_metadata={"type": "publish_done"})
    return {"reply": summary, "needs": created}


async def handle_draft_message(
    need_title: str, match_name: str, match_skills: list[str],
    match_reason: str, user_name: str,
) -> str:
    """起草站内消息。"""
    from app.adapters.deepseek_adapter import DeepSeekChatAdapter
    from app.integrations.client import get_ai_client
    from app.integrations.model_router import route
    from app.prompts.registry import PromptRegistry

    client = get_ai_client()
    cfg = route("agent_chat")
    adapter = DeepSeekChatAdapter(client, model=cfg["model"])

    messages = PromptRegistry.render("agent_draft_message", {
        "need_title": need_title,
        "match_name": match_name,
        "match_skills": ", ".join(match_skills),
        "match_reason": match_reason,
        "user_name": user_name,
    })

    return await adapter.chat(messages, temperature=0.8, max_tokens=200)


def _extract_text(file_bytes: bytes, filename: str, file_type: str) -> str:
    """从文件字节中提取文本内容。"""
    if file_type == "txt":
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("gbk", errors="ignore")

    if file_type == "docx":
        try:
            from io import BytesIO
            from docx import Document
            doc = Document(BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception:
            return f"[无法解析docx文件: {filename}]"

    if file_type == "pdf":
        try:
            from io import BytesIO
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(file_bytes))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception:
            return f"[无法解析pdf文件: {filename}]"

    return f"[不支持的文件类型: {file_type}]"
