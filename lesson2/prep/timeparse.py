"""Parse timestamps into the Moscow time zone.

Each function takes strings and returns tz-aware Europe/Moscow values.
Unrecognised non-empty strings become NaT; the caller counts them.
"""
import pandas as pd

from prep.config import TZ


def parse_local(s: pd.Series, fmt: str) -> pd.Series:
    """Values without a time zone, recorded in Moscow time."""
    return pd.to_datetime(s, format=fmt, errors="coerce").dt.tz_localize(TZ)


def parse_current(s: pd.Series) -> pd.Series:
    """Current system: ISO 8601 with Z suffix is UTC; without suffix it is Moscow time (confirmed by the client)."""
    is_utc = s.str.endswith("Z")
    utc = pd.to_datetime(s[is_utc], format="%Y-%m-%dT%H:%M:%SZ", errors="coerce", utc=True).dt.tz_convert(TZ)
    local = parse_local(s[~is_utc], "%Y-%m-%dT%H:%M:%S")
    return pd.concat([utc, local]).reindex(s.index)


def parse_billing_month(s: pd.Series) -> pd.Series:
    """Billing month: mostly YYYY-MM-DD, some rows in DD.MM.YYYY."""
    iso = parse_local(s, "%Y-%m-%d")
    ru = parse_local(s, "%d.%m.%Y")
    return iso.fillna(ru)


def parse_iso_offset(s: pd.Series) -> pd.Series:
    """Prepared tables: ISO 8601 with an explicit offset, e.g. 2026-08-18T21:32:58+03:00."""
    return pd.to_datetime(s, format="%Y-%m-%dT%H:%M:%S%z", errors="coerce").dt.tz_convert(TZ)


def format_iso_offset(s: pd.Series) -> pd.Series:
    """Inverse of parse_iso_offset; missing values become empty strings."""
    return s.map(lambda t: "" if pd.isna(t) else t.isoformat())
