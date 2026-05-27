from __future__ import annotations

from lmas_trgc.attacks.impersonation import RoleImpersonationAttack
from lmas_trgc.attacks.poisoning import MessagePoisoningAttack
from lmas_trgc.attacks.relay import RelayInjectionAttack


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
