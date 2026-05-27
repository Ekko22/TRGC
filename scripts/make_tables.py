#!/usr/bin/env python
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Build publication tables from aggregated results.")
    parser.add_argument("--input", default="results/tables")
    parser.add_argument("--output", default="results/tables")
    args = parser.parse_args()
    print({"script": "make_tables", "input": args.input, "output": args.output})


if __name__ == "__main__":
    main()
