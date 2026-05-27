from __future__ import annotations

import pandas as pd


def to_markdown_table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)
