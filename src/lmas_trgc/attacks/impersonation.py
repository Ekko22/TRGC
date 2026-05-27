from __future__ import annotations

from lmas_trgc.attacks.base import AttackAdapter


class RoleImpersonationAttack(AttackAdapter):
    name = "role_impersonation"

    def apply(self, message):
        return message.model_copy(update={"declared_authority": "unverified_authority"})
