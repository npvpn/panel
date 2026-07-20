from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ManagedPushRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    version: str = ""
    source: str = ""


class ManagedStateResponse(BaseModel):
    key: str
    version: str
    source: str
    applied_at: Any = None
