"""系统设置 API — 让用户配置 API Key 等参数。"""

from pathlib import Path

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select as _s
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BACKEND_DIR
from app.core.database import get_db
from app.core.deps import get_current_user
from app.integrations.client import apply_runtime_config
from app.models.system_config import SystemConfig
from app.models.user import User

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    deepseek_api_key: str = ""


@router.get("")
async def get_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(_s(SystemConfig))
    configs = {c.key: c.value for c in r.scalars().all()}
    # Mask API key for security, also check if configured
    key = configs.get("deepseek_api_key", "")
    has_key = bool(key)
    masked = key[:7] + "***" + key[-4:] if len(key) > 10 else ("***" if key else "")
    return {
        "has_api_key": has_key,
        "api_key_masked": masked,
        "base_url": configs.get("deepseek_base_url", "https://api.deepseek.com"),
        "pro_model": configs.get("deepseek_pro_model", "deepseek-v4-pro"),
        "flash_model": configs.get("deepseek_flash_model", "deepseek-v4-flash"),
    }


@router.put("")
async def update_settings(
    data: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = data.deepseek_api_key.strip()
    if key and not key.startswith("sk-"):
        raise HTTPException(400, "API Key 格式不正确，应以 sk- 开头")
    if "\n" in key or "\r" in key:
        raise HTTPException(400, "API Key 不能包含换行符")

    if key:
        await _upsert(db, "deepseek_api_key", key)
        persist_env_value("DEEPSEEK_API_KEY", key)
        apply_runtime_config(deepseek_api_key=key)
    return {"ok": True, "message": "设置已保存并立即生效"}


@router.get("/status")
async def api_status():
    """公开端点：检查 API 是否已配置。"""
    from app.core.database import async_session
    async with async_session() as db:
        r = await db.execute(_s(SystemConfig))
        configs = {c.key: c.value for c in r.scalars().all()}
        has_key = bool(configs.get("deepseek_api_key", ""))
    return {"configured": has_key}


async def _upsert(db: AsyncSession, key: str, value: str):
    r = await db.execute(_s(SystemConfig).where(SystemConfig.key == key))
    existing = r.scalar_one_or_none()
    if existing:
        existing.value = value
    else:
        db.add(SystemConfig(key=key, value=value))
    await db.commit()


def persist_env_value(key: str, value: str, env_path: str | Path | None = None) -> None:
    path = Path(env_path) if env_path is not None else BACKEND_DIR / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    prefix = f"{key}="
    updated: list[str] = []
    replaced = False

    for line in lines:
        if line.startswith(prefix):
            updated.append(f"{key}={value}")
            replaced = True
        else:
            updated.append(line)

    if not replaced:
        updated.append(f"{key}={value}")

    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


async def get_config_value(db: AsyncSession, key: str, default: str = "") -> str:
    """从系统配置表中读取值，不存在则返回默认值。"""
    r = await db.execute(_s(SystemConfig).where(SystemConfig.key == key))
    c = r.scalar_one_or_none()
    return c.value if c else default
