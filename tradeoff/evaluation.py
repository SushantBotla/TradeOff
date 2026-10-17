"""Privileged, separate evaluation worker. Never imported by the coordinator."""

import json
import time
from pathlib import Path

from .common import TradeOffError, database, identifier, integer, load_json, object_fields, write_json
from .scenarios import FACTORIES, SCENARIOS


def local_options(profile):
    d, stock = profile["demand"], profile["stock"]
    result = []
    for x in range(d + 1):
        best = None
        for u in range(min(stock, d - x) + 1):
            z = d - x - u
            cost = (u * profile["stock_unit_cost"] + min(z, profile["mild_threshold"]) * profile["mild_unit_cost"]
                    + max(0, z - profile["mild_threshold"]) * profile["severe_unit_cost"])
            item = (cost, u, z)
            if best is None or item < best:
                best = item
        result.append(best)
    return result


def solve_oracle(profiles, supply, require_service=True):
    started = time.perf_counter()
    options = [local_options(profiles[n]) for n in FACTORIES]
    best = None
    for a, la in enumerate(options[0]):
        if require_service and la[2] > profiles["factory_a"]["mild_threshold"]:
            continue
        for b, lb in enumerate(options[1]):
            if require_service and lb[2] > profiles["factory_b"]["mild_threshold"]:
                continue
            y = max(0, a + b - supply["primary_capacity"])
            if y > supply["alternate_capacity"]:
                continue
            item = (supply["alternate_unit_cost"] * y + la[0] + lb[0], a, b, y)
            if best is None or item < best:
                best = item
    if best is None:
        return dict(status="infeasible_service_requirements", solve_ms=round((time.perf_counter() - started) * 1000, 3))
    return dict(status="optimal", true_cost=best[0], allocations=dict(zip(FACTORIES, best[1:3])),
                alternate_qty=best[3], solve_ms=round((time.perf_counter() - started) * 1000, 3), backend="independent_exhaustive_integer")


def true_cost(proposal, profiles, supply):
    integer(proposal["alternate_qty"], "alternate_qty", high=supply["alternate_capacity"])
    if sum(proposal["allocations"].values()) > supply["primary_capacity"] + proposal["alternate_qty"]:
        raise TradeOffError("Evaluator rejected supply infeasibility")
    total = supply["alternate_unit_cost"] * proposal["alternate_qty"]
    for name in FACTORIES:
        integer(proposal["allocations"][name], "allocation", high=profiles[name]["demand"])
        total += local_options(profiles[name])[proposal["allocations"][name]][0]
    return total


class Evaluator:
    def __init__(self, config):
        self.config = config
        self.cache = {}

    def profiles(self, scenario):
        result = {}
        for name, path in self.config["private_databases"].items():
            with database(path, readonly=True) as db:
                row = db.execute("SELECT payload FROM profiles WHERE scenario_id=?", (scenario,)).fetchone()
            result[name] = json.loads(row[0])
        return result

    def evaluate(self, exchange):
        object_fields(exchange, ("run_id", "scenario_id", "status", "rounds"))
        identifier(exchange["run_id"])
        if exchange["scenario_id"] not in SCENARIOS or not isinstance(exchange["rounds"], list) or len(exchange["rounds"]) > 2:
            raise TradeOffError("Invalid evaluation job")
        scenario = exchange["scenario_id"]
        profiles = self.profiles(scenario)
        supply = profiles.pop("supplier_s")
        if scenario not in self.cache:
            self.cache[scenario] = solve_oracle(profiles, supply)
        oracle = self.cache[scenario]
        rows = []
        for proposal in exchange["rounds"]:
            if proposal.get("status") != "optimal":
                continue
            cost = true_cost(proposal, profiles, supply)
            rows.append(dict(proposal_id=proposal["proposal_id"], true_cost=cost))
        accepted = exchange["status"] == "completed" and bool(rows)
        gap = None
        if accepted and oracle["status"] == "optimal" and oracle["true_cost"] > 0:
            gap = round(100 * (rows[-1]["true_cost"] - oracle["true_cost"]) / oracle["true_cost"], 6)
            if gap < -0.0001:
                raise TradeOffError("Candidate cost below oracle: check comparable constraints")
        return dict(run_id=exchange["run_id"], scenario_id=scenario, fixture_version="synthetic-v1",
                    policy_version="no-severe-shortage-v1", oracle=oracle, rounds=rows,
                    final_true_cost=rows[-1]["true_cost"] if accepted else None, optimality_gap_percent=gap,
                    absolute_regret=rows[-1]["true_cost"] - oracle["true_cost"] if accepted and oracle["status"] == "optimal" else None,
                    accepted_candidate=accepted, label="Privileged synthetic benchmark; not provided to the LLM",
                    disclosure_note="Oracle allocation and aggregated true costs are extra disclosures to this demo viewer.",
                    evaluated_at=time.time())

    def process_once(self):
        for path in Path(self.config["exchange_dir"]).glob("*.json"):
            try:
                identifier(path.stem)
                job = load_json(path)
                if job.get("run_id") != path.stem:
                    continue
                report_path = Path(self.config["reports_dir"]) / path.name
                if report_path.exists() and report_path.stat().st_mtime_ns >= path.stat().st_mtime_ns:
                    continue
                report = self.evaluate(job)
                write_json(report_path, report, mode=0o640)
            except (TradeOffError, ValueError, KeyError, OSError, TypeError):
                # A malformed exchange never becomes a fabricated benchmark.
                continue

    def watch(self):
        while True:
            self.process_once()
            time.sleep(0.4)
