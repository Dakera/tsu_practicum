"""Step 3: format alignment and cleaning.

Each function takes raw string tables and returns typed clean tables.
Every action is written to a decision log with the number of affected records,
so the report quotes counts produced by code, not by hand.
Unexpected states (a new tariff spelling, a key conflict, an unrestorable debt)
raise instead of being silently patched: the rules below were derived from the
data as delivered and must be revisited if the data changes.
"""
import pandas as pd

from prep import load, timeparse
from prep.audit import LEGACY_TS_FMT, TARIFF_FEE, msk, num, customer_dates

BILLING_TS_FMT = "%Y-%m-%d %H:%M:%S"
TARIFF_SPELLINGS = {"basic": "Basic", "comfort": "Comfort", "premium": "Premium", "премиум": "Premium"}


class DecisionLog:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, source, field, problem, action, rationale, affected, unit="строки"):
        self.rows.append({"source": source, "field": field, "problem": problem, "action": action,
                          "rationale": rationale, "affected": int(affected), "unit": unit})

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def drop_full_duplicates(df: pd.DataFrame, key: list[str], source: str, log: DecisionLog) -> pd.DataFrame:
    copies = df.duplicated()
    log.add(source, "*", "Полная повторная копия строки", "Удалена, оставлена первая копия",
            "Идентичная строка не несёт новой информации и удваивает счётчики", copies.sum(), "копии")
    out = df[~copies]
    conflicts = out.duplicated(key, keep=False)
    if conflicts.any():
        raise ValueError(f"{source}: {conflicts.sum()} rows share a key with different values; review needed")
    return out


# ---------------------------------------------------------------- subscribers

def clean_subscribers(raw: pd.DataFrame, events: pd.DataFrame, log: DecisionLog) -> pd.DataFrame:
    df = drop_full_duplicates(raw, ["customer_id"], "subscribers", log).copy()
    own = msk(df.activation_date)
    act, _ = customer_dates(events)
    from_journal = df.customer_id.map(act)

    if (own.notna() & (own != from_journal)).any():
        raise ValueError("subscribers: activation_date contradicts contract_events; restoring by journal is unsafe")

    missing = own.isna()
    restorable = missing & from_journal.notna()
    df["activation_date"] = own.fillna(from_journal)
    df["activation_date_restored"] = restorable
    log.add("subscribers", "activation_date", "Пропуск даты подключения",
            "Восстановлена по событию activation из contract_events",
            "У абонента ровно одно activation; для заполненных дат журнал совпадает с реестром во всех строках",
            restorable.sum())
    log.add("subscribers", "activation_date", "Пропуск, не восстанавливаемый по журналу",
            "Оставлен пропуск, абонент сохранён", "Удалять абонента целиком запрещено", (missing & ~restorable).sum())
    return df


# ------------------------------------------------------------ contract events

def clean_events(raw: pd.DataFrame, log: DecisionLog) -> pd.DataFrame:
    df = drop_full_duplicates(raw, ["event_id"], "contract_events", log).copy()
    df["event_date"] = msk(df.event_date)
    return df


# -------------------------------------------------------------------- billing

