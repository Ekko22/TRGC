#!/usr/bin/env python
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Build figures from aggregated LMAS-TRGC results.")
    parser.add_argument("--input", default="results/tables")
    parser.add_argument("--output", default="results/figures")
    args = parser.parse_args()
    print({"script": "make_figures", "input": args.input, "output": args.output})


if __name__ == "__main__":
    main()
