"""Streaming, local-only DataCo aggregation; never exports customer rows to AI."""

import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path

from .common import TradeOffError

SOURCE = "https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis"
ALLOWED = ("Category Name", "Order Item Quantity", "Days for shipping (real)",
           "Days for shipment (scheduled)", "Delivery Status", "Late_delivery_risk", "Shipping Mode", "Order Status")
REQUIRED = ("Category Name", "Order Item Quantity", "Days for shipping (real)", "Days for shipment (scheduled)")


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def summarize(csv_path):
    path = Path(csv_path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    # DataCo releases commonly use Latin-1. Prefer UTF-8 when the complete file
    # validates; latin-1 fallback is explicit, not lossy replacement.
    encoding = "utf-8-sig"
    try:
        with path.open(encoding=encoding) as stream:
            for _ in stream:
                pass
    except UnicodeDecodeError:
        encoding = "latin-1"
    groups = defaultdict(lambda: dict(line_items=0, observed_units=0, shipping_observations=0,
                                    actual_days_sum=0.0, scheduled_days_sum=0.0, delayed_line_items=0))
    count, excluded, invalid = 0, 0, 0
    with path.open(encoding=encoding, newline="") as stream:
        reader = csv.DictReader(stream)
        fields = [field.strip() for field in (reader.fieldnames or [])]
        if len(fields) != len(set(fields)) or any(k not in fields for k in REQUIRED):
            raise TradeOffError("DataCo CSV lacks required columns or has duplicate headers")
        reader.fieldnames = fields
        for row in reader:
            count += 1
            # Read only the allowlisted fields. Customer names, emails, addresses,
            # passwords, individual IDs and free-form product text are ignored.
            if row.get("Order Status", "").strip().upper() in ("CANCELED", "SUSPECTED_FRAUD"):
                excluded += 1
                continue
            category = row.get("Category Name", "").strip()
            qty = number(row.get("Order Item Quantity"))
            if not category or len(category) > 100 or qty is None or qty <= 0 or not qty.is_integer():
                invalid += 1
                continue
            group = groups[category]
            group["line_items"] += 1
            group["observed_units"] += int(qty)
            actual, scheduled = number(row.get("Days for shipping (real)")), number(row.get("Days for shipment (scheduled)"))
            if actual is not None and scheduled is not None and actual >= 0 and scheduled >= 0:
                group["shipping_observations"] += 1
                group["actual_days_sum"] += actual
                group["scheduled_days_sum"] += scheduled
                group["delayed_line_items"] += int(actual > scheduled)
    output = []
    for category, group in sorted(groups.items(), key=lambda pair: (-pair[1]["observed_units"], pair[0])):
        n = group.pop("shipping_observations")
        actual_sum, scheduled_sum = group.pop("actual_days_sum"), group.pop("scheduled_days_sum")
        delayed = group.pop("delayed_line_items")
        output.append(dict(category=category, **group, shipping_observations=n,
                           actual_shipping_days_mean=round(actual_sum / n, 4) if n else None,
                           scheduled_shipping_days_mean=round(scheduled_sum / n, 4) if n else None,
                           delayed_line_item_fraction=round(delayed / n, 6) if n else None))
    if not output:
        raise TradeOffError("No valid DataCo line items were found")
    return dict(source=SOURCE, source_filename=path.name, source_sha256=digest.hexdigest(), encoding=encoding,
                rows_read=count, excluded_canceled_or_suspected_fraud=excluded, invalid_rows=invalid,
                fields_used=list(ALLOWED), categories=output,
                limitations=["Rows are order line items, not necessarily unique orders.",
                             "Historical shipping outcomes are descriptive; they are not pre-order predictions.",
                             "Different product categories do not establish competition for an interchangeable component.",
                             "No observed safety stock, shortage loss curve, common-component capacity or emergency procurement cost is inferred.",
                             "Core optimization presets remain explicitly synthetic; this summary is context, not validated shortage ground truth."],
                privacy=dict(raw_customer_rows_exported=False, sent_to_llm=False))

