import pytest

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.llm.registry import build_model_registry
from lmas_trgc.runners.manifest_pilot import StageCDeepSeekManifestPilotConfig, StageCDeepSeekManifestPilotRunner
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.topology.manager import TopologyManager


def test_stage_c_manifest_pilot_config_defaults():
    config = StageCDeepSeekManifestPilotConfig(batch_id="batch_test")
    assert config.tasks_per_dataset == 1
    assert config.topologies == ["graph"]
    assert config.attacks == ["message_poisoning"]
    assert config.defenses == ["no_defense", "trgc"]
    assert config.max_steps == 3
    assert config.sv_mode == "client"
    assert not config.confirm_real_llm


def test_runner_refuses_without_confirm_real_llm():
    topology_manager = TopologyManager()
    runner = StageCDeepSeekManifestPilotRunner(
        topology_manager=topology_manager,
        protocol_manager=ProtocolManager(topology_manager=topology_manager),
        agent_profiles=load_agent_profiles(),
        prompt_builder=PromptBuilder(),
        model_registry=build_model_registry(require_keys=False),
    )
    with pytest.raises(RuntimeError, match="Refusing"):
        runner.run_pilot(StageCDeepSeekManifestPilotConfig(batch_id="batch_test"))


def test_stage_c_manifest_pilot_config_rejects_bad_values():
    with pytest.raises(ValueError):
        StageCDeepSeekManifestPilotConfig(batch_id="batch_test", max_steps=0)
    with pytest.raises(ValueError):
        StageCDeepSeekManifestPilotConfig(batch_id="batch_test", topologies=["bad"])
    with pytest.raises(ValueError):
        StageCDeepSeekManifestPilotConfig(batch_id="batch_test", attacks=["bad"])
    with pytest.raises(ValueError):
        StageCDeepSeekManifestPilotConfig(batch_id="batch_test", defenses=["gsafeguard"])
    with pytest.raises(ValueError):
        StageCDeepSeekManifestPilotConfig(batch_id="batch_test", sv_mode="bad")
