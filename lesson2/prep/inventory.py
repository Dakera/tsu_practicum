"""Шаг 1: инвентаризация источников — строки, ключи, фактические типы, временные диапазоны."""
import re

import pandas as pd

from prep import timeparse

LEGACY_FMT = "%d.%m.%Y %H:%M:%S"
BILLING_TS_FMT = "%Y-%m-%d %H:%M:%S"
DATE_FMT = "%Y-%m-%d"

# Паспорт источников: единица наблюдения, ключ, способ чтения и разбор временных полей.
SPEC = {
    "subscribers": {
        "unit": "абонент",
        "key": ["customer_id"],
        "read": "pandas.read_csv, все поля как строки",
        "time": {"activation_date": lambda s: timeparse.parse_local(s, DATE_FMT)},
    },
    "billing": {
        "unit": "абонент × месяц",
        "key": ["customer_id", "billing_month"],
        "read": "pandas.read_csv, все поля как строки",
        "time": {
            "billing_month": timeparse.parse_billing_month,
            "available_at": lambda s: timeparse.parse_local(s, BILLING_TS_FMT),
        },
    },
    "contract_events": {
        "unit": "событие договора",
        "key": ["event_id"],
        "read": "pandas.read_csv, все поля как строки",
        "time": {"event_date": lambda s: timeparse.parse_local(s, DATE_FMT)},
    },
    "support_legacy": {
        "unit": "обращение",
        "key": ["ticket_no"],
        "read": "pandas.read_csv, все поля как строки",
        "time": {c: (lambda s: timeparse.parse_local(s, LEGACY_FMT))
                 for c in ["opened_local", "loaded_local", "closed_local", "closed_loaded_local"]},
    },
    "support_current": {
        "unit": "обращение",
        "key": ["ticket_id"],
        "read": "sqlite3 (mode=ro) + prep/sql/support_current.sql",
        "time": {c: timeparse.parse_current
                 for c in ["created_at", "available_at", "resolved_at", "resolution_available_at"]},
    },
}

# Порядок важен: значение относится к первому совпавшему шаблону.
VALUE_TYPES = [
    ("empty", r""),
    ("int", r"-?\d+"),
    ("decimal_dot", r"-?\d+\.\d+"),
    ("decimal_comma", r"-?\d+,\d+"),
    ("date_iso", r"\d{4}-\d{2}-\d{2}"),
    ("date_ru", r"\d{2}\.\d{2}\.\d{4}"),
    ("datetime_space", r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"),
    ("datetime_utc_z", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"),
    ("datetime_no_tz", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"),
    ("datetime_ru", r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}"),
]
_COMPILED = [(name, re.compile(rf"^{p}$")) for name, p in VALUE_TYPES]


def value_type(v: str) -> str:
    for name, rx in _COMPILED:
        if rx.match(v):
            return name
    return "text"


def observed_types(s: pd.Series) -> str:
    counts = s.map(value_type).value_counts()
    return "; ".join(f"{t}:{n}" for t, n in counts.items())


def source_summary(name: str, df: pd.DataFrame) -> dict:
    spec = SPEC[name]
    key = spec["key"]
    return {
        "source": name,
        "read_method": spec["read"],
        "unit": spec["unit"],
        "key": "+".join(key),
        "rows": len(df),
        "columns": df.shape[1],
        "distinct_keys": len(df.drop_duplicates(key)),
        "rows_with_repeated_key": int(df.duplicated(key, keep=False).sum()),
    }


def column_summary(name: str, df: pd.DataFrame) -> list[dict]:
    rows = []
    for col in df.columns:
        row = {"source": name, "column": col, "observed_types": observed_types(df[col])}
        parser = SPEC[name]["time"].get(col)
        if parser is not None:
            parsed = parser(df[col])
            row["min_msk"] = parsed.min()
            row["max_msk"] = parsed.max()
            row["unparsed_nonempty"] = int((parsed.isna() & (df[col] != "")).sum())
        rows.append(row)
    return rows


def build(sources: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = pd.DataFrame([source_summary(n, df) for n, df in sources.items()])
    columns = pd.DataFrame([r for n, df in sources.items() for r in column_summary(n, df)])
    return summary, columns.astype({"unparsed_nonempty": "Int64"})