def clean_billing(raw: pd.DataFrame, log: DecisionLog) -> pd.DataFrame:
    df = drop_full_duplicates(raw, ["customer_id", "billing_month"], "billing", log).copy()

    ru_month = df.billing_month.str.contains(".", regex=False)
    df["billing_month"] = timeparse.parse_billing_month(df.billing_month)
    log.add("billing", "billing_month", "Формат DD.MM.YYYY", "Приведён к YYYY-MM-DD",
            "Тот же месяц в другом формате; после приведения ключ остаётся уникальным", ru_month.sum())
    df["available_at"] = timeparse.parse_local(df.available_at, BILLING_TS_FMT)

    spelled = df.tariff.str.strip().str.casefold()
    unknown = set(spelled) - set(TARIFF_SPELLINGS)
    if unknown:
        raise ValueError(f"billing: unknown tariff spellings {unknown}")
    canonical = spelled.map(TARIFF_SPELLINGS)
    log.add("billing", "tariff", "Регистр, пробелы, русское написание", "Приведён к Basic/Comfort/Premium",
            "Варианты однозначно соответствуют тарифу; цена monthly_fee_rub это подтверждает",
            (canonical != df.tariff).sum())
    df["tariff"] = canonical

    comma = df.paid_rub.str.contains(",", regex=False)
    log.add("billing", "paid_rub", "Десятичная запятая", "Заменена на точку",
            "Значение не меняется, меняется только запись числа", comma.sum())
    for c in ["monthly_fee_rub", "charged_rub", "paid_rub", "opening_debt_rub", "closing_debt_rub", "traffic_gb"]:
        df[c] = num(df[c])
    for c in ["voice_minutes", "active_days", "payment_delay_days", "tariff_changes_count"]:
        df[c] = num(df[c]).astype("Int64")

    restore_closing_debt(df, log)

    df["traffic_gb_missing"] = df.traffic_gb.isna()
    log.add("billing", "traffic_gb", "Пропуск", "Оставлен пропуск, добавлен флаг traffic_gb_missing",
            "По заказчику пропуск — неизвестный объём, а не ноль; заполнение статистиками — только на обучающей выборке",
            df.traffic_gb_missing.sum())

    negative = df.voice_minutes < 0
    df["voice_minutes_invalid"] = negative
    df.loc[negative, "voice_minutes"] = pd.NA
    log.add("billing", "voice_minutes", "Отрицательное значение", "Заменено пропуском, добавлен флаг voice_minutes_invalid",
            "По заказчику значение некорректно; ноль или модуль исказили бы данные", negative.sum())
    return df.sort_values(["customer_id", "billing_month"]).reset_index(drop=True)


def restore_closing_debt(df: pd.DataFrame, log: DecisionLog) -> None:
    """Missing closing debt follows from the debt identity; the next month's opening debt confirms it."""
    missing = df.closing_debt_rub.isna()
    # "+ 0.0" turns a rounded -0.0 into 0.0, otherwise it is written as "-0.00"
    restored = (df.opening_debt_rub + df.charged_rub - df.paid_rub).round(2) + 0.0
    if (restored[missing] < 0).any():
        raise ValueError("billing: restored closing debt is negative")

    nxt = (df.sort_values(["customer_id", "billing_month"])
             .groupby("customer_id").opening_debt_rub.shift(-1).reindex(df.index))
    confirmed = missing & nxt.notna() & ((nxt - restored).abs() <= 0.005)
    contradicted = missing & nxt.notna() & ~confirmed
    if contradicted.any():
        raise ValueError(f"billing: {contradicted.sum()} restored closing debts contradict next month's opening")

    df["closing_debt_restored"] = missing
    df.loc[missing, "closing_debt_rub"] = restored[missing]
    log.add("billing", "closing_debt_rub", "Пропуск конечного долга",
            "Восстановлен как opening + charged − paid, добавлен флаг closing_debt_restored",
            f"Тождество выполняется во всех строках с полными данными; "
            f"{confirmed.sum()} из {missing.sum()} значений дополнительно подтверждены opening_debt_rub следующего месяца, "
            f"остальные — последний месяц абонента", missing.sum())


# -------------------------------------------------------------------- support

SUPPORT_COLUMNS = ["ticket_id", "customer_id", "source_system", "created_at", "available_at", "topic", "channel",
                   "resolved_at", "resolution_available_at", "satisfaction_score"]


def align_legacy(raw: pd.DataFrame, schema: pd.DataFrame, log: DecisionLog) -> pd.DataFrame:
    df = drop_full_duplicates(raw, ["ticket_no"], "support_legacy", log).rename(columns=load.legacy_renames(schema))
    for field in ["topic", "channel"]:
        mapping = load.value_map(schema, field)
        unknown = set(df[field]) - set(mapping) - {""}
        if unknown:
            raise ValueError(f"support_legacy: unmapped {field} values {unknown}")
        df[field] = df[field].map(mapping).fillna("")
    for c in ["created_at", "available_at", "resolved_at", "resolution_available_at"]:
        df[c] = timeparse.parse_local(df[c], LEGACY_TS_FMT)
    log.add("support_legacy", "*", "Русские названия полей, тем, каналов; местное время",
            "Поля переименованы и значения перекодированы по schema_support.csv; время — Москва",
            "Единая схема для обеих систем", len(df))
    return df.assign(source_system="legacy")


