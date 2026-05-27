from __future__ import annotations

from lmas_trgc.attacks.base import AttackResult, BaseAttackStrategy
from lmas_trgc.attacks.impersonation import RoleImpersonationAttack
from lmas_trgc.attacks.poisoning import MessagePoisoningAttack
from lmas_trgc.attacks.relay import RelayInjectionAttack
from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.tasks.schema import TaskPacket


def build_attack(name: str):
    attacks = {
        "message_poisoning": MessagePoisoningAttack,
        "role_impersonation": RoleImpersonationAttack,
        "relay_injection": RelayInjectionAttack,
    }
    if name == "none":
        return None
    if name not in attacks:
        raise KeyError(f"Unknown attack: {name}")
    return attacks[name]()


class AttackManager:
    def __init__(
        self,
        attack_type: str,
        strategies: dict[str, BaseAttackStrategy] | None = None,
    ) -> None:
        self.attack_type = attack_type.strip().lower().replace("-", "_")
        self.strategies = strategies or {
            "message_poisoning": MessagePoisoningAttack(),
            "role_impersonation": RoleImpersonationAttack(),
            "relay_injection": RelayInjectionAttack(),
        }
        if self.attack_type != "none" and self.attack_type not in self.strategies:
            raise ValueError(f"Unknown attack_type: {attack_type}")

    def is_enabled(self) -> bool:
        return self.attack_type != "none"

    def apply_attack_if_needed(
        self,
        message: AgentMessage,
        route_meta: dict,
        task_packet: TaskPacket,
    ) -> tuple[AgentMessage, AttackResult | None]:
        if not self.is_enabled():
            return message, None
        strategy = self.strategies[self.attack_type]
        decision = strategy.should_attack(message, route_meta, task_packet)
        if not decision.should_attack:
            return message, None
        return strategy.apply(message, route_meta, task_packet, decision)
