from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from lmas_trgc.core.enums import GateAction


class GateDecision(BaseModel):
    action: GateAction
    delivered: bool
    context_bucket: str
    rerouted_to_sv: bool = False
    blocked: bool = False
    downweighted: bool = False
    warning: bool = False
    reason: str | None = None
    triggered_flags: list[str] = Field(default_factory=list)
    defense_latency_ms: float = 0.0
    metadata: dict = Field(default_factory=dict)


class DefenseAdapter(ABC):
    name: str

    @abstractmethod
    def inspect_before_delivery(self, message, envelope, route_meta) -> GateDecision:
        raise NotImplementedError
