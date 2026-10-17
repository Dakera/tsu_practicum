"""Step 2: data quality audit.

Every check returns a boolean row mask. The audit records:
  copies — extra full-duplicate rows (removed before all other checks),
  rows   — rows that fail a check,
  cells  — wrong cells; empty for checks on a relation between fields,
           where no single cell can be blamed.
All checks except the duplicate check run on unique rows, so a defect
copied together with its row is counted once.
"""
import pandas as pd

from prep import load, timeparse
from prep.config import TZ

DATE_FMT = "%Y-%m-%d"
BILLING_TS_FMT = "%Y-%m-%d %H:%M:%S"
LEGACY_TS_FMT = "%d.%m.%Y %H:%M:%S"
EXPORT_AT = pd.Timestamp("2026-10-01", tz=TZ)  # final export of support data

CUSTOMER_ID = r"C\d{6}"
TARIFF_FEE = {"Basic": 450.0, "Comfort": 750.0, "Premium": 1200.0}


def num(s: pd.Series) -> pd.Series:
    """Lenient number parsing for value checks; formats are checked separately."""
    return pd.to_numeric(s.str.strip().str.replace(",", ".", regex=False), errors="coerce")


def msk(date_str: pd.Series) -> pd.Series:
    return pd.to_datetime(date_str, format=DATE_FMT, errors="coerce").dt.tz_localize(TZ)


class Audit:
    def __init__(self, source: str, df: pd.DataFrame, key: list[str]):
        self.source = source
        self.records: list[dict] = []
        copies = df.duplicated()
        self._add("*", "Полная повторная копия строки", copies=int(copies.sum()))
        self.df = df[~copies]
        self.bad = pd.Series(False, index=self.df.index)
        same_key = self.df.duplicated(key, keep=False)
        self.check("+".join(key), "Один ключ, разные значения (конфликт)", same_key)

    def _add(self, field, problem, rows=None, cells=None, copies=None):
        self.records.append({"source": self.source, "field": field, "problem": problem,
                             "rows": rows, "cells": cells, "copies": copies})

    def check(self, field: str, problem: str, mask: pd.Series, relation: bool = False) -> None:
        mask = mask.fillna(False).astype(bool)
        self.bad |= mask
        n = int(mask.sum())
        self._add(field, problem, rows=n, cells=None if relation else n)

    def missing(self, *cols: str) -> None:
        for c in cols:
            self.check(c, "Пропуск", self.df[c].str.strip() == "")

    def bad_format(self, col: str, pattern: str, expected: str) -> None:
        s = self.df[col]
        self.check(col, f"Формат не {expected}", (s != "") & ~s.str.fullmatch(pattern))

    def not_in(self, col: str, allowed) -> None:
        s = self.df[col]
        self.check(col, f"Значение вне {sorted(allowed)}", (s != "") & ~s.isin(allowed))

    def unknown_customer(self, col: str, ids: set) -> None:
        s = self.df[col].str.strip()  # surrounding spaces are insignificant per schema
        self.check(col, "Абонент не найден в реестре", (s != "") & ~s.isin(ids))

    def summary(self) -> dict:
        cells = sum(r["cells"] or 0 for r in self.records)
        return {"source": self.source, "field": "ИТОГО",
                "problem": "Уникальных строк с хотя бы одной проблемой",
                "rows": int(self.bad.sum()), "cells": cells, "copies": self.records[0]["copies"]}


