"""Independent participant services: own private database, restricted HTTP API."""

import json
import time

from .common import TradeOffError, database, identifier, integer, object_fields
from .http import Handler, serve
from .scenarios import SCENARIOS
from .security import sign, verify


class Participant:
    def __init__(self, config):
        self.config = config
        self.name = config["role"]

    def profile(self, scenario):
        if not isinstance(scenario, str) or scenario not in SCENARIOS:
            raise TradeOffError("Unknown scenario")
        with database(self.config["db_path"], readonly=True) as db:
            row = db.execute("SELECT payload FROM profiles WHERE scenario_id=?", (scenario,)).fetchone()
        if not row:
            raise TradeOffError("Participant scenario unavailable", 404)
        return json.loads(row[0])

    def handle(self, path, envelope):
        payload = verify(envelope, self.config["key"], "coordinator", self.name, path, db_path=self.config["db_path"])
        run_id = envelope["run_id"]
        object_fields(payload, ("scenario_id",), ("proposal",))
        scenario = payload["scenario_id"]
        profile = self.profile(scenario)
        with database(self.config["db_path"]) as db:
            binding = db.execute("SELECT * FROM run_bindings WHERE run_id=?", (run_id,)).fetchone()
            if binding and binding["scenario_id"] != scenario:
                raise TradeOffError("Run cannot switch scenario", 403)
            if path == "/bid":
                if "proposal" in payload:
                    raise TradeOffError("Bid request cannot contain a proposal")
                db.execute("INSERT OR IGNORE INTO run_bindings(run_id,scenario_id) VALUES (?,?)", (run_id, scenario))
                if self.name == "supplier_s":
                    response = {k: profile[k] for k in ("primary_capacity", "alternate_capacity", "alternate_unit_cost")}
                else:
                    response = dict(requested_qty=max(0, profile["demand"] - profile["stock"]),
                                    priority_signal=profile["priority_signal"], deadline=profile["deadline"])
            elif path == "/validate" and self.name != "supplier_s":
                if not binding or "proposal" not in payload:
                    raise TradeOffError("Bid registration and a proposal are required", 403)
                proposal = payload["proposal"]
                object_fields(proposal, ("proposal_id", "run_id", "round_id", "allocations", "alternate_qty"))
                round_id = integer(proposal["round_id"], "round_id", 1, 2)
                if proposal["run_id"] != run_id or proposal["proposal_id"] != f"{run_id}_r{round_id}":
                    raise TradeOffError("Proposal binding rejected", 403)
                if round_id < binding["latest_round"]:
                    raise TradeOffError("Stale proposal rejected", 403)
                allocations = proposal["allocations"]
                object_fields(allocations, ("factory_a", "factory_b"))
                for amount in allocations.values():
                    integer(amount, "allocation", high=2000)
                integer(proposal["alternate_qty"], "alternate_qty", high=10000)
                allocation = integer(allocations[self.name], "allocation", high=profile["demand"] - profile["stock"])
                minimum = max(0, profile["demand"] - profile["stock"] - profile["mild_threshold"])
                response = dict(proposal_id=proposal["proposal_id"], accept=allocation >= minimum)
                if not response["accept"]:
                    response["minimum_external_qty"] = minimum
                db.execute("UPDATE run_bindings SET latest_round=? WHERE run_id=?", (round_id, run_id))
            else:
                raise TradeOffError("Participant endpoint unavailable", 404)
        return sign(response, self.config["key"], self.name, "coordinator", path + ":response", run_id)

    def denied(self, reason):
        with database(self.config["db_path"]) as db:
            db.execute("INSERT INTO denied_events(reason,created) VALUES (?,?)", (reason, time.time()))


def participant_server(config):
    participant = Participant(config)

    class ParticipantHandler(Handler):
        def route(self, path):
            if self.command == "GET" and path == "/health":
                return self.send(200, dict(status="ok", role=participant.name))
            if self.command != "POST" or path not in ("/bid", "/validate"):
                raise TradeOffError("No private data endpoint exists", 404)
            try:
                result = participant.handle(path, self.read_json())
            except TradeOffError as exc:
                if exc.status == 403:
                    participant.denied(str(exc))
                raise
            self.send(200, result)

    serve(ParticipantHandler, config["port"])

