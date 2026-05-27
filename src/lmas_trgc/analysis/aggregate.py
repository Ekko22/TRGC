from __future__ import annotations

import pandas as pd


def aggregate_mean(df: pd.DataFrame, group_cols: list[str], value_col: str) -> pd.DataFrame:
    return df.groupby(group_cols, as_index=False)[value_col].mean()
