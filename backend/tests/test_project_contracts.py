import pathlib
import importlib
import os
import sys
import unittest
from datetime import datetime, timedelta


ROOT = pathlib.Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


class ProjectContractTests(unittest.TestCase):
    def test_runtime_requirements_include_agent_file_and_embedding_dependencies(self):
        requirements = (BACKEND / "requirements.txt").read_text(encoding="utf-8")

        for package in ("sentence-transformers", "python-docx", "PyPDF2"):
            with self.subTest(package=package):
                self.assertIn(package, requirements)

    def test_typescript_six_deprecation_is_explicitly_handled(self):
        tsconfig = (FRONTEND / "tsconfig.app.json").read_text(encoding="utf-8")

        self.assertIn('"ignoreDeprecations": "6.0"', tsconfig)

    def test_backend_config_anchors_env_and_sqlite_to_backend_directory(self):
        source = (BACKEND / "app" / "core" / "config.py").read_text(encoding="utf-8")

        self.assertIn("BACKEND_DIR", source)
        self.assertIn('DB_PATH = BACKEND_DIR / "app.db"', source)
        self.assertIn('SettingsConfigDict(env_file=BACKEND_DIR / ".env")', source)
        self.assertIn("DB_PATH.as_posix()", source)

    def test_backend_config_accepts_release_debug_environment_value(self):
        previous_debug = os.environ.get("DEBUG")
        os.environ["DEBUG"] = "release"
        sys.modules.pop("app.core.config", None)
        try:
            config = importlib.import_module("app.core.config")
            self.assertFalse(config.settings.DEBUG)
        finally:
            sys.modules.pop("app.core.config", None)
            if previous_debug is None:
                os.environ.pop("DEBUG", None)
            else:
                os.environ["DEBUG"] = previous_debug

    def test_message_conversation_query_partitions_by_actual_other_user(self):
        source = (BACKEND / "app" / "services" / "message_service.py").read_text(encoding="utf-8")

        self.assertIn("conversation_partner_expr", source)
        self.assertNotIn("partition_by=func.max", source)

    def test_frontend_exposes_promised_demo_features(self):
        need_create = (FRONTEND / "src" / "views" / "NeedCreateView.vue").read_text(encoding="utf-8")
        match_result = (FRONTEND / "src" / "views" / "MatchResultView.vue").read_text(encoding="utf-8")
        agent_store = (FRONTEND / "src" / "stores" / "agent.ts").read_text(encoding="utf-8")
        agent_view = (FRONTEND / "src" / "views" / "AgentView.vue").read_text(encoding="utf-8")

        self.assertIn("needTemplates", need_create)
        self.assertIn("comparison-table", match_result)
        self.assertIn("suggestions", agent_store)
        self.assertIn("主动建议", agent_view)


class AgentBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from app.core.database import Base
        import app.models.agent  # noqa: F401
        import app.models.user  # noqa: F401

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_agent_messages_return_latest_limit_in_chronological_order(self):
        from app.models.agent import AgentMessage, AgentSession
        from app.models.user import User
        from app.services import agent_service

        async with self.Session() as db:
            user = User(username="agent-user", password_hash="x")
            db.add(user)
            await db.flush()
            session = AgentSession(user_id=user.id, title="latest messages")
            db.add(session)
            await db.flush()

            base_time = datetime(2026, 5, 30, 8, 0, 0)
            for i in range(60):
                db.add(AgentMessage(
                    session_id=session.id,
                    role="user",
                    content=f"message-{i}",
                    created_at=base_time + timedelta(minutes=i),
                ))
            await db.commit()

            messages = await agent_service.get_messages(db, session.id, limit=50)

        self.assertEqual(len(messages), 50)
        self.assertEqual(messages[0].content, "message-10")
        self.assertEqual(messages[-1].content, "message-59")

    async def test_agent_memory_does_not_resummarize_already_summarized_messages(self):
        from app.models.agent import AgentMessage, AgentSession
        from app.models.user import User
        from app.services.agent_memory import ContextManager
        from app.skills.registry import SkillRegistry

        class FakeSummarizer:
            def __init__(self):
                self.calls = []

            async def execute(self, payload):
                self.calls.append([m["content"] for m in payload["messages"]])
                return {"summary": f"summary-{len(self.calls)}"}

        original_get = SkillRegistry.get
        fake = FakeSummarizer()
        SkillRegistry.get = classmethod(lambda cls, name: fake if name == "context_summarizer" else original_get(name))
        try:
            async with self.Session() as db:
                user = User(username="memory-user", password_hash="x")
                db.add(user)
                await db.flush()
                session = AgentSession(user_id=user.id, title="memory")
                db.add(session)
                await db.flush()

                base_time = datetime(2026, 5, 30, 9, 0, 0)
                for i in range(25):
                    db.add(AgentMessage(
                        session_id=session.id,
                        role="user",
                        content=f"memory-{i}",
                        created_at=base_time + timedelta(minutes=i),
                    ))
                await db.commit()
                await db.refresh(session)

                manager = ContextManager(db)
                await manager.get_chat_context(session.id)
                await manager.get_chat_context(session.id)

                await db.refresh(session)

            self.assertEqual(fake.calls, [[f"memory-{i}" for i in range(15)]])
            self.assertIn("summarized_until_message_id", session.planning_state["_memory"])
        finally:
            SkillRegistry.get = original_get

    def test_agent_router_protects_session_scoped_side_endpoints(self):
        source = (BACKEND / "app" / "routers" / "agents.py").read_text(encoding="utf-8")

        self.assertIn("ensure_session_owner", source)
        self.assertIn("await ensure_session_owner(db, session_id, user.id)", source)

    def test_agent_view_renders_messages_as_text_not_html(self):
        source = (FRONTEND / "src" / "views" / "AgentView.vue").read_text(encoding="utf-8")

        self.assertNotIn("v-html", source)
        self.assertIn("white-space: pre-wrap", source)

    def test_agent_store_keeps_task_panel_and_streaming_state_in_sync(self):
        source = (FRONTEND / "src" / "stores" / "agent.ts").read_text(encoding="utf-8")

        self.assertIn("async function refreshTasks", source)
        self.assertIn("await refreshTasks(sessionId)", source)
        self.assertIn("finally", source)
        self.assertIn("isStreaming.value = false", source)

    def test_agent_upload_can_return_publishable_drafts(self):
        backend_source = (BACKEND / "app" / "services" / "agent_planner.py").read_text(encoding="utf-8")
        frontend_source = (FRONTEND / "src" / "api" / "agent.ts").read_text(encoding="utf-8")

        self.assertIn('return {"reply": ai_msg, "file_id": af.id, "extracted": extracted, "drafts": drafts}', backend_source)
        self.assertIn("drafts?: NeedDraft[]", frontend_source)


if __name__ == "__main__":
    unittest.main()
