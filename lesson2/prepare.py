"""Single entry point for the lesson 2 data preparation.

Run from the repository root:
    python lesson2/prepare.py
"""
import pandas as pd

from prep import audit, checks, clean, config, inventory, load, merge, summary
from prep.export import write_csv

DATE_COLS = {
    "subscribers_clean": ("activation_date",),
    "contract_events_clean": ("event_date",),
    "billing_clean": ("billing_month",),
    "support_clean": (),
    "quarantine": ("created_month",),
    "customer_month": ("billing_month", "activation_date"),
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
    inventory_summary, columns = inventory.build(sources)
    write_csv(inventory_summary, out / "inventory_sources.csv")
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

    # Step 4: monthly table
    customer_month = merge.build_customer_month(billing, subscribers, support, quarantine)
    write_csv(customer_month, out / "customer_month.csv", DATE_COLS["customer_month"])
    coverage = merge.ticket_coverage(support, billing[merge.KEY + ["available_at"]])

    # Step 5: availability and join checks
    tables["customer_month"] = customer_month
    check_results = checks.run(customer_month, billing, coverage, tables, load.read_raw_csv(config.DICTIONARY_V2))
    write_csv(check_results, out / "checks.csv")

    # Machine-readable summary of all counts
    summary.write(summary.build(sources, tables, audit_before, audit_after, log.frame(), coverage, check_results),
                  out / "summary.json")

    show("Источники:", inventory_summary.drop(columns="read_method"))
    show("Решения (decisions.csv):", log.frame().drop(columns="rationale"))
    show("Проблемы после очистки (ненулевые; полный список — audit_after.csv):",
         audit_after[(audit_after.rows > 0) | (audit_after.copies > 0)])
    show("Строки подготовленных таблиц:", pd.DataFrame({"table": list(tables), "rows": [len(t) for t in tables.values()]}))
    show("Проверки (checks.csv):", check_results)

    failed = check_results[~check_results.passed]
    if len(failed):
        raise SystemExit(f"Не пройдено проверок: {len(failed)} — см. checks.csv")


if __name__ == "__main__":
    main()