def align_current(raw: pd.DataFrame, log: DecisionLog) -> pd.DataFrame:
    df = drop_full_duplicates(raw, ["ticket_id"], "support_current", log).copy()
    no_tz = ~df.created_at.str.endswith("Z")
    for c in ["created_at", "available_at", "resolved_at", "resolution_available_at"]:
        df[c] = timeparse.parse_current(df[c])
    log.add("support_current", "created_at", "Время без часового пояса", "Принято московским",
            "Подтверждено заказчиком", no_tz.sum())
    log.add("support_current", "*_at", "Время в UTC (суффикс Z)", "Переведено в Europe/Moscow с сохранением момента",
            "Единый часовой пояс со старой системой и биллингом", len(df))
    return df.assign(source_system="current")


def clean_support(legacy_raw: pd.DataFrame, current_raw: pd.DataFrame, schema: pd.DataFrame,
                  subscriber_ids: set, log: DecisionLog) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (support_clean, quarantine)."""
    df = pd.concat([align_legacy(legacy_raw, schema, log), align_current(current_raw, log)], ignore_index=True)
    if df.ticket_id.duplicated().any():
        raise ValueError("support: the same ticket_id appears in both systems")

    stripped = df.customer_id.str.strip()
    log.add("support_current", "customer_id", "Пробелы вокруг идентификатора", "Удалены",
            "По схеме пробелы незначимы", (stripped != df.customer_id).sum())
    df["customer_id"] = stripped

    no_topic = df.topic == ""
    df.loc[no_topic, "topic"] = "unknown"
    log.add("support_current", "topic", "Пропуск темы", "Отдельная категория unknown",
            "Схема допускает unknown; такие обращения входят в support_count и support_unknown_topic_count",
            no_topic.sum())

    # Quarantine: no customer link, or no safe availability moment.
    reason = pd.Series("", index=df.index)
    reason[df.customer_id == ""] = "customer_id пуст: нельзя связать с абонентом"
    reason[(df.customer_id != "") & ~df.customer_id.isin(subscriber_ids)] = "customer_id нет в реестре абонентов"
    reason[(reason == "") & (df.available_at < df.created_at)] = \
        "available_at раньше created_at: безопасный момент доступности не установлен"
    quarantined = reason != ""
    for text, n in reason[quarantined].value_counts().sort_index().items():
        log.add("support", "*", text, "Вынесено в карантин", "Запись нельзя корректно включить в месячный снимок", n)
    quarantine = build_quarantine(df[quarantined], reason[quarantined], subscriber_ids)
    df = df[~quarantined].copy()

    # A wrong closure must not erase the ticket itself: drop only the closure fields.
    bad_closure = df.resolved_at < df.created_at
    df["resolution_invalid"] = bad_closure
    df.loc[bad_closure, ["resolved_at", "resolution_available_at"]] = pd.NaT
    log.add("support_current", "resolved_at", "Закрытие раньше создания",
            "Обращение сохранено; resolved_at, resolution_available_at и оценка заменены пропуском, флаг resolution_invalid",
            "Факт создания корректен и учитывается; факт закрытия недостоверен", bad_closure.sum())

    score = num(df.satisfaction_score)
    bad_score = score.notna() & ~score.isin([1, 2, 3, 4, 5])
    df["satisfaction_score"] = score.where(~bad_score & ~bad_closure).astype("Int64")
    df["score_invalid"] = bad_score
    log.add("support_current", "satisfaction_score", "Оценка вне 1–5", "Заменена пропуском, флаг score_invalid",
            "Шкала 1–5; исходное значение не восстанавливается", bad_score.sum())

    for later, earlier in [("resolution_available_at", "resolved_at"), ("resolution_available_at", "available_at")]:
        if (df[later] < df[earlier]).any():
            raise ValueError(f"support: {later} earlier than {earlier} after cleaning")

    cols = SUPPORT_COLUMNS + ["resolution_invalid", "score_invalid"]
    return df[cols].sort_values("ticket_id").reset_index(drop=True), quarantine


def build_quarantine(rows: pd.DataFrame, reason: pd.Series, subscriber_ids: set) -> pd.DataFrame:
    q = rows[SUPPORT_COLUMNS].copy()
    q.insert(0, "reason", reason)
    q["linked_to_customer"] = rows.customer_id.isin(subscriber_ids)
    created_month = rows.created_at.dt.tz_localize(None).dt.to_period("M").dt.start_time
    q["created_month"] = created_month.where(q.linked_to_customer)
    return q.sort_values("ticket_id").reset_index(drop=True)
