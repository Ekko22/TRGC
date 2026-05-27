from __future__ import annotations

from lmas_trgc.core.enums import GateAction
from lmas_trgc.defenses.base import DefenseAdapter, GateDecision


class NoDefenseAdapter(DefenseAdapter):
    name = "no_defense"

    def inspect_before_delivery(self, message, envelope, route_meta) -> GateDecision:
        return GateDecision(action=GateAction.ALLOW, delivered=True, context_bucket="trusted")
