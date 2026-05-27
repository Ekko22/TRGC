#!/usr/bin/env python
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate LMAS-TRGC result files.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print({"script": "aggregate_results", "input": args.input, "output": args.output})


if __name__ == "__main__":
    main()
