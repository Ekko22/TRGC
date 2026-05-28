import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _fake_run(
    batch_dir: Path,
    *,
    run_id: str,
    attack_type: str,
    defense_name: str,
    task_success: bool,
    answer_correct: bool,
    attack_success: bool,
    robust_success: bool,
    attacked_messages: int,
    blocked_messages: int = 0,
) -> dict:
    run_dir = batch_dir.parent / "stage_c_manifest" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_id": run_id,
        "task_id": "task_1",
        "dataset": "gsm8k",
        "domain": "math_reasoning",
        "topology": "graph",
        "attack_type": attack_type,
        "defense_name": defense_name,
        "completed": True,
        "final_agent": "A7",
        "total_messages": 1,
        "total_llm_calls": 1,
        "total_input_tokens": 10,
        "total_output_tokens": 5,
        "total_tokens": 15,
        "delivered_messages": 1 - blocked_messages,
        "blocked_messages": blocked_messages,
        "downweighted_messages": 0,
        "rerouted_messages": 0,
        "attacked_messages": attacked_messages,
        "final_context_hash": "ctx_hash",
        "final_output_hash": "out_hash",
        "created_at": "2026-05-28T00:00:00+00:00",
        "metadata": {},
    }
    metrics = {
        "run_id": run_id,
        "task_id": "task_1",
        "topology": "graph",
        "attack_type": attack_type,
        "defense_name": defense_name,
        "total_messages": 1,
        "delivered_messages": 1 - blocked_messages,
        "blocked_messages": blocked_messages,
        "downweighted_messages": 0,
        "rerouted_messages": 0,
        "attacked_messages": attacked_messages,
        "total_llm_calls": 1,
        "total_input_tokens": 10,
        "total_output_tokens": 5,
        "total_tokens": 15,
        "avg_tokens_per_message": 15.0,
        "attack_injection_rate": float(attacked_messages),
        "block_rate": float(blocked_messages),
        "downweight_rate": 0.0,
        "reroute_rate": 0.0,
        "delivery_rate": float(1 - blocked_messages),
        "critical_node_reach_count": 1 if attacked_messages else 0,
        "critical_node_reach_rate": 1.0 if attacked_messages else 0.0,
        "propagation_depth_proxy": 1,
        "metadata": {},
    }
    judge = {
        "run_id": run_id,
        "task_id": "task_1",
        "judge_mode": "rule_based",
        "valid_for_paper": True,
        "task_success": task_success,
        "answer_correct": answer_correct,
        "safety_violation": False,
        "attack_success": attack_success,
        "robust_success": robust_success,
        "expected_answer": "42",
        "predicted_answer": "42" if answer_correct else "wrong",
        "metric": "exact_match",
        "violation_types": [],
        "matched_terms": [],
        "reason": None,
        "metadata": {},
    }
    standard = {
        "run_id": run_id,
        "task_id": "task_1",
        "dataset": "gsm8k",
        "domain": "math_reasoning",
        "topology": "graph",
        "attack_type": attack_type,
        "defense_name": defense_name,
        "judge_mode": "rule_based",
        "valid_for_paper": True,
        "clean_success": task_success if attack_type == "none" else None,
        "robust_success": robust_success if attack_type != "none" else None,
        "attack_success": attack_success if attack_type != "none" else None,
        "safety_violation": False,
        "benign_drop_applicable": attack_type == "none",
        "task_success": task_success,
        "answer_correct": answer_correct,
    }
    event = {
        "run_id": run_id,
        "task_id": "task_1",
        "step_id": 1,
        "sender": "A1",
        "receiver": "A7",
        "message_id": f"msg_{run_id}",
        "delivered": blocked_messages == 0,
        "gate_action": "allow" if blocked_messages == 0 else "block",
        "context_bucket": "trusted",
        "blocked": blocked_messages > 0,
        "downweighted": False,
        "rerouted_to_sv": False,
        "attack_injected": attacked_messages > 0,
        "attack_type": attack_type if attacked_messages else None,
        "topology": "graph",
    }
    topo_event = {
        "run_id": run_id,
        "task_id": "task_1",
        "topology": "graph",
        "step_id": 1,
        "edge": "A1->A7",
        "sender": "A1",
        "receiver": "A7",
        "gate_action": event["gate_action"],
        "delivered": event["delivered"],
        "blocked": event["blocked"],
        "downweighted": False,
        "rerouted_to_sv": False,
        "attack_injected": event["attack_injected"],
        "is_critical_receiver": True,
        "critical_nodes_reachable": ["A7"] if attacked_messages else [],
        "metadata": {},
    }
    _write_json(run_dir / "run_summary.json", summary)
    _write_json(run_dir / "metrics.json", metrics)
    _write_json(run_dir / "judge_outcome.json", judge)
    _write_json(run_dir / "standard_metrics.json", standard)
    _write_jsonl(run_dir / "message_events.jsonl", [event])
    _write_jsonl(run_dir / "topology_events.jsonl", [topo_event])
    return {
        "run_id": run_id,
        "task_id": "task_1",
        "dataset": "gsm8k",
        "topology": "graph",
        "attack": attack_type,
        "defense": defense_name,
        "artifact_dir": str(run_dir),
        "completed": True,
        "failed": False,
    }


def test_diagnose_deepseek_pilot_script_outputs_json_and_markdown(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    batch_dir = tmp_path / "results" / "runs" / "stage_c_manifest_batches" / "fake_batch"
    batch_dir.mkdir(parents=True)
    records = [
        _fake_run(
            batch_dir,
            run_id="run_clean_fail",
            attack_type="none",
            defense_name="no_defense",
            task_success=False,
            answer_correct=False,
            attack_success=False,
            robust_success=False,
            attacked_messages=0,
        ),
        _fake_run(
            batch_dir,
            run_id="run_trgc_attack",
            attack_type="message_poisoning",
            defense_name="trgc",
            task_success=False,
            answer_correct=False,
            attack_success=True,
            robust_success=False,
            attacked_messages=1,
            blocked_messages=1,
        ),
    ]
    _write_jsonl(batch_dir / "run_index.jsonl", records)

    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "diagnose_deepseek_pilot.py"),
            "--batch-dir",
            str(batch_dir),
            "--json",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["total_runs"] == 2
    assert payload["root_cause_decision"]["should_scale_experiment"] is False
    assert (tmp_path / "docs" / "dev_logs" / "0020_deepseek_diagnostic_root_cause.md").exists()
    assert (tmp_path / "data" / "manifests" / "deepseek_diagnostic_audit.json").exists()
