from __future__ import annotations

from lmas_trgc.communication.envelope import TransportEnvelope
from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.core.enums import GateAction
from lmas_trgc.defenses.base import GateDecision
from lmas_trgc.defenses.trgc.risk_flags import find_blocking_terms, find_suspicious_terms


class TRGCPolicy:
    def evaluate(
        self,
        message: AgentMessage,
        envelope: TransportEnvelope,
        route_meta: dict,
    ) -> GateDecision:
        if not route_meta.get("edge_allowed", True):
            return GateDecision(
                action=GateAction.BLOCK,
                delivered=False,
                context_bucket="blocked",
                blocked=True,
                reason="Topology edge is not allowed.",
                triggered_flags=["illegal_topology_edge"],
            )

        blocking_flags = find_blocking_terms(message.content)
        if blocking_flags:
            return GateDecision(
                action=GateAction.BLOCK,
                delivered=False,
                context_bucket="blocked",
                blocked=True,
                reason="TRGC blocked sensitive or bypass content.",
                triggered_flags=blocking_flags,
            )

        if message.declared_authority and message.parent_message_id is None:
            return GateDecision(
                action=GateAction.REROUTE_TO_SV,
                delivered=False,
                context_bucket="sv_pending",
                rerouted_to_sv=True,
                reason="Authority claim has no parent evidence.",
                triggered_flags=["authority_without_parent"],
            )

        suspicious_flags = find_suspicious_terms(message.content)
        if route_meta.get("exposure_level") == "high" and suspicious_flags:
            return GateDecision(
                action=GateAction.REROUTE_TO_SV,
                delivered=False,
                context_bucket="sv_pending",
                rerouted_to_sv=True,
                reason="High exposure route with suspicious content.",
                triggered_flags=suspicious_flags,
            )

        return GateDecision(action=GateAction.ALLOW, delivered=True, context_bucket="trusted")
