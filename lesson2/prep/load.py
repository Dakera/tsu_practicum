"""Read raw sources without converting any values.

Every field is read as a string and an empty field stays an empty string.
This way source defects (decimal comma, ' basic ', 'X0001234') reach the
audit unchanged instead of being lost to automatic type inference.
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

from prep import config

SQL_SUPPORT_CURRENT = Path(__file__).parent / "sql" / "support_current.sql"


def read_raw_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)


def read_support_current(db_path: Path) -> pd.DataFrame:
    """Open SQLite read-only so the database file cannot be modified."""
    query = SQL_SUPPORT_CURRENT.read_text(encoding="utf-8")
    with sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True) as conn:
        df = pd.read_sql_query(query, conn, dtype=str)
    n_null = int(df.isna().sum().sum())
    if n_null:
        # The current export stores missing values as ''. A NULL would change
        # how missing values are counted, so stop instead of guessing.
        raise ValueError(f"support_current_raw содержит {n_null} NULL-ячеек; ожидались только пустые строки")
    return df


def read_support_schema() -> pd.DataFrame:
    """Field mapping between the legacy and current support systems (schema_support.csv)."""
    return read_raw_csv(config.SUPPORT_SCHEMA)


def legacy_renames(schema: pd.DataFrame) -> dict[str, str]:
    return dict(zip(schema.legacy_field, schema.canonical_field))


def value_map(schema: pd.DataFrame, field: str) -> dict[str, str]:
    """Parse 'Русское название=code; ...' pairs from the rules column of a schema field."""
    rules = schema.loc[schema.canonical_field == field, "rules"].item()
    pairs = dict((ru.strip(), code) for ru, code in re.findall(r"([^;=.]+)=(\w+)", rules))
    if not pairs:
        raise ValueError(f"schema_support.csv: no value mapping found for {field}")
    return pairs


def load_sources() -> dict[str, pd.DataFrame]:
    return {
        "subscribers": read_raw_csv(config.SUBSCRIBERS),
        "billing": read_raw_csv(config.BILLING),
        "contract_events": read_raw_csv(config.EVENTS),
        "support_legacy": read_raw_csv(config.SUPPORT_LEGACY),
        "support_current": read_support_current(config.SUPPORT_DB),
    }
