from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _not_empty(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("field must not be empty")
    return value


class RunSummaryRecord(BaseModel):
    run_id: str
    task_id: str
    dataset: str | None = None
    domain: str | None = None
    topology: str
    attack_type: str
    defense_name: str
    completed: bool
    final_agent: str
    total_messages: int = Field(ge=0)
    delivered_messages: int = Field(ge=0)
    blocked_messages: int = Field(ge=0)
    downweighted_messages: int = Field(ge=0)
    rerouted_messages: int = Field(ge=0)
    attacked_messages: int = Field(ge=0)
    final_context_hash: str | None = None
    final_output_hash: str | None = None
    created_at: str
    metadata: dict = Field(default_factory=dict)

    @field_validator("run_id", "task_id", "topology", "attack_type", "defense_name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _not_empty(value)


class MessageEventRecord(BaseModel):
    run_id: str
    task_id: str
    step_id: int
    sender: str
    receiver: str
    message_id: str
    delivered: bool
    gate_action: str
    context_bucket: str
    blocked: bool
    downweighted: bool
    rerouted_to_sv: bool
    reason: str | None = None
    attack_injected: bool = False
    attack_type: str | None = None
    attack_changed_fields: list[str] = Field(default_factory=list)
    topology: str
    topology_edge: str | None = None
    fanout_count: int | None = None
    critical_nodes_reachable: list[str] = Field(default_factory=list)
    exposure_level: str | None = None
    content_hash: str | None = None
    metadata: dict = Field(default_factory=dict)


class TopologyEventRecord(BaseModel):
    run_id: str
    task_id: str
    topology: str
    step_id: int
    edge: str
    sender: str
    receiver: str
    gate_action: str
    delivered: bool
    blocked: bool
    downweighted: bool
    rerouted_to_sv: bool
    attack_injected: bool = False
    is_critical_receiver: bool = False
    critical_nodes_reachable: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class MetricsRecord(BaseModel):
    run_id: str
    task_id: str
    topology: str
    attack_type: str
    defense_name: str
    total_messages: int = Field(ge=0)
    delivered_messages: int = Field(ge=0)
    blocked_messages: int = Field(ge=0)
    downweighted_messages: int = Field(ge=0)
    rerouted_messages: int = Field(ge=0)
    attacked_messages: int = Field(ge=0)
    attack_injection_rate: float
    block_rate: float
    downweight_rate: float
    reroute_rate: float
    delivery_rate: float
    critical_node_reach_count: int = Field(ge=0)
    critical_node_reach_rate: float
    propagation_depth_proxy: int = Field(ge=0)
    metadata: dict = Field(default_factory=dict)


class RunArtifactManifest(BaseModel):
    run_id: str
    artifact_dir: str
    files: dict[str, str]
    created_at: str
    schema_version: str = "1.0"
    metadata: dict = Field(default_factory=dict)
