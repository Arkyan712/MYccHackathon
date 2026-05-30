from datetime import datetime

from pydantic import BaseModel


class NeedCreate(BaseModel):
    type: str  # 求助 / 组队 / 技能交换
    title: str
    description: str
    selection_mode: str = "single"  # single / multi


class NeedUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None


class SelectUsersRequest(BaseModel):
    user_ids: list[int]


class NeedResponse(BaseModel):
    id: int
    user_id: int
    username: str = ""
    type: str
    title: str
    description: str
    req_tags: list[str] | None = None
    selection_mode: str = "single"
    selected_user_ids: list[int] | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NeedListResponse(BaseModel):
    items: list[NeedResponse]
    total: int
    page: int
    page_size: int
