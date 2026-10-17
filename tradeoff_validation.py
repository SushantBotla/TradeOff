"""Reproduce the numerical audit of the supplied TradeOff plan using stdlib only.

This is an exhaustive checker for the tiny, synthetic, integer-chip example,
not the proposed production solver. Batch constraints are deliberately excluded,
matching the equations actually written in the supplied specification.
"""

import json
from pathlib import Path


FACTORIES = {
    "A": dict(demand=600, stock=40, stock_cost=45, threshold=100, mild=90, severe=220),
    "B": dict(demand=500, stock=50, stock_cost=30, threshold=150, mild=40, severe=110),
}
ALT_COST = 95


def local_cost(allocation, factory):
    f = FACTORIES[factory]
    # Both stock costs are below their respective mild shortage costs.
    stock_used = min(f["stock"], f["demand"] - allocation)
    shortage = f["demand"] - allocation - stock_used
    cost = (
        stock_used * f["stock_cost"]
        + min(shortage, f["threshold"]) * f["mild"]
        + max(0, shortage - f["threshold"]) * f["severe"]
    )
    return dict(cost=cost, stock_used=stock_used, shortage=shortage)


def evaluate(a, b, y):
    la, lb = local_cost(a, "A"), local_cost(b, "B")
    return dict(
        xA=a, xB=b, y=y,
        true_cost=ALT_COST * y + la["cost"] + lb["cost"],
        stock_A=la["stock_used"], stock_B=lb["stock_used"],
        shortage_A=la["shortage"], shortage_B=lb["shortage"],
    )


def solve(capacity=800, alt_capacity=300, bids=None, floors=(0, 0)):
    # bids=None: minimize true cost, with unrestricted external demand limits.
    # Otherwise minimize the coordinator's coarse linear surrogate.
    qa, qb = (600, 500) if bids is None else (560, 450)
    best_key, best = None, None
    a_costs = [local_cost(a, "A")["cost"] for a in range(qa + 1)]
    b_costs = [local_cost(b, "B")["cost"] for b in range(qb + 1)]
    for a in range(floors[0], qa + 1):
        for b in range(floors[1], qb + 1):
            y = max(0, a + b - capacity)
            if y > alt_capacity:
                continue
            objective = ALT_COST * y
            if bids is None:
                objective += a_costs[a] + b_costs[b]
            else:
                objective += bids[0] * (qa - a) + bids[1] * (qb - b)
            key = (objective, a, b, y)
            if best_key is None or key < best_key:
                best_key = key
                best = evaluate(a, b, y)
                best["optimized_objective"] = objective
    return best


def main():
    oracle = solve()
    cases = {
        "scope": "Synthetic integer-chip example; no batches; no payments; primary cost treated as sunk.",
        "oracle_baseline": oracle,
        "oracle_baseline_with_service_floors": solve(floors=(460, 300)),
        "original_claim_y60": evaluate(560, 300, 60),
        "coarse_round1": solve(bids=(165, 75)),
        "original_round2_raise_entire_B_bid": solve(bids=(165, 110), floors=(0, 350)),
        "corrected_round2_keep_bid_add_floor": solve(bids=(165, 75), floors=(0, 300)),
        "oracle_primary_disruption": solve(capacity=480),
        "oracle_primary_disruption_with_service_floors": solve(capacity=480, floors=(460, 300)),
        "corrected_primary_disruption": solve(capacity=480, bids=(165, 75), floors=(0, 300)),
        "oracle_alt_only_disruption": solve(alt_capacity=150),
        "combined_disruption_round1": solve(capacity=480, alt_capacity=150, bids=(165, 75)),
        "combined_disruption_round2": solve(capacity=480, alt_capacity=150, bids=(165, 75), floors=(0, 300)),
        "combined_disruption_both_floors": solve(capacity=480, alt_capacity=150, bids=(165, 75), floors=(460, 300)),
    }
    for name in ("coarse_round1", "original_round2_raise_entire_B_bid", "corrected_round2_keep_bid_add_floor"):
        cases[name]["gap_percent"] = round(100 * (cases[name]["true_cost"] - oracle["true_cost"]) / oracle["true_cost"], 6)
    assert oracle["true_cost"] == 14700
    assert oracle["y"] == 0
    assert cases["original_round2_raise_entire_B_bid"]["true_cost"] == 23250
    assert cases["corrected_round2_keep_bid_add_floor"]["true_cost"] == 15000
    assert cases["oracle_primary_disruption"]["true_cost"] == 44900
    assert cases["oracle_baseline_with_service_floors"]["true_cost"] == 14700
    assert cases["oracle_primary_disruption_with_service_floors"]["true_cost"] == 44900
    assert cases["corrected_primary_disruption"]["true_cost"] == 45000
    assert cases["combined_disruption_both_floors"] is None
    output = Path(__file__).with_name("tradeoff_validation_results.json")
    output.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
