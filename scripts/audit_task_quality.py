#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.tasks.quality import audit_task_quality, write_json_report, write_markdown_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit processed task datasets and the active main manifest.")
    parser.add_argument("--processed-public-dir", default="data/processed/public")
    parser.add_argument("--synthetic-dir", default="data/processed/synthetic")
    parser.add_argument("--manifest-path", default="data/manifests/main_manifest.json")
    parser.add_argument("--report-path", default="data/manifests/task_quality_report.json")
    parser.add_argument("--markdown-report-path", default="docs/dev_logs/0015_data_quality_audit.md")
    parser.add_argument("--require-full", action="store_true", default=False)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = audit_task_quality(
        processed_public_dir=Path(args.processed_public_dir),
        synthetic_dir=Path(args.synthetic_dir),
        manifest_path=Path(args.manifest_path),
    )
    write_json_report(report, Path(args.report_path))
    write_markdown_report(report, Path(args.markdown_report_path))

    summary = {
        "overall_status": report["overall_status"],
        "expected_total_tasks": report["expected_total_tasks"],
        "manifest_total_tasks": report["manifest_total_tasks"],
        "total_errors": report["summary"]["total_errors"],
        "total_warnings": report["summary"]["total_warnings"],
        "datasets_ready": report["summary"]["datasets_ready"],
        "datasets_failed": report["summary"]["datasets_failed"],
        "can_run_main_manifest": report["summary"]["can_run_main_manifest"],
        "report_path": args.report_path,
        "markdown_report_path": args.markdown_report_path,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"overall_status: {summary['overall_status']}")
        print(f"manifest_total_tasks: {summary['manifest_total_tasks']}")
        print(f"total_errors: {summary['total_errors']}")
        print(f"total_warnings: {summary['total_warnings']}")
        print(f"report_path: {summary['report_path']}")
        print(f"markdown_report_path: {summary['markdown_report_path']}")
    if args.require_full and report["overall_status"] == "fail":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
