from __future__ import annotations

from lmas_trgc.core.enums import GateAction
from lmas_trgc.defenses.base import DefenseAdapter, GateDecision
from lmas_trgc.defenses.trgc.risk_flags import find_blocking_terms


class SimpleContentGuardrailAdapter(DefenseAdapter):
    name = "simple_content_guardrail"

    def inspect_before_delivery(self, message, envelope, route_meta) -> GateDecision:
        flags = find_blocking_terms(message.content)
        if flags:
            return GateDecision(
                action=GateAction.BLOCK,
                delivered=False,
                context_bucket="blocked",
                blocked=True,
                reason="Sensitive or verification-bypass content matched.",
                triggered_flags=flags,
            )
        return GateDecision(action=GateAction.ALLOW, delivered=True, context_bucket="trusted")
