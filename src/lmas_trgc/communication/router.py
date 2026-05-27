from __future__ import annotations

from pydantic import BaseModel, Field

from lmas_trgc.communication.envelope import TransportEnvelope
from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.core.enums import GateAction
from lmas_trgc.core.ids import make_delivery_id
from lmas_trgc.defenses.base import DefenseAdapter, GateDecision
from lmas_trgc.topology.exposure import estimate_topology_exposure
from lmas_trgc.topology.manager import TopologyManager


class RouteResult(BaseModel):
    message_id: str
    delivery_id: str
    delivered: bool
    gate_action: GateAction
    context_bucket: str
    blocked: bool
    downweighted: bool
    warning: bool
    rerouted_to_sv: bool
    reason: str | None
    route_meta: dict = Field(default_factory=dict)
    decision_metadata: dict = Field(default_factory=dict)


class MessageRouter:
    def __init__(self, topology_manager: TopologyManager, defense: DefenseAdapter) -> None:
        self.topology_manager = topology_manager
        self.defense = defense

    def route(
        self,
        message: AgentMessage,
        topology: str,
        source_model: str | None = None,
        injected_by_attack: bool = False,
        attack_type: str | None = None,
    ) -> RouteResult:
        delivery_id = make_delivery_id(
            message_id=message.message_id,
            topology=topology,
            sender=message.sender,
            receiver=message.receiver,
            round_id=message.round_id,
        )
        edge = f"{message.sender}->{message.receiver}"
        envelope = TransportEnvelope(
            delivery_id=delivery_id,
            actual_sender=message.sender,
            actual_receiver=message.receiver,
            declared_sender=message.sender,
            declared_receiver=message.receiver,
            topology=topology,
            topology_edge=edge,
            round_id=message.round_id,
            injected_by_attack=injected_by_attack,
            attack_type=attack_type,
            source_model=source_model,
        )
        edge_allowed = self.topology_manager.is_allowed_edge(topology, message.sender, message.receiver)
        exposure = estimate_topology_exposure(self.topology_manager, topology, message.receiver)
        route_meta = {
            "topology": topology,
            "edge": edge,
            "sender": message.sender,
            "receiver": message.receiver,
            "edge_allowed": edge_allowed,
            "fanout_count": exposure["fanout_count"],
            "critical_nodes_reachable": exposure["critical_nodes_reachable"],
            "exposure_level": exposure["exposure_level"],
            "reachable_nodes": exposure["reachable_nodes"],
        }
        if not edge_allowed:
            decision = GateDecision(
                action=GateAction.BLOCK,
                delivered=False,
                context_bucket="blocked",
                blocked=True,
                reason="Topology edge is not allowed.",
                triggered_flags=["illegal_topology_edge"],
            )
        else:
            decision = self.defense.inspect_before_delivery(message, envelope, route_meta)

        return RouteResult(
            message_id=message.message_id,
            delivery_id=delivery_id,
            delivered=decision.delivered,
            gate_action=decision.action,
            context_bucket=decision.context_bucket,
            blocked=decision.blocked,
            downweighted=decision.downweighted,
            warning=decision.warning,
            rerouted_to_sv=decision.rerouted_to_sv,
            reason=decision.reason,
            route_meta=route_meta,
            decision_metadata={
                "triggered_flags": decision.triggered_flags,
                "defense_latency_ms": decision.defense_latency_ms,
                **decision.metadata,
            },
        )
