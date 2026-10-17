"""Step 4: customer_month — one row per customer_id and billing_month.

Snapshot moment of a row = billing available_at (00:00 of the next month, Moscow).
A ticket counts for a row when
  * it was created in billing_month (Moscow calendar), and
  * its creation record was available no later than the snapshot.
Closure and score are used only when resolution_available_at is no later than the snapshot.
Support is aggregated to the row key first and then left-joined to billing,
so billing rows can never be multiplied.
"""
import pandas as pd

from prep.config import TZ

KEY = ["customer_id", "billing_month"]
SUBSCRIBER_COLUMNS = ["region", "acquisition_channel", "customer_segment", "activation_date", "activation_date_restored"]
COUNT_COLUMNS = ["support_count", "support_network_count", "support_billing_count", "support_unknown_topic_count",
                 "support_flagged_count", "support_resolved_count", "support_score_count",
                 "support_quarantined_linked_count"]


def month_start(ts: pd.Series) -> pd.Series:
    """Calendar month of a Moscow timestamp, as a Moscow midnight of the 1st."""
    return ts.dt.tz_localize(None).dt.to_period("M").dt.start_time.dt.tz_localize(TZ)


def available_tickets(support: pd.DataFrame, snapshots: pd.DataFrame) -> pd.DataFrame:
    """Tickets matched to their billing row and known at that row's snapshot.

    snapshots: customer_id, billing_month, available_at (the billing row's availability).
    """
    t = support.assign(billing_month=month_start(support.created_at))
    t = t.merge(snapshots.rename(columns={"available_at": "snapshot_at"}), on=KEY, how="inner", validate="m:1")
    known = t[t.available_at <= t.snapshot_at].copy()
    closure_known = known.resolution_available_at <= known.snapshot_at
    known["resolved_known"] = closure_known & known.resolved_at.notna()
    known["score_known"] = known.satisfaction_score.where(closure_known)
    return known


def aggregate_support(support: pd.DataFrame, snapshots: pd.DataFrame) -> pd.DataFrame:
    t = available_tickets(support, snapshots)
    t = t.assign(is_network=t.topic == "network", is_billing=t.topic == "billing", is_unknown=t.topic == "unknown",
                 is_flagged=t.resolution_invalid | t.score_invalid)
    g = t.groupby(KEY)
    agg = pd.DataFrame({
        "support_count": g.size(),
        "support_network_count": g.is_network.sum(),
        "support_billing_count": g.is_billing.sum(),
        "support_unknown_topic_count": g.is_unknown.sum(),
        "support_flagged_count": g.is_flagged.sum(),
        "support_resolved_count": g.resolved_known.sum(),
        "support_score_count": g.score_known.count(),
        "support_score_mean": g.score_known.mean().round(2),
    })
    return agg.reset_index()


def ticket_coverage(support: pd.DataFrame, snapshots: pd.DataFrame) -> dict[str, int]:
    """Where every clean ticket ended up relative to the monthly snapshots."""
    t = support.assign(billing_month=month_start(support.created_at))
    t = t.merge(snapshots.rename(columns={"available_at": "snapshot_at"}), on=KEY, how="left", validate="m:1")
    no_row = t.snapshot_at.isna()
    late = ~no_row & (t.available_at > t.snapshot_at)
    return {"tickets_clean": len(t), "tickets_in_snapshot": int((~no_row & ~late).sum()),
            "tickets_after_snapshot": int(late.sum()), "tickets_without_billing_row": int(no_row.sum())}


def quarantined_linked(quarantine: pd.DataFrame) -> pd.DataFrame:
    """Quarantined tickets that still point at a known customer and month (service column, not a feature)."""
    q = quarantine[quarantine.linked_to_customer]
    q = q.assign(billing_month=month_start(q.created_at))
    return q.groupby(KEY).size().rename("support_quarantined_linked_count").reset_index()


def build_customer_month(billing: pd.DataFrame, subscribers: pd.DataFrame,
                         support: pd.DataFrame, quarantine: pd.DataFrame) -> pd.DataFrame:
    snapshots = billing[KEY + ["available_at"]]
    out = (billing
           .merge(subscribers[["customer_id"] + SUBSCRIBER_COLUMNS], on="customer_id", how="left", validate="m:1")
           .merge(aggregate_support(support, snapshots), on=KEY, how="left", validate="1:1")
           .merge(quarantined_linked(quarantine), on=KEY, how="left", validate="1:1"))

    # No ticket in a correct, available source means zero tickets — not "unknown".
    # support_score_mean stays missing when there is no available score.
    out[COUNT_COLUMNS] = out[COUNT_COLUMNS].fillna(0).astype("int64")

    if len(out) != len(billing):
        raise ValueError(f"customer_month has {len(out)} rows, billing has {len(billing)}")
    return out
