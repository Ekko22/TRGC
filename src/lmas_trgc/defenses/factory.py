from __future__ import annotations

from lmas_trgc.defenses.base import DefenseAdapter
from lmas_trgc.defenses.full_checking import FullCheckingLightAdapter
from lmas_trgc.defenses.gsafeguard_adapter import GSafeguardAdapter
from lmas_trgc.defenses.no_defense import NoDefenseAdapter
from lmas_trgc.defenses.simple_guardrail import SimpleContentGuardrailAdapter
from lmas_trgc.defenses.trgc.controller import TRGCAdapter
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.topology.manager import TopologyManager


def _normalize(name: str) -> str:
    return name.strip().lower().replace("-", "_")


def create_defense_adapter(
    defense_name: str,
    topology_manager: TopologyManager,
    safety_verifier: SafetyVerifier | None = None,
) -> DefenseAdapter:
    normalized = _normalize(defense_name)
    if normalized == "no_defense":
        return NoDefenseAdapter()
    if normalized == "simple_content_guardrail":
        return SimpleContentGuardrailAdapter()
    if normalized == "full_checking_light":
        if safety_verifier is None:
            raise ValueError("full_checking_light requires a safety_verifier")
        return FullCheckingLightAdapter(safety_verifier=safety_verifier)
    if normalized == "gsafeguard":
        return GSafeguardAdapter()
    if normalized == "trgc":
        if safety_verifier is None:
            raise ValueError("trgc requires a safety_verifier")
        return TRGCAdapter(safety_verifier=safety_verifier)
    raise ValueError(f"Unknown defense adapter: {defense_name}")
