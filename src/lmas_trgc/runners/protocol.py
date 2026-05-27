from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from lmas_trgc.core.config import load_config_file, load_yaml
from lmas_trgc.core.enums import MessageType
from lmas_trgc.topology.manager import TopologyManager


class ProtocolEdge(BaseModel):
    sender: str
    receiver: str
    message_type: str
    purpose: str | None = None

    @field_validator("sender", "receiver", "message_type")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be empty")
        return value

    @model_validator(mode="after")
    def _valid_edge(self) -> "ProtocolEdge":
        if self.sender == self.receiver:
            raise ValueError("protocol edge sender and receiver must differ")
        if self.sender == "SV" or self.receiver == "SV":
            raise ValueError("SV must not appear in protocol edges")
        return self


class ProtocolStep(BaseModel):
    step_id: int = Field(ge=1)
    edges: list[ProtocolEdge]

    @field_validator("edges")
    @classmethod
    def _edges_non_empty(cls, value: list[ProtocolEdge]) -> list[ProtocolEdge]:
        if not value:
            raise ValueError("protocol step must contain at least one edge")
        return value


class TopologyProtocol(BaseModel):
    topology: str
    steps: list[ProtocolStep]

    @field_validator("steps")
    @classmethod
    def _steps_non_empty(cls, value: list[ProtocolStep]) -> list[ProtocolStep]:
        if not value:
            raise ValueError("protocol must contain at least one step")
        return value


def _message_type_name(value: str) -> MessageType:
    if value in MessageType.__members__:
        return MessageType[value]
    lowered = value.lower()
    for item in MessageType:
        if item.value == lowered:
            return item
    raise ValueError(f"Unknown message_type: {value}")


class ProtocolManager:
    def __init__(
        self,
        protocols_path: Path | None = None,
        topology_manager: TopologyManager | None = None,
    ) -> None:
        self.topology_manager = topology_manager or TopologyManager()
        raw = load_yaml(protocols_path) if protocols_path else load_config_file("protocols.yaml")
        protocols = raw.get("protocols", {})
        if not isinstance(protocols, dict) or not protocols:
            raise ValueError("protocols.yaml must contain a non-empty protocols mapping")
        self._protocols = {
            name: TopologyProtocol(**spec)
            for name, spec in protocols.items()
        }
        for name in self._protocols:
            self.validate_protocol(name)

    def list_protocols(self) -> list[str]:
        return sorted(self._protocols)

    def get_protocol(self, topology: str) -> TopologyProtocol:
        if topology not in self._protocols:
            raise KeyError(f"Unknown protocol topology: {topology}")
        return self._protocols[topology]

    def validate_protocol(self, topology: str) -> None:
        protocol = self.get_protocol(topology)
        if protocol.topology != topology:
            raise ValueError(f"Protocol key {topology!r} declares topology {protocol.topology!r}")
        if topology not in self.topology_manager.list_topologies():
            raise ValueError(f"Protocol references unknown topology: {topology}")
        previous = 0
        for step in protocol.steps:
            if step.step_id <= previous:
                raise ValueError(f"Protocol {topology} step_id must be strictly increasing at step {step.step_id}")
            previous = step.step_id
            for edge in step.edges:
                try:
                    _message_type_name(edge.message_type)
                    allowed = self.topology_manager.is_allowed_edge(topology, edge.sender, edge.receiver)
                except Exception as exc:
                    raise ValueError(
                        f"Invalid protocol edge topology={topology} step_id={step.step_id} "
                        f"sender={edge.sender} receiver={edge.receiver}: {exc}"
                    ) from exc
                if not allowed:
                    raise ValueError(
                        f"Invalid protocol edge topology={topology} step_id={step.step_id} "
                        f"sender={edge.sender} receiver={edge.receiver}: edge not allowed by topology"
                    )

    def iter_edges(self, topology: str) -> Iterator[tuple[int, ProtocolEdge]]:
        protocol = self.get_protocol(topology)
        for step in protocol.steps:
            for edge in step.edges:
                yield step.step_id, edge
