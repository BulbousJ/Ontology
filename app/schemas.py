import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    q: str
    entity_type: str | None = None
    max_results: int = 5


class EntityOut(BaseModel):
    id: uuid.UUID
    type: str
    data: dict[str, Any]


class WriteRequest(BaseModel):
    entity_type: Literal["contact", "preference", "goal"]
    match: dict[str, Any] = Field(default_factory=dict)
    patch: dict[str, Any]
    confidence: float = 1.0


class ProposedField(BaseModel):
    field: str
    claim_id: uuid.UUID
    current: Any
    new: Any


class WriteResponse(BaseModel):
    entity_id: uuid.UUID
    applied: list[str]
    proposed: list[ProposedField]


class GrantCreateRequest(BaseModel):
    user_id: uuid.UUID
    client_id: str
    scopes: list[str] = Field(default_factory=list)


class GrantCreateResponse(BaseModel):
    token: str
    expires_at: datetime


class ClaimOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    client_id: str
    entity_id: uuid.UUID
    entity_type: str
    field: str
    old_value: Any
    new_value: Any
    status: str
    created_at: datetime
    confirmed_at: datetime | None

    model_config = {"from_attributes": True}
