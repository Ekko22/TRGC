from __future__ import annotations

from lmas_trgc.core.enums import GateAction
from lmas_trgc.defenses.base import DefenseAdapter, GateDecision


class GSafeguardAdapter(DefenseAdapter):
    """Stable integration boundary for G-Safeguard.

    This adapter is a stable integration boundary. The actual G-Safeguard GNN
    implementation will be integrated here in a later step. It is not used to
    claim G-Safeguard results before integration.
    """

    name = "gsafeguard"

    def inspect_before_delivery(self, message, envelope, route_meta) -> GateDecision:
        return GateDecision(action=GateAction.ALLOW, delivered=True, context_bucket="trusted")

    def on_after_round(self, round_messages, topology) -> dict:
        return {"interventions": []}
