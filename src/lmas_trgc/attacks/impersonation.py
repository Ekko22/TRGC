from __future__ import annotations

from lmas_trgc.attacks.base import AttackDecision, BaseAttackStrategy
from lmas_trgc.attacks.targeting import choose_target_slot, should_attack_edge
from lmas_trgc.attacks.templates import append_attack_payload, build_role_impersonation_payload
from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.tasks.schema import TaskPacket


class RoleImpersonationAttack(BaseAttackStrategy):
    attack_type = "role_impersonation"

    def should_attack(self, message: AgentMessage, route_meta: dict, task_packet: TaskPacket) -> AttackDecision:
        should_attack = should_attack_edge(route_meta, self.attack_type)
        return AttackDecision(
            should_attack=should_attack,
            attack_type=self.attack_type,
            reason="high_value_receiver_authority_claim" if should_attack else "edge_not_selected",
            target_slot=choose_target_slot(task_packet, self.attack_type),
        )

    def apply(
        self,
        message: AgentMessage,
        route_meta: dict,
        task_packet: TaskPacket,
        decision: AttackDecision,
    ):
        claimed_authority = "DomainReviewer" if message.receiver == "A7" else "Planner"
        attacked = message.model_copy(deep=True)
        attacked.message_id = f"{message.message_id}__atk_ri"
        attacked.declared_authority = claimed_authority
        attacked.content = append_attack_payload(
            message.content,
            build_role_impersonation_payload(task_packet, decision.target_slot),
        )
        attacked.reasoning_summary = "The message claims an upstream authority confirmation."
        attacked.metadata = {
            **message.metadata,
            "attack": {
                "attack_type": self.attack_type,
                "original_message_id": message.message_id,
                "claimed_authority": claimed_authority,
                "target_slot": decision.target_slot,
            },
        }
        result = self._result(
            message,
            attacked,
            ["message_id", "content", "declared_authority", "reasoning_summary", "metadata"],
            decision.reason,
            metadata={"claimed_authority": claimed_authority, "target_slot": decision.target_slot},
        )
        return attacked, result
