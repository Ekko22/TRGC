from __future__ import annotations

from lmas_trgc.core.enums import GateAction
from lmas_trgc.defenses.base import DefenseAdapter, GateDecision
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier


class FullCheckingLightAdapter(DefenseAdapter):
    name = "full_checking_light"

    def __init__(self, safety_verifier: SafetyVerifier | None = None) -> None:
        self.safety_verifier = safety_verifier or SafetyVerifier(mode="mock")

    def inspect_before_delivery(self, message, envelope, route_meta) -> GateDecision:
        verdict = self.safety_verifier.verify(
            {"text": message.content, "route_meta": route_meta, "message": message.model_dump()}
        )
        sv_flags = []
        if verdict.raw and isinstance(verdict.raw.get("matched_terms"), list):
            sv_flags = verdict.raw["matched_terms"]
        if verdict.verdict == "block":
            return GateDecision(
                action=GateAction.BLOCK,
                delivered=False,
                context_bucket="blocked",
                blocked=True,
                rerouted_to_sv=True,
                reason=verdict.reason,
                triggered_flags=sv_flags,
                metadata={"sv_verdict": verdict.model_dump()},
            )
        if verdict.verdict == "downweight":
            return GateDecision(
                action=GateAction.DOWNWEIGHT,
                delivered=True,
                context_bucket="risk_marked",
                downweighted=True,
                rerouted_to_sv=True,
                reason=verdict.reason,
                triggered_flags=sv_flags,
                metadata={"sv_verdict": verdict.model_dump()},
            )
        return GateDecision(
            action=GateAction.ALLOW,
            delivered=True,
            context_bucket="trusted",
            rerouted_to_sv=True,
            metadata={"sv_verdict": verdict.model_dump()},
        )
