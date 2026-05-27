from __future__ import annotations

from pydantic import BaseModel, Field


class TransportEnvelope(BaseModel):
    delivery_id: str
    actual_sender: str
    actual_receiver: str
    declared_sender: str | None
    declared_receiver: str | None
    topology: str
    topology_edge: str
    round_id: int = Field(ge=0)
    injected_by_attack: bool = False
    attack_type: str | None = None
    source_model: str | None = None
    timestamp_ms: int | None = None
    metadata: dict = Field(default_factory=dict)
