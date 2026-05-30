import logging

from app.adapters.deepseek_adapter import DeepSeekChatAdapter
from app.agents.base import BaseAgent
from app.integrations.client import get_ai_client
from app.integrations.model_router import route

logger = logging.getLogger(__name__)


class IntentAnalyzerAgent(BaseAgent):
    name = "IntentAnalyzerAgent"
    description = "分析用户意图，判断下一步动作"

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        await self.think("正在分析用户意图...")

        message = input_data.get("message", "")
        extracted = input_data.get("extracted_info")
        user_context = input_data.get("user_context", "")

        client = get_ai_client()
        cfg = route("intent_analysis")
        adapter = DeepSeekChatAdapter(client, model=cfg["model"])

        ctx_parts = []
        if extracted:
            if isinstance(extracted, dict):
                ctx_parts.append(f"已提取文件信息: {extracted.get('title','')} - {extracted.get('summary','')}")
                if extracted.get("potential_needs"):
                    ctx_parts.append(f"潜在需求: {len(extracted['potential_needs'])}个")
        if user_context:
            ctx_parts.append(f"用户背景: {user_context[:200]}")

        ctx_str = "; ".join(ctx_parts) if ctx_parts else "无额外上下文"

        system = (
            "你是意图分类器。分析用户消息，判断其意图。\n"
            "分类: publish_need(发布需求), refine_need(细化需求), "
            "view_matches(查看匹配), upload_file(上传文件), chat(普通对话)。\n"
            "输出JSON: {intent, confidence, summary}。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"用户消息: {message}\n上下文: {ctx_str}"},
        ]

        try:
            result = await adapter.chat_with_json(messages, temperature=cfg["temperature"], max_tokens=cfg["max_tokens"])
            return {"intent": result.get("intent", "chat"), "confidence": result.get("confidence", 0.5), "summary": result.get("summary", "")}
        except Exception:
            logger.exception("Intent analysis failed")
            return {"intent": "chat", "confidence": 0.3, "summary": ""}
