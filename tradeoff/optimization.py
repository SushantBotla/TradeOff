"""Restricted-information optimization. This module never imports private fixtures."""

import os
import shutil
import time

from .common import TradeOffError, integer, object_fields
from .scenarios import FACTORIES


def validate_inputs(offer, bids, floors):
    object_fields(offer, ("primary_capacity", "alternate_capacity", "alternate_unit_cost"))
    for key, value in offer.items():
        integer(value, key, high=10000)
    if set(bids) != set(FACTORIES) or set(floors) - set(FACTORIES):
        raise TradeOffError("Exactly two known factory bids are required")
    for name, bid in bids.items():
        object_fields(bid, ("requested_qty", "priority_signal", "deadline"))
        integer(bid["requested_qty"], "requested_qty", high=2000)
        integer(bid["priority_signal"], "priority_signal", high=10000)
        if bid["deadline"] != "day_5":
            raise TradeOffError("This prototype supports only the day_5 deadline")
        integer(floors.get(name, 0), "minimum_external_qty", high=2000)


def solve_restricted(offer, bids, floors=None, backend=None):
    started = time.perf_counter()
    floors = floors or {}
    validate_inputs(offer, bids, floors)
    backend = backend or os.getenv("TRADEOFF_SOLVER", "auto")
    if backend not in ("auto", "exact", "cbc"):
        raise TradeOffError("Unknown solver backend")
    if backend in ("auto", "cbc") and shutil.which("cbc"):
        try:
            import pulp
        except ImportError:
            if backend == "cbc":
                raise TradeOffError("CBC backend requires PuLP 3.3.1", 503) from None
        else:
            if not str(pulp.__version__).startswith("3."):
                raise TradeOffError("CBC adapter requires the pinned PuLP 3.x API", 503)
            result = _cbc(pulp, offer, bids, floors)
            result["solve_ms"] = round((time.perf_counter() - started) * 1000, 3)
            return result
    if backend == "cbc":
        raise TradeOffError("OS CBC executable is not installed", 503)
    qa, qb = [bids[name]["requested_qty"] for name in FACTORIES]
    pa, pb = [bids[name]["priority_signal"] for name in FACTORIES]
    fa, fb = [floors.get(name, 0) for name in FACTORIES]
    c1, c2, cy = [offer[k] for k in ("primary_capacity", "alternate_capacity", "alternate_unit_cost")]
    best = None
    # For each A quantity, the B objective is linear on each side of the
    # primary-capacity kink. Its minimum is at an endpoint or that kink.
    for a in range(fa, qa + 1):
        upper_b = min(qb, c1 + c2 - a)
        if upper_b < fb:
            continue
        kink = min(upper_b, max(fb, c1 - a))
        for b in {fb, upper_b, kink}:
            y = max(0, a + b - c1)
            key = (cy * y + pa * (qa - a) + pb * (qb - b), a, b, y)
            if best is None or key < best:
                best = key
    result = dict(status="infeasible", backend="exact_integer", solve_ms=round((time.perf_counter() - started) * 1000, 3))
    if best:
        result.update(status="optimal", allocations=dict(zip(FACTORIES, best[1:3])), alternate_qty=best[3], surrogate_cost=best[0])
    return result


def _cbc(pulp, offer, bids, floors):
    model = pulp.LpProblem("restricted_shortage", pulp.LpMinimize)
    x = {name: pulp.LpVariable(name, floors.get(name, 0), bids[name]["requested_qty"], cat="Integer") for name in FACTORIES}
    if any(floors.get(name, 0) > bids[name]["requested_qty"] for name in FACTORIES):
        return dict(status="infeasible", backend="cbc")
    y = pulp.LpVariable("alternate", 0, offer["alternate_capacity"], cat="Integer")
    model += sum(x.values()) <= offer["primary_capacity"] + y
    model += offer["alternate_unit_cost"] * y + sum(bids[n]["priority_signal"] * (bids[n]["requested_qty"] - x[n]) for n in FACTORIES)
    model.solve(pulp.COIN_CMD(path=shutil.which("cbc"), msg=False, timeLimit=2, threads=1))
    status = pulp.LpStatus[model.status].lower()
    if status != "optimal":
        return dict(status=status.replace(" ", "_"), backend="cbc")
    allocations = {n: int(round(x[n].value())) for n in FACTORIES}
    return dict(status="optimal", backend="cbc", allocations=allocations,
                alternate_qty=int(round(y.value())), surrogate_cost=int(round(pulp.value(model.objective))))


def check_proposal(proposal, offer, bids, floors=None):
    if proposal.get("status") != "optimal":
        raise TradeOffError("Only optimal proposals can be validated")
    if set(proposal.get("allocations", {})) != set(FACTORIES):
        raise TradeOffError("Invalid allocation participant set")
    y = integer(proposal.get("alternate_qty"), "alternate_qty", high=offer["alternate_capacity"])
    for name in FACTORIES:
        integer(proposal["allocations"][name], "allocation", low=(floors or {}).get(name, 0), high=bids[name]["requested_qty"])
    if sum(proposal["allocations"].values()) > offer["primary_capacity"] + y:
        raise TradeOffError("Allocation exceeds supply")

