from __future__ import annotations

from lmas_trgc.attacks.base import AttackAdapter


class RelayInjectionAttack(AttackAdapter):
    name = "relay_injection"

    def apply(self, message):
        return message.model_copy(update={"is_forwarded": True})
