"""Единый запуск подготовки данных второго занятия.

Запуск из корня репозитория:
    python lesson2/prepare.py
"""
import pandas as pd

from prep import config, inventory, load


def main() -> None:
    config.check_inputs()
    config.OUTPUT.mkdir(parents=True, exist_ok=True)

    sources = load.load_sources()
    summary, columns = inventory.build(sources)
    summary.to_csv(config.OUTPUT / "inventory_sources.csv", sep=";", index=False, encoding="utf-8-sig")
    columns.to_csv(config.OUTPUT / "inventory_columns.csv", sep=";", index=False, encoding="utf-8-sig")

    time_cols = columns.dropna(subset=["unparsed_nonempty"]).astype({"unparsed_nonempty": int})
    with pd.option_context("display.width", 200, "display.max_columns", None, "display.max_colwidth", 60):
        print(summary.drop(columns="read_method").to_string(index=False), end="\n\n")
        print(columns[["source", "column", "observed_types"]].to_string(index=False), end="\n\n")
        print(time_cols.drop(columns="observed_types").to_string(index=False))


if __name__ == "__main__":
    main()
