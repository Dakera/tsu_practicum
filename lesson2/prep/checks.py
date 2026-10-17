"""Step 5: availability and join checks.

Small synthetic cases run through the same functions as the real pipeline,
plus invariants on the real customer_month. Any failed check stops the run.
"""
import numpy as np
import pandas as pd

from prep import clean, merge
from prep.config import TZ

MONEY = ["charged_rub", "paid_rub", "opening_debt_rub", "closing_debt_rub"]


def ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz=TZ)


def billing_rows(*pairs: tuple[str, str]) -> pd.DataFrame:
    rows = [{"customer_id": c, "billing_month": ts(m), "available_at": ts(m) + pd.offsets.MonthBegin(1)}
            for c, m in pairs]
    return pd.DataFrame(rows)


def ticket(tid, cid, created, available, topic="network", resolved=None, resolution_available=None, score=None):
    return {"ticket_id": tid, "customer_id": cid, "source_system": "test", "created_at": ts(created),
            "available_at": ts(available), "topic": topic, "channel": "chat",
            "resolved_at": ts(resolved) if resolved else pd.NaT,
            "resolution_available_at": ts(resolution_available) if resolution_available else pd.NaT,
            "satisfaction_score": score, "resolution_invalid": False, "score_invalid": False}


def tickets(*rows) -> pd.DataFrame:
    df = pd.DataFrame(list(rows))
    for c in ["created_at", "available_at", "resolved_at", "resolution_available_at"]:
        df[c] = pd.to_datetime(df[c], utc=True).dt.tz_convert(TZ)  # an all-NaT column must stay tz-aware
    df["satisfaction_score"] = df.satisfaction_score.astype("Int64")
    return df


def subscribers_for(billing: pd.DataFrame) -> pd.DataFrame:
    ids = billing.customer_id.drop_duplicates()
    return pd.DataFrame({"customer_id": ids, "region": "Москва", "acquisition_channel": "online",
                         "customer_segment": "individual", "activation_date": ts("2020-01-01"),
                         "activation_date_restored": False})


def no_quarantine() -> pd.DataFrame:
    return pd.DataFrame({"customer_id": pd.Series(dtype=str), "created_at": pd.Series(dtype=f"datetime64[ns, {TZ}]"),
                         "linked_to_customer": pd.Series(dtype=bool)})


def month_row(billing, support, customer="C1", month="2026-08-01") -> pd.Series:
    cm = merge.build_customer_month(billing, subscribers_for(billing), support, no_quarantine())
    return cm[(cm.customer_id == customer) & (cm.billing_month == ts(month))].iloc[0]


def result(name: str, expected: str, actual: str, passed: bool) -> dict:
    return {"check": name, "expected": expected, "result": actual, "passed": bool(passed)}


def check_repeated_row() -> dict:
    t = ticket("T1", "C1", "2026-08-10 12:00", "2026-08-11 09:00")
    raw = tickets(t, t)  # the same row delivered twice
    deduped = clean.drop_full_duplicates(raw, ["ticket_id"], "test", clean.DecisionLog())
    n = month_row(billing_rows(("C1", "2026-08-01")), deduped).support_count
    return result("Повтор обращения", "support_count = 1 при двух одинаковых строках", f"support_count = {n}", n == 1)


def check_late_arrival() -> list[dict]:
    billing = billing_rows(("C1", "2026-08-01"))
    late = month_row(billing, tickets(ticket("T1", "C1", "2026-08-31 23:00", "2026-09-01 09:00"))).support_count
    on_time = month_row(billing, tickets(ticket("T1", "C1", "2026-08-31 23:00", "2026-09-01 00:00"))).support_count
    return [
        result("Позднее поступление", "Создано 31.08 23:00, загружено 01.09 09:00 → не в августе",
               f"support_count = {late}", late == 0),
        result("Граница снимка", "Загружено ровно 01.09 00:00 → в августе (≤ момента снимка)",
               f"support_count = {on_time}", on_time == 1),
    ]


def check_customer_without_tickets() -> dict:
    billing = billing_rows(("C1", "2026-08-01"), ("C2", "2026-08-01"))
    support = tickets(ticket("T1", "C1", "2026-08-10 12:00", "2026-08-11 09:00"))
    cm = merge.build_customer_month(billing, subscribers_for(billing), support, no_quarantine())
    row = cm[cm.customer_id == "C2"]
    ok = len(cm) == 2 and len(row) == 1 and row.support_count.item() == 0 and pd.isna(row.support_score_mean.item())
    return result("Абонент без обращений", "Строка сохраняется, support_count = 0, средняя оценка пуста",
                  f"строк {len(cm)}, у C2: count = {row.support_count.item()}, mean = {row.support_score_mean.item()}", ok)


def check_closure_after_snapshot() -> dict:
    support = tickets(ticket("T1", "C1", "2026-08-10 12:00", "2026-08-11 09:00",
                             resolved="2026-08-31 20:00", resolution_available="2026-09-01 08:00", score=5))
    row = month_row(billing_rows(("C1", "2026-08-01")), support)
    ok = row.support_count == 1 and row.support_resolved_count == 0 and row.support_score_count == 0
    return result("Закрытие после снимка", "Обращение учтено, закрытие и оценка — нет",
                  f"count = {row.support_count}, resolved = {row.support_resolved_count}, "
                  f"scores = {row.support_score_count}", ok)


def check_real(customer_month: pd.DataFrame, billing: pd.DataFrame, coverage: dict) -> list[dict]:
    sums_equal = all(np.isclose(customer_month[c].sum(), billing[c].sum(), rtol=0, atol=0.005) for c in MONEY)
    key_unique = not customer_month.duplicated(merge.KEY).any()
    future = [c for c in customer_month.columns if "termination" in c]
    counted = int(customer_month.support_count.sum())
    return [
        result("Объединение биллинга", "Строки и суммы не изменились",
               f"строк {len(customer_month)} из {len(billing)}; суммы {', '.join(MONEY)} совпадают: {sums_equal}",
               len(customer_month) == len(billing) and sums_equal),
        result("Ключ customer_month", "customer_id + billing_month уникален", f"уникален: {key_unique}", key_unique),
        result("Будущие расторжения", "Нет полей termination в признаках", f"найдено: {future or 'нет'}", not future),
        result("Сверка счётчика", "Σ support_count = обращения, доступные к своему снимку",
               f"{counted} = {coverage['tickets_in_snapshot']}; после снимка: {coverage['tickets_after_snapshot']}; "
               f"без строки биллинга: {coverage['tickets_without_billing_row']}",
               counted == coverage["tickets_in_snapshot"] and coverage["tickets_without_billing_row"] == 0),
    ]


def run(customer_month: pd.DataFrame, billing: pd.DataFrame, coverage: dict) -> pd.DataFrame:
    rows = [check_repeated_row(), *check_late_arrival(), check_customer_without_tickets(),
            check_closure_after_snapshot(), *check_real(customer_month, billing, coverage)]
    return pd.DataFrame(rows)
