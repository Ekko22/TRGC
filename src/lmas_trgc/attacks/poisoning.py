from __future__ import annotations

from lmas_trgc.attacks.base import AttackAdapter


class MessagePoisoningAttack(AttackAdapter):
    name = "message_poisoning"

    def apply(self, message):
        return message.model_copy(update={"metadata": {**message.metadata, "attack": self.name}})
