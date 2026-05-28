from pathlib import Path

from lmas_trgc.tasks.registry import get_default_dataset_specs, load_dataset_specs, total_target_main_count


PUBLIC_DATASETS = ["gsm8k", "prontoqa", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]


def test_public_dataset_specs_have_candidates_or_local_raw():
    specs = get_default_dataset_specs()
    for dataset in PUBLIC_DATASETS:
        spec = specs[dataset]
        assert spec.hf_candidates or spec.local_raw_candidates
        assert spec.processed_path == f"data/processed/public/{dataset}.jsonl"


def test_key_public_candidate_sources():
    specs = get_default_dataset_specs()
    assert any(candidate["path"] == "openai/gsm8k" for candidate in specs["gsm8k"].hf_candidates)
    assert any(candidate["path"] == "EleutherAI/prontoqa" for candidate in specs["prontoqa"].hf_candidates)
    assert any(candidate["path"] == "cais/mmlu" for candidate in specs["mmlu"].hf_candidates)
    assert any(candidate["path"] == "tau/commonsense_qa" for candidate in specs["csqa"].hf_candidates)
    assert any(candidate["path"] == "openai/openai_humaneval" for candidate in specs["humaneval"].hf_candidates)
    assert total_target_main_count() == 104


def test_dataset_specs_load_from_yaml_config():
    specs = load_dataset_specs(Path("configs/datasets.yaml"))
    assert list(specs)[:3] == ["gsm8k", "prontoqa", "mmlu"]
    assert specs["svamp"].source_type == "hf_or_local"
