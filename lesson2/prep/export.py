"""Write prepared tables as CSV in one consistent text format.

UTF-8 with BOM, ';' separator (as the sources), dates YYYY-MM-DD,
moments ISO 8601 with +03:00, decimals with a dot and two digits,
missing values as empty fields.
"""
from pathlib import Path

import pandas as pd

from prep import timeparse


def to_text(df: pd.DataFrame, date_cols: tuple[str, ...] = ()) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if c in date_cols:
            out[c] = out[c].dt.strftime("%Y-%m-%d").fillna("")
        elif isinstance(out[c].dtype, pd.DatetimeTZDtype):
            out[c] = timeparse.format_iso_offset(out[c])
    return out


def write_csv(df: pd.DataFrame, path: Path, date_cols: tuple[str, ...] = ()) -> None:
    to_text(df, date_cols).to_csv(path, sep=";", index=False, encoding="utf-8-sig", float_format="%.2f")
