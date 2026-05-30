from app.core.config import settings

ROUTING_RULES = {
    "tag_extraction": {"model": settings.DEEPSEEK_FLASH_MODEL, "temperature": 0.1, "max_tokens": 500},
    "rerank": {"model": settings.DEEPSEEK_PRO_MODEL, "temperature": 0.3, "max_tokens": 2000},
    "concierge": {"model": settings.DEEPSEEK_PRO_MODEL, "temperature": 0.7, "max_tokens": 1000},
    "reflection": {"model": settings.DEEPSEEK_PRO_MODEL, "temperature": 0.3, "max_tokens": 1500},
    "moderation": {"model": settings.DEEPSEEK_FLASH_MODEL, "temperature": 0.0, "max_tokens": 200},
    "file_analysis": {"model": settings.DEEPSEEK_FLASH_MODEL, "temperature": 0.1, "max_tokens": 800},
    "summarization": {"model": settings.DEEPSEEK_FLASH_MODEL, "temperature": 0.2, "max_tokens": 300},
    "agent_planner": {"model": settings.DEEPSEEK_PRO_MODEL, "temperature": 0.3, "max_tokens": 1000},
    "agent_chat": {"model": settings.DEEPSEEK_PRO_MODEL, "temperature": 0.7, "max_tokens": 1500},
    "intent_analysis": {"model": settings.DEEPSEEK_FLASH_MODEL, "temperature": 0.1, "max_tokens": 300},
}

DEFAULT_RULE = {"model": settings.DEEPSEEK_FLASH_MODEL, "temperature": 0.3, "max_tokens": 1000}


def route(task: str) -> dict:
    return ROUTING_RULES.get(task, DEFAULT_RULE)
