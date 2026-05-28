#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.analysis.diagnostics import (  # noqa: E402
    build_json_report,
    load_diagnostic_artifacts,
    render_markdown_report,
    run_all_analyses,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose a completed DeepSeek manifest pilot batch from local artifacts.")
    parser.add_argument(
        "--batch-dir",
        default="results/runs/stage_c_manifest_batches/stage_c_deepseek_diag_graph_mp_22x4",
    )
    parser.add_argument(
        "--output-json",
        default="data/manifests/deepseek_diagnostic_audit.json",
    )
    parser.add_argument(
        "--output-md",
        default="docs/dev_logs/0020_deepseek_diagnostic_root_cause.md",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-examples-per-section", type=int, default=5)
    args = parser.parse_args()

    try:
        batch_dir = Path(args.batch_dir)
        if not batch_dir.exists():
            raise FileNotFoundError(f"diagnostic batch artifact not found; cannot audit without local artifacts: {batch_dir}")

        records = load_diagnostic_artifacts(batch_dir)
        analyses = run_all_analyses(records)
        report = build_json_report(batch_dir, records, analyses)

        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(
            render_markdown_report(report, max_examples_per_section=args.max_examples_per_section),
            encoding="utf-8",
        )

        if args.json:
            print(json.dumps({**report, "output_json": str(output_json), "output_md": str(output_md)}, ensure_ascii=False, indent=2))
        else:
            decision = report["root_cause_decision"]
            print("# DeepSeek Diagnostic Root Cause Audit")
            print(f"- batch_dir: {batch_dir}")
            print(f"- total_runs: {report['total_runs']}")
            print(f"- should_scale_experiment: {decision['should_scale_experiment']}")
            print(f"- recommended_next_step: {decision['recommended_next_step']}")
            print(f"- output_json: {output_json}")
            print(f"- output_md: {output_md}")
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        else:
            print(f"DeepSeek diagnostic audit failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
