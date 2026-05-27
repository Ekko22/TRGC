#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.core.config import load_yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Describe main experiment matrix configuration.")
    parser.add_argument("--config", default="configs/experiment_main.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_yaml(args.config)
    print(
        {
            "script": "run_main_matrix",
            "dry_run": args.dry_run,
            "stage": config.get("stage"),
            "expected_runs": config.get("expected_runs"),
        }
    )


if __name__ == "__main__":
    main()
