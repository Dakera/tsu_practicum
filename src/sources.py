"""Чтение исходных CSV, разбор форматов и правило активной базы.

Модуль ничего не печатает и не считает показатели для отчёта: все числа устава
получаются в notebooks/01_charter_checks.ipynb, который вызывает эти функции.
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent
FIRST_T = "2025-09-01"
LAST_T = "2026-10-01"                     # боевая дата: исход неизвестен
EVENTS_END = pd.Timestamp("2026-10-01")   # журнал полон до этой даты, не включая её
CAMPAIGN_SHARE = 0.10


def read(name: str) -> pd.DataFrame:
    """Исходный CSV как строки, без преобразований."""
    return pd.read_csv(DATA_DIR / name, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)


def to_num(s: pd.Series) -> pd.Series:
    """Число с точкой или запятой; пустая строка -> NaN."""
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")


def parse_billing_month(s: pd.Series) -> pd.Series:
    """billing_month в форматах ГГГГ-ММ-ДД и ДД.ММ.ГГГГ. Падает на любом другом."""
    iso = s.str.match(r"^\d{4}-\d{2}-\d{2}$")
    ru = s.str.match(r"^\d{2}\.\d{2}\.\d{4}$")
    if not (iso | ru).all():
        raise ValueError(f"Неизвестный формат billing_month: {s[~(iso | ru)].unique()[:5]}")
    out = pd.to_datetime(s.where(iso), format="%Y-%m-%d")
    return out.fillna(pd.to_datetime(s.where(ru), format="%d.%m.%Y"))


def contract_dates(events: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Даты подключения и расторжения по абоненту. Падает, если нарушено правило словаря."""
    counts = events.groupby(["customer_id", "event_type"]).size().unstack(fill_value=0)
    if (counts["activation"] != 1).any() or (counts.get("termination", 0) > 1).any():
        raise ValueError("Нарушено правило: одно подключение и не более одного расторжения")
    dates = pd.to_datetime(events.event_date, format="%Y-%m-%d")
    is_act = events.event_type == "activation"
    is_term = events.event_type == "termination"
    act = dates[is_act].set_axis(events.customer_id[is_act])
    term = dates[is_term].set_axis(events.customer_id[is_term]).reindex(act.index)
    if (term <= act).any():
        raise ValueError("Расторжение не позже подключения")
    return act, term


def active_base(act: pd.Series, term: pd.Series, T: pd.Timestamp) -> pd.Index:
    """Активная база на T: подключён до T и не расторг до T."""
    return act.index[(act < T) & ~(term < T)]


def snapshot_table(billing: pd.DataFrame, act: pd.Series, term: pd.Series) -> pd.DataFrame:
    """Активная база, отток и короткая история на каждую дату расчёта T.

    billing — без дублей ключа, с колонкой bm (месяц как дата).
    """
    if billing.duplicated(["customer_id", "bm"]).any():
        raise ValueError("В биллинге дубли ключа: сначала удалите их")
    available = pd.to_datetime(billing.available_at)
    rows = []
    for T in pd.date_range(FIRST_T, LAST_T, freq="MS"):
        t_next = T + pd.DateOffset(months=1)
        base = active_base(act, term, T)
        months_seen = billing[(available <= T) & billing.customer_id.isin(base)].groupby("customer_id").size()
        months_seen = months_seen.reindex(base, fill_value=0)
        known = t_next <= EVENTS_END
        churn = int(((term[base] >= T) & (term[base] < t_next)).sum()) if known else None
        rows.append({
            "T": T.date(),
            "N": len(base),
            "K": int(len(base) * CAMPAIGN_SHARE),
            "churners": churn,
            "churn_%": round(churn / len(base) * 100, 2) if known else None,
            "no_billing": int((months_seen == 0).sum()),
            "billing_lt_3m": int((months_seen < 3).sum()),
        })
    return pd.DataFrame(rows)
