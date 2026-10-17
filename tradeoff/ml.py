"""Real, local logistic regression trained on historical DataCo shipping outcomes.

Training and inference use stdlib only to remain deployable on s390x. The
model predicts retail line-item delay risk, not chip inventory/shortage costs.
No outcome column is an input feature; the holdout is chronological.
"""

import csv
import hashlib
import math
import random
from datetime import datetime
from pathlib import Path

from .common import TradeOffError, load_json, write_json
from .dataco import SOURCE

MODES = ("Standard Class", "Second Class", "First Class", "Same Day")
MARKETS = ("Africa", "Europe", "LATAM", "Pacific Asia", "USCA")
FEATURES = ["intercept", "scheduled_days_div_5"] + ["mode=" + x for x in MODES] + ["market=" + x for x in MARKETS]


def vector(mode, scheduled_days, market):
    if mode not in MODES or market not in MARKETS or type(scheduled_days) not in (int, float) or not math.isfinite(scheduled_days) or not 0 <= scheduled_days <= 10:
        raise TradeOffError("Risk inputs require a known shipping mode/market and scheduled days from 0 to 10")
    return [1.0, scheduled_days / 5] + [float(mode == x) for x in MODES] + [float(market == x) for x in MARKETS]


def sigmoid(value):
    value = max(-35, min(35, value))
    return 1 / (1 + math.exp(-value))


def score(weights, features):
    return sigmoid(sum(w * x for w, x in zip(weights, features)))


def auc(labels, probabilities):
    pairs = sorted(zip(probabilities, labels))
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    positive_rank, index = 0.0, 0
    while index < len(pairs):
        end = index + 1
        while end < len(pairs) and pairs[end][0] == pairs[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2
        positive_rank += average_rank * sum(label for _, label in pairs[index:end])
        index = end
    return (positive_rank - positives * (positives + 1) / 2) / (positives * negatives)


def train(csv_path, output, epochs=6, max_training=60000):
    source = Path(csv_path)
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    rows, skipped = [], 0
    # The supplied DataCo release uses Latin-1; all selected feature values and
    # date fields are ASCII. No raw customer columns are retained.
    required = {"Shipping Mode", "Market", "Days for shipment (scheduled)", "Days for shipping (real)", "order date (DateOrders)", "Order Status"}
    with source.open(encoding="latin-1", newline="") as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            raise TradeOffError("CSV does not contain required DataCo training columns")
        for row in reader:
            if row["Order Status"].upper() in ("CANCELED", "SUSPECTED_FRAUD"):
                skipped += 1
                continue
            try:
                scheduled, actual = float(row["Days for shipment (scheduled)"]), float(row["Days for shipping (real)"])
                if not math.isfinite(actual) or not 0 <= actual <= 60:
                    raise ValueError("invalid actual outcome")
                timestamp = datetime.strptime(row["order date (DateOrders)"], "%m/%d/%Y %H:%M")
                features = vector(row["Shipping Mode"], scheduled, row["Market"])
                rows.append((timestamp, features, int(actual > scheduled)))
            except (ValueError, TradeOffError):
                skipped += 1
    if len(rows) < 100:
        raise TradeOffError("At least 100 usable historical line items are required")
    rows.sort(key=lambda row: row[0])
    # Split on a timestamp boundary so line items sharing the order timestamp
    # cannot be divided between training and test partitions.
    cutoff = rows[int(len(rows) * .8)][0]
    training = [row for row in rows if row[0] < cutoff]
    holdout = [row for row in rows if row[0] >= cutoff]
    if not training or not holdout or len({r[2] for r in training}) != 2:
        raise TradeOffError("Chronological split needs training/test data and both training classes")
    rng = random.Random(74129)
    fitted_rows = rng.sample(training, min(max_training, len(training)))
    weights = [0.0] * len(FEATURES)
    step = 0
    for _ in range(epochs):
        rng.shuffle(fitted_rows)
        for _, features, label in fitted_rows:
            step += 1
            rate = .06 / math.sqrt(1 + step / 20000)
            error = score(weights, features) - label
            for j, feature in enumerate(features):
                weights[j] -= rate * (error * feature + (0.0001 * weights[j] if j else 0))
    labels = [r[2] for r in holdout]
    probabilities = [score(weights, r[1]) for r in holdout]
    accuracy = sum((p >= .5) == y for p, y in zip(probabilities, labels)) / len(labels)
    positive_fraction = sum(labels) / len(labels)
    log_loss = -sum(y * math.log(max(p, 1e-12)) + (1-y) * math.log(max(1-p, 1e-12)) for p, y in zip(probabilities, labels)) / len(labels)
    model = dict(kind="logistic_regression", version="dataco-delay-v1", framework="Python standard library", source=SOURCE,
                 source_sha256=digest.hexdigest(), features=FEATURES, weights=weights,
                 target="actual_shipping_days > scheduled_shipping_days", epochs=epochs, seed=74129,
                 train_rows_available=len(training), train_rows_fitted=len(fitted_rows), holdout_rows=len(holdout), skipped_rows=skipped,
                 chronological_cutoff=cutoff.isoformat(),
                 metrics=dict(holdout_accuracy=round(accuracy, 6), holdout_roc_auc=round(auc(labels, probabilities), 6) if auc(labels, probabilities) is not None else None,
                              holdout_brier=round(sum((p-y)**2 for p, y in zip(probabilities, labels)) / len(labels), 6),
                              holdout_log_loss=round(log_loss, 6), majority_baseline_accuracy=round(max(positive_fraction, 1-positive_fraction), 6)),
                 limitations=["Historical retail order-line outcomes, not prospective chip procurement validation.",
                              "No causal improvement or calibrated manufacturing risk is claimed.",
                              "Shipping mode, market and promised days are pre-delivery features; actual days are target only.",
                              "The optimizer and mandatory local validations remain authoritative."])
    write_json(output, model)
    return {k: v for k, v in model.items() if k != "weights"}


class RiskModel:
    def __init__(self, path):
        self.model = load_json(path)
        if self.model.get("kind") != "logistic_regression" or self.model.get("features") != FEATURES or len(self.model.get("weights", [])) != len(FEATURES):
            raise TradeOffError("Unsupported local model artifact")
        if not all(type(w) in (int, float) and math.isfinite(w) for w in self.model["weights"]):
            raise TradeOffError("Invalid local model weights")

    def predict(self, shipping_mode, scheduled_days, market):
        probability = score(self.model["weights"], vector(shipping_mode, scheduled_days, market))
        return dict(delay_probability=round(probability, 6), model=self.model["version"],
                    inputs=dict(shipping_mode=shipping_mode, scheduled_days=scheduled_days, market=market),
                    provenance="Local inference from learned historical DataCo coefficients; illustrative domain transfer")

