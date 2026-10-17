"""Разбор моментов времени в московский часовой пояс.

Каждая функция принимает строки и возвращает tz-aware значения Europe/Moscow.
Нераспознанные непустые строки становятся NaT; их число считает вызывающий код.
"""
import pandas as pd

from prep.config import TZ


def parse_local(s: pd.Series, fmt: str) -> pd.Series:
    """Значения без часового пояса, записанные по Москве."""
    return pd.to_datetime(s, format=fmt, errors="coerce").dt.tz_localize(TZ)


def parse_current(s: pd.Series) -> pd.Series:
    """Новая система: ISO 8601 с суффиксом Z (UTC); без суффикса — Москва (подтверждено заказчиком)."""
    is_utc = s.str.endswith("Z")
    utc = pd.to_datetime(s[is_utc], format="%Y-%m-%dT%H:%M:%SZ", errors="coerce", utc=True).dt.tz_convert(TZ)
    local = parse_local(s[~is_utc], "%Y-%m-%dT%H:%M:%S")
    return pd.concat([utc, local]).reindex(s.index)


def parse_billing_month(s: pd.Series) -> pd.Series:
    """Месяц биллинга: основной формат YYYY-MM-DD, часть записей в DD.MM.YYYY."""
    iso = parse_local(s, "%Y-%m-%d")
    ru = parse_local(s, "%d.%m.%Y")
    return iso.fillna(ru)
