import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

V4_ENDPOINT = "/chat/completions"


class AIClient:
    """DeepSeek API 客户端。

    v4 模型使用 /chat/completions endpoint (无 /v1 前缀)。
    直接用 httpx 调用，避免 OpenAI SDK 自动加 /v1/ 路径。
    """

    def __init__(self):
        self.base = settings.DEEPSEEK_BASE_URL.rstrip("/")
        self.api_key = settings.DEEPSEEK_API_KEY
        self.chat_model = settings.DEEPSEEK_PRO_MODEL
        self.flash_model = settings.DEEPSEEK_FLASH_MODEL

    async def _chat_raw(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: float = 60.0,
    ) -> dict:
        url = f"{self.base}{V4_ENDPOINT}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # v4 models need thinking param for reasoning
        is_v4 = "v4" in model
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        # v4 模型必须显式禁用 thinking，否则输出包含推理过程
        if is_v4:
            body["thinking"] = {"type": "disabled"}

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: float = 60.0,
        max_retries: int = 2,
        json_mode: bool = False,
    ) -> str:
        """调用 DeepSeek Chat API。

        json_mode=True: 使用 response_format={type: json_object} 确保 JSON 输出。
        prompt 中必须包含 "json" 字样才能生效（DeepSeek 要求）。
        """
        model = model or self.chat_model
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                body_kwargs = {}
                if json_mode:
                    body_kwargs["response_format"] = {"type": "json_object"}

                kwargs = {}
                if body_kwargs:

                    async def _call():
                        url = f"{self.base.rstrip('/')}{V4_ENDPOINT}"
                        is_v4 = "v4" in (model or "")
                        body = {
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "stream": False,
                        }
                        if is_v4:
                            body["thinking"] = {"type": "disabled"}
                        body.update(body_kwargs)
                        async with httpx.AsyncClient(timeout=timeout) as client:
                            resp = await client.post(
                                url,
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": f"Bearer {self.api_key}",
                                },
                                json=body,
                            )
                            resp.raise_for_status()
                            return resp.json()

                    data = await asyncio.wait_for(_call(), timeout=timeout + 10)
                else:
                    data = await asyncio.wait_for(
                        self._chat_raw(messages, model, temperature, max_tokens, timeout),
                        timeout=timeout + 10,
                    )

                msg = data["choices"][0]["message"]
                content = msg.get("content") or ""
                if not content:
                    content = msg.get("reasoning_content") or ""
                return content

            except asyncio.TimeoutError:
                last_error = "AI request timed out"
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (400, 401, 402, 403):
                    raise RuntimeError(f"API error {e.response.status_code}: {e.response.text[:200]}")
                last_error = str(e)
            except Exception as e:
                last_error = str(e)

            wait = 2 ** attempt
            if attempt < max_retries:
                logger.warning("Chat error (attempt %d/%d): %s, retrying in %ds", attempt + 1, max_retries + 1, last_error, wait)
                await asyncio.sleep(wait)

        raise RuntimeError(f"AI chat failed after {max_retries + 1} attempts: {last_error}")


_ai_client: AIClient | None = None


def get_ai_client() -> AIClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client
