import json

import pytest

from lmas_trgc.logging.batch_writer import StageBBatchWriter


def test_batch_writer_writes_files_and_redacts(tmp_path):
    writer = StageBBatchWriter(tmp_path)
    batch_dir = writer.make_batch_dir("batch_test")
    summary = {"batch_id": "batch_test", "total_runs": 1, "successful_runs": 1, "failed_runs": 0}
    writer.write_batch_summary(batch_dir, summary)
    writer.write_run_index(
        batch_dir,
        [
            {
                "batch_id": "batch_test",
                "run_id": "run_1",
                "task_id": "task_1",
                "dataset": "local_mas_safety",
                "topology": "graph",
                "attack": "message_poisoning",
                "defense": "trgc",
                "artifact_dir": "/tmp/run_1",
                "completed": True,
                "failed": False,
                "error": None,
            }
        ],
    )
    writer.write_aggregate_metrics(batch_dir, {"total_runs": 1}, [{"run_id": "run_1", "blocked_messages": 0}])
    writer.write_manifest(batch_dir, {"summary": "batch_summary.json"}, {"api_key": "secret", "prompt": "hidden"})
    writer.write_readme(batch_dir, summary)

    assert (batch_dir / "batch_summary.json").exists()
    assert (batch_dir / "run_index.jsonl").exists()
    assert (batch_dir / "aggregate_metrics.json").exists()
    assert (batch_dir / "aggregate_metrics.csv").exists()
    assert (batch_dir / "manifest.json").exists()
    assert (batch_dir / "README.md").exists()

    combined = "\n".join(path.read_text(encoding="utf-8") for path in batch_dir.iterdir() if path.is_file())
    assert "secret" not in combined
    assert "hidden" not in combined
    assert "prompt" not in combined
    assert "api_key" not in combined
    assert "redacted_field_1" in json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))["metadata"]


def test_batch_writer_overwrite_behavior(tmp_path):
    writer = StageBBatchWriter(tmp_path)
    writer.make_batch_dir("batch_test")
    with pytest.raises(FileExistsError):
        writer.make_batch_dir("batch_test")
    rewritten = StageBBatchWriter(tmp_path, overwrite=True).make_batch_dir("batch_test")
    assert rewritten.exists()
