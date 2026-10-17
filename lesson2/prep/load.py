"""Чтение исходных источников без преобразования значений.

Все поля читаются как строки, пустое поле остаётся пустой строкой.
Так дефекты исходных данных (десятичная запятая, ' basic ', 'X0001234')
доходят до аудита в исходном виде, а не теряются при автоматическом
приведении типов.
"""
import sqlite3
from pathlib import Path

import pandas as pd

from prep import config

SQL_SUPPORT_CURRENT = Path(__file__).parent / "sql" / "support_current.sql"


def read_raw_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)


def read_support_current(db_path: Path) -> pd.DataFrame:
    """Читает SQLite в режиме только чтения: файл базы не может быть изменён."""
    query = SQL_SUPPORT_CURRENT.read_text(encoding="utf-8")
    with sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True) as conn:
        df = pd.read_sql_query(query, conn, dtype=str)
    n_null = int(df.isna().sum().sum())
    if n_null:
        # В текущей выгрузке пустые значения хранятся как ''. Если появится NULL,
        # правила подсчёта пропусков нужно пересмотреть — останавливаемся.
        raise ValueError(f"support_current_raw содержит {n_null} NULL-ячеек; ожидались только пустые строки")
    return df


def load_sources() -> dict[str, pd.DataFrame]:
    return {
        "subscribers": read_raw_csv(config.SUBSCRIBERS),
        "billing": read_raw_csv(config.BILLING),
        "contract_events": read_raw_csv(config.EVENTS),
        "support_legacy": read_raw_csv(config.SUPPORT_LEGACY),
        "support_current": read_support_current(config.SUPPORT_DB),
    }
