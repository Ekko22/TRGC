from __future__ import annotations

from lmas_trgc.core.enums import GateAction
from lmas_trgc.defenses.base import DefenseAdapter, GateDecision
from lmas_trgc.defenses.trgc.policy import TRGCPolicy
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier


class TRGCAdapter(DefenseAdapter):
    name = "trgc"

    def __init__(
        self,
        policy: TRGCPolicy | None = None,
        safety_verifier: SafetyVerifier | None = None,
    ) -> None:
        self.policy = policy or TRGCPolicy()
        self.safety_verifier = safety_verifier or SafetyVerifier(mode="mock")

    def inspect_before_delivery(self, message, envelope, route_meta) -> GateDecision:
        decision = self.policy.evaluate(message, envelope, route_meta)
        if decision.action != GateAction.REROUTE_TO_SV:
            return decision

        verdict = self.safety_verifier.verify(
            {
                "text": message.content,
                "message": message.model_dump(),
                "envelope": envelope.model_dump(),
                "route_meta": route_meta,
                "evidence_missing": message.parent_message_id is None,
            }
        )
        sv_flags = []
        if verdict.raw and isinstance(verdict.raw.get("matched_terms"), list):
            sv_flags = verdict.raw["matched_terms"]
        flags = [*decision.triggered_flags, *sv_flags]
        if verdict.verdict == "block":
            return GateDecision(
                action=GateAction.BLOCK,
                delivered=False,
                context_bucket="blocked",
                rerouted_to_sv=True,
                blocked=True,
                reason=verdict.reason or decision.reason,
                triggered_flags=flags,
                metadata={"sv_verdict": verdict.model_dump()},
            )
        if verdict.verdict == "downweight":
            return GateDecision(
                action=GateAction.DOWNWEIGHT,
                delivered=True,
                context_bucket="risk_marked",
                rerouted_to_sv=True,
                downweighted=True,
                reason=verdict.reason or decision.reason,
                triggered_flags=flags,
                metadata={"sv_verdict": verdict.model_dump()},
            )
        return GateDecision(
            action=GateAction.ALLOW,
            delivered=True,
            context_bucket="trusted",
            rerouted_to_sv=True,
            reason=verdict.reason,
            triggered_flags=flags,
            metadata={"sv_verdict": verdict.model_dump()},
        )
