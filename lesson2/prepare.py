"""Single entry point for the lesson 2 data preparation.

Run from the repository root:
    python lesson2/prepare.py
"""
import pandas as pd

from prep import audit, config, inventory, load


def write(df: pd.DataFrame, name: str) -> None:
    df.to_csv(config.OUTPUT / name, sep=";", index=False, encoding="utf-8-sig")


def main() -> None:
    config.check_inputs()
    config.OUTPUT.mkdir(parents=True, exist_ok=True)
    sources = load.load_sources()

    # Step 1: inventory
    summary, columns = inventory.build(sources)
    write(summary, "inventory_sources.csv")
    write(columns, "inventory_columns.csv")

    # Step 2: quality audit of the raw sources
    audit_before = audit.run(sources)
    write(audit_before, "audit_before.csv")

    with pd.option_context("display.width", 220, "display.max_columns", None,
                           "display.max_colwidth", 70, "display.max_rows", None):
        print(summary.drop(columns="read_method").to_string(index=False), end="\n\n")
        print("Проблемы до очистки (строки с нулём не показаны, полный список — audit_before.csv):")
        found = audit_before[(audit_before.rows > 0) | (audit_before.copies > 0)]
        print(found.astype(object).fillna("").to_string(index=False))


if __name__ == "__main__":
    main()
