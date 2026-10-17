"""Single entry point for the lesson 2 data preparation.

Run from the repository root:
    python lesson2/prepare.py
"""
import pandas as pd

from prep import audit, clean, config, inventory, load
from prep.export import write_csv

DATE_COLS = {
    "subscribers_clean": ("activation_date",),
    "contract_events_clean": ("event_date",),
    "billing_clean": ("billing_month",),
    "support_clean": (),
    "quarantine": ("created_month",),
}


def show(title: str, df: pd.DataFrame) -> None:
    with pd.option_context("display.width", 250, "display.max_columns", None,
                           "display.max_colwidth", 90, "display.max_rows", None):
        print(title)
        print(df.astype(object).where(df.notna(), "").to_string(index=False), end="\n\n")


def main() -> None:
    config.check_inputs()
    out = config.OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    sources = load.load_sources()

    # Step 1: inventory
    summary, columns = inventory.build(sources)
    write_csv(summary, out / "inventory_sources.csv")
    write_csv(columns, out / "inventory_columns.csv")

    # Step 2: audit of the raw sources
    audit_before = audit.run_raw(sources)
    write_csv(audit_before, out / "audit_before.csv")

    # Step 3: cleaning
    log = clean.DecisionLog()
    events = clean.clean_events(sources["contract_events"], log)
    subscribers = clean.clean_subscribers(sources["subscribers"], sources["contract_events"], log)
    billing = clean.clean_billing(sources["billing"], log)
    support, quarantine = clean.clean_support(sources["support_legacy"], sources["support_current"],
                                              load.read_support_schema(), set(subscribers.customer_id), log)
    tables = {"subscribers_clean": subscribers, "contract_events_clean": events,
              "billing_clean": billing, "support_clean": support, "quarantine": quarantine}
    for name, df in tables.items():
        write_csv(df, out / f"{name}.csv", DATE_COLS[name])
    write_csv(log.frame(), out / "decisions.csv")

    # Step 2 repeated: the same checks on the written files
    written = {name: load.read_raw_csv(out / f"{name}.csv") for name in tables if name != "quarantine"}
    audit_after = audit.run_clean(written)
    write_csv(audit_after, out / "audit_after.csv")

    show("Источники:", summary.drop(columns="read_method"))
    show("Решения (decisions.csv):", log.frame().drop(columns="rationale"))
    show("Проблемы после очистки (ненулевые; полный список — audit_after.csv):",
         audit_after[(audit_after.rows > 0) | (audit_after.copies > 0)])
    show("Строки подготовленных таблиц:", pd.DataFrame({"table": list(tables), "rows": [len(t) for t in tables.values()]}))


if __name__ == "__main__":
    main()
