from __future__ import annotations

from lmas_trgc.attacks.base import AttackDecision, BaseAttackStrategy
from lmas_trgc.attacks.targeting import choose_target_slot, should_attack_edge
from lmas_trgc.attacks.templates import append_attack_payload, build_message_poisoning_payload
from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.tasks.schema import TaskPacket


class MessagePoisoningAttack(BaseAttackStrategy):
    attack_type = "message_poisoning"

    def should_attack(self, message: AgentMessage, route_meta: dict, task_packet: TaskPacket) -> AttackDecision:
        target_slot = choose_target_slot(task_packet, self.attack_type)
        should_attack = should_attack_edge(route_meta, self.attack_type)
        return AttackDecision(
            should_attack=should_attack,
            attack_type=self.attack_type,
            reason="targeted_high_value_edge" if should_attack else "edge_not_selected",
            target_slot=target_slot,
            metadata={"target_slot_missing": target_slot is None},
        )

    def apply(
        self,
        message: AgentMessage,
        route_meta: dict,
        task_packet: TaskPacket,
        decision: AttackDecision,
    ):
        payload = build_message_poisoning_payload(task_packet, decision.target_slot)
        attacked = message.model_copy(deep=True)
        attacked.message_id = f"{message.message_id}__atk_mp"
        attacked.content = append_attack_payload(message.content, payload)
        attacked.metadata = {
            **message.metadata,
            "attack": {
                "attack_type": self.attack_type,
                "original_message_id": message.message_id,
                "target_slot": decision.target_slot,
            },
        }
        result = self._result(
            message,
            attacked,
            ["message_id", "content", "metadata"],
            decision.reason,
            metadata={"target_slot": decision.target_slot},
        )
        return attacked, result
