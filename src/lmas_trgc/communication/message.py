from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AgentMessage(BaseModel):
    message_id: str
    parent_message_id: str | None
    round_id: int = Field(ge=0)
    sender: str
    receiver: str
    sender_role: str
    receiver_role: str
    message_type: str
    content: str
    reasoning_summary: str | None
    confidence: float | None = None
    task_id: str
    is_forwarded: bool = False
    declared_authority: str | None = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("sender", "receiver", "content")
    @classmethod
    def _must_not_be_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def _confidence_in_range(cls, value: float | None) -> float | None:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return value
