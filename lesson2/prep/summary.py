"""Machine-readable summary of the run: every count quoted in the quality report."""
import json
from pathlib import Path

import pandas as pd


def build(sources: dict, tables: dict, audit_before: pd.DataFrame, audit_after: pd.DataFrame,
          decisions: pd.DataFrame, coverage: dict, check_results: pd.DataFrame) -> dict:
    cm = tables["customer_month"]
    q = tables["quarantine"]
    totals = lambda a: {r.source: {"problem_rows": int(r.rows), "problem_cells": int(r.cells), "copies": int(r.copies)}
                        for r in a[a.field == "ИТОГО"].itertuples()}
    return {
        "source_rows": {name: len(df) for name, df in sources.items()},
        "prepared_rows": {name: len(df) for name, df in tables.items()},
        "audit_before": totals(audit_before),
        "audit_after": totals(audit_after),
        "decisions": [{"source": r.source, "field": r.field, "problem": r.problem, "affected": int(r.affected),
                       "unit": r.unit} for r in decisions.itertuples()],
        "quarantine": {
            "by_reason": q.reason.value_counts().sort_index().to_dict(),
            "linked_to_customer": int(q.linked_to_customer.sum()),
        },
        "support_coverage": coverage,
        "customer_month": {
            "rows": len(cm),
            "customers": int(cm.customer_id.nunique()),
            "rows_with_zero_support": int((cm.support_count == 0).sum()),
            "share_rows_with_zero_support": round(float((cm.support_count == 0).mean()), 4),
            "customers_without_available_tickets": int((cm.groupby("customer_id").support_count.sum() == 0).sum()),
            "rows_with_score_mean": int(cm.support_score_mean.notna().sum()),
            "subscribers_without_billing": int((~tables["subscribers_clean"].customer_id.isin(cm.customer_id)).sum()),
        },
        "checks": {"total": len(check_results), "passed": int(check_results.passed.sum())},
    }


def write(summary: dict, path: Path) -> None:
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