def customer_dates(events: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Activation and termination dates per customer from the contract journal."""
    ev = events.assign(d=msk(events.event_date))
    first = ev.sort_values("d").drop_duplicates(["customer_id", "event_type"])
    by_type = first.pivot(index="customer_id", columns="event_type", values="d")
    return by_type["activation"], by_type["termination"]


def audit_subscribers(df: pd.DataFrame, events: pd.DataFrame) -> Audit:
    a = Audit("subscribers", df, ["customer_id"])
    d = a.df
    a.bad_format("customer_id", CUSTOMER_ID, "CNNNNNN")
    a.missing("activation_date")
    a.bad_format("activation_date", r"\d{4}-\d{2}-\d{2}", "YYYY-MM-DD")
    a.not_in("region", {"Москва", "Московская область", "Новосибирская область", "Томская область", "Красноярский край"})
    a.not_in("acquisition_channel", {"online", "store", "partner"})
    a.not_in("customer_segment", {"individual", "small_business"})
    act, _ = customer_dates(events)
    ev_act = d.customer_id.map(act)
    own = msk(d.activation_date)
    a.check("activation_date", "Расходится с activation в журнале договора", own.notna() & (own != ev_act), relation=True)
    a.check("activation_date", "Нет activation в журнале договора", ev_act.isna(), relation=True)
    return a


def audit_events(df: pd.DataFrame, ids: set) -> Audit:
    a = Audit("contract_events", df, ["event_id"])
    d = a.df
    a.bad_format("event_id", r"E\d{7}", "ENNNNNNN")
    a.bad_format("event_date", r"\d{4}-\d{2}-\d{2}", "YYYY-MM-DD")
    a.not_in("event_type", {"activation", "termination"})
    a.unknown_customer("customer_id", ids)
    counts = d.groupby(["customer_id", "event_type"]).event_id.transform("size")
    a.check("event_type", "Больше одного события этого типа у абонента", counts > 1, relation=True)
    act, term = customer_dates(d)
    t = d.customer_id.map(term)
    a.check("event_date", "Расторжение не позже подключения",
            (d.event_type == "termination") & (t <= d.customer_id.map(act)), relation=True)
    return a


def audit_billing(df: pd.DataFrame, ids: set, events: pd.DataFrame) -> Audit:
    a = Audit("billing", df, ["customer_id", "billing_month"])
    d = a.df
    month = timeparse.parse_billing_month(d.billing_month)
    a.bad_format("customer_id", CUSTOMER_ID, "CNNNNNN")
    a.unknown_customer("customer_id", ids)
    a.bad_format("billing_month", r"\d{4}-\d{2}-01", "YYYY-MM-01")
    a.check("available_at", "Не первое число следующего месяца 00:00",
            timeparse.parse_local(d.available_at, BILLING_TS_FMT) != month + pd.offsets.MonthBegin(1), relation=True)

    a.not_in("tariff", set(TARIFF_FEE))
    fee = num(d.monthly_fee_rub)
    a.check("monthly_fee_rub", "Не равна цене тарифа",
            d.tariff.isin(set(TARIFF_FEE)) & (fee != d.tariff.map(TARIFF_FEE)), relation=True)

    money = ["monthly_fee_rub", "charged_rub", "paid_rub", "opening_debt_rub", "closing_debt_rub"]
    for c in money + ["traffic_gb"]:
        a.bad_format(c, r"\d+\.\d{2}", "N.NN")
    for c in ["voice_minutes", "active_days", "payment_delay_days", "tariff_changes_count"]:
        a.bad_format(c, r"-?\d+", "целое")
    a.missing(*money, "traffic_gb", "voice_minutes", "active_days", "payment_delay_days", "tariff_changes_count")
    for c in money + ["traffic_gb", "voice_minutes"]:
        a.check(c, "Отрицательное значение", num(d[c]) < 0)

    days = month.dt.days_in_month
    a.check("active_days", "Вне [0, дней в месяце]", (num(d.active_days) < 0) | (num(d.active_days) > days))
    a.check("payment_delay_days", "Вне [0, дней в месяце]",
            (num(d.payment_delay_days) < 0) | (num(d.payment_delay_days) > days))
    a.not_in("tariff_changes_count", {"0", "1"})

    opening, charged, paid, closing = (num(d[c]) for c in ["opening_debt_rub", "charged_rub", "paid_rub", "closing_debt_rub"])
    a.check("closing_debt_rub", "opening + charged − paid ≠ closing (±0.005)",
            (opening + charged - paid - closing).abs() > 0.005, relation=True)

    order = pd.DataFrame({"cid": d.customer_id, "m": month, "opening": opening, "closing": closing}).sort_values(["cid", "m"])
    prev_closing = order.groupby("cid").closing.shift()
    is_first = order.groupby("cid").cumcount() == 0
    a.check("opening_debt_rub", "Не равен closing предыдущего месяца",
            ((order.opening - prev_closing).abs() > 0.005).reindex(d.index), relation=True)
    a.check("opening_debt_rub", "Не ноль в первой строке абонента",
            (is_first & (order.opening.abs() > 0.005)).reindex(d.index), relation=True)
    gap = order.groupby("cid").m.diff().dt.days > 31
    a.check("billing_month", "Пропущен месяц перед этой строкой", gap.reindex(d.index), relation=True)

    act, term = customer_dates(events)
    act_month = d.customer_id.map(act).dt.tz_localize(None).dt.to_period("M").dt.start_time.dt.tz_localize(TZ)
    a.check("billing_month", "Месяц раньше месяца подключения", month < act_month, relation=True)
    a.check("billing_month", "Месяц начинается после расторжения", month >= d.customer_id.map(term), relation=True)
    return a


def support_variant(system: str, schema: pd.DataFrame) -> dict:
    if system == "legacy":
        return {"parse": lambda s: timeparse.parse_local(s, LEGACY_TS_FMT),
                "ts_pattern": r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}", "ts_name": "DD.MM.YYYY HH:MM:SS",
                "topics": set(load.value_map(schema, "topic")), "channels": set(load.value_map(schema, "channel")),
                "window": ("2025-09-01", "2025-11-01")}
    return {"parse": timeparse.parse_current,
            "ts_pattern": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "ts_name": "ISO 8601 с Z",
            "topics": set(load.value_map(schema, "topic").values()),
            "channels": set(load.value_map(schema, "channel").values()),
            "window": ("2025-11-01", "2026-09-01")}


def audit_support(df: pd.DataFrame, system: str, schema: pd.DataFrame, ids: set, events: pd.DataFrame) -> Audit:
    """Legacy columns are renamed to the canonical schema first; values stay untouched."""
    if system == "legacy":
        df = df.rename(columns=load.legacy_renames(schema))
    v = support_variant(system, schema)
    a = Audit(f"support_{system}", df, ["ticket_id"])
    d = a.df

    a.bad_format("ticket_id", r"T\d{7}", "TNNNNNNN")
    a.missing("customer_id")
    a.bad_format("customer_id", CUSTOMER_ID, "CNNNNNN (без пробелов)")
    a.unknown_customer("customer_id", ids)
    a.missing("created_at", "available_at", "topic", "channel")
    for c in ["created_at", "available_at", "resolved_at", "resolution_available_at"]:
        a.bad_format(c, v["ts_pattern"], v["ts_name"])
    a.not_in("topic", v["topics"])
    a.not_in("channel", v["channels"])
    score = num(d.satisfaction_score)
    a.check("satisfaction_score", "Вне целых 1–5",
            (d.satisfaction_score != "") & ~(score.isin([1, 2, 3, 4, 5])))

    created, available, resolved, res_avail = (v["parse"](d[c]) for c in
                                               ["created_at", "available_at", "resolved_at", "resolution_available_at"])
    lo, hi = (pd.Timestamp(x, tz=TZ) for x in v["window"])
    a.check("created_at", f"Вне периода системы [{v['window'][0]}, {v['window'][1]})",
            (created < lo) | (created >= hi), relation=True)
    a.check("available_at", "Раньше created_at", available < created, relation=True)
    a.check("resolved_at", "Раньше created_at", resolved < created, relation=True)
    a.check("resolution_available_at", "Раньше resolved_at", res_avail < resolved, relation=True)
    a.check("resolution_available_at", "Раньше available_at", res_avail < available, relation=True)
    a.check("resolved_at", "Заполнено только одно из resolved_at / resolution_available_at",
            resolved.isna() != res_avail.isna(), relation=True)
    a.check("available_at", "Позже финальной выгрузки 2026-10-01",
            (available > EXPORT_AT) | (res_avail > EXPORT_AT), relation=True)
    a.check("satisfaction_score", "Оценка без подтверждённого закрытия",
            (d.satisfaction_score != "") & resolved.isna(), relation=True)

    act, term = customer_dates(events)
    cid = d.customer_id.str.strip()
    a.check("created_at", "Создано до подключения абонента", created < cid.map(act), relation=True)
    a.check("created_at", "Создано после расторжения договора", created >= cid.map(term), relation=True)
    return a


def run(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    schema = load.read_support_schema()
    events = sources["contract_events"]
    ids = set(sources["subscribers"].customer_id)
    audits = [
        audit_subscribers(sources["subscribers"], events),
        audit_events(events, ids),
        audit_billing(sources["billing"], ids, events),
        audit_support(sources["support_legacy"], "legacy", schema, ids, events),
        audit_support(sources["support_current"], "current", schema, ids, events),
    ]
    legacy_ids = set(sources["support_legacy"].ticket_no)
    overlap = sources["support_current"].ticket_id.isin(legacy_ids)
    records = [r for a in audits for r in a.records + [a.summary()]]
    records.append({"source": "support_legacy+current", "field": "ticket_id",
                    "problem": "Номер обращения есть в обеих системах", "rows": int(overlap.sum()),
                    "cells": None, "copies": None})
    out = pd.DataFrame(records).astype({"rows": "Int64", "cells": "Int64", "copies": "Int64"})
    return out
