from app.adapters.qwen_adapter import get_qwen_embed
from app.skills.base import BaseSkill


class EmbedSkill(BaseSkill):
    name = "embedding"
    description = "将文本转为语义向量（Qwen3-Embedding-0.6B 本地模型）"
    version = "1.0.0"
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "待向量化的文本"}},
        "required": ["text"],
    }
    output_schema = {
        "type": "object",
        "properties": {"embedding": {"type": "array", "items": {"type": "number"}}},
    }
    tags = ["nlp", "embedding", "local"]

    async def execute(self, input_data: dict) -> dict:
        text = input_data["text"]
        adapter = get_qwen_embed()
        embedding = await adapter.embed_single(text)
        return {"embedding": embedding}
