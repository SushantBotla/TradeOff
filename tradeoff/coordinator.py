"""Coordinator runtime: restricted payloads only, no fixture/private DB imports."""

import json
import os
import platform
import threading
import time
import uuid
from pathlib import Path

from . import __version__
from .agent import LLMAgent, safe_action
from .audit import Store
from .common import TradeOffError, canonical, identifier, integer, load_json, object_fields, write_json
from .http import Handler, post_json, serve
from .optimization import check_proposal, solve_restricted, validate_inputs
from .scenarios import FACTORIES, SCENARIOS, SHIPMENT_CONTEXTS
from .security import bearer_matches, sign, verify


def proposal_message(proposal):
    return {key: proposal[key] for key in ("proposal_id", "run_id", "round_id", "allocations", "alternate_qty")}


def disclosure_metrics(transcript):
    incoming = [m for m in transcript if m["direction"] == "participant_to_coordinator"]
    metadata = {"proposal_id"}
    values = sum(len(set(m["payload"]) - metadata) for m in incoming)
    unique = sorted({m["participant"] + "." + field for m in incoming for field in m["payload"] if field not in metadata})
    return dict(participant_message_count=len(incoming), business_scalar_values_transmitted=values,
                unique_business_fields=unique, business_payload_bytes=sum(len(canonical(m["payload"])) for m in incoming),
                envelope_bytes=sum(m["envelope_bytes"] for m in incoming),
                note="Inventory of actual messages, not a privacy guarantee. Feedback and inferred facts can disclose additional information.")


class Coordinator:
    def __init__(self, config, agent_factory=LLMAgent):
        self.config = config
        self.store = Store(config["db_path"], config["audit_key"], recover=True)
        self.agent_factory = agent_factory
        self.active_lock = threading.Lock()
        self.active_run = None

    def health(self):
        agent = self.agent_factory()
        return dict(status="ok", role="coordinator", version=__version__, architecture=platform.machine(),
                    python=platform.python_version(), operating_system=platform.system(),
                    linuxone_architecture=platform.machine().lower() == "s390x", ai=agent.metadata(),
                    isolation=self.config["isolation_mode"], active_run=self.active_run,
                    platform_note="s390x is architecture evidence; confirm LinuxONE using the VM deployment record.")

    def start(self, scenario):
        if not isinstance(scenario, str) or scenario not in SCENARIOS:
            raise TradeOffError("Unknown scenario")
        with self.active_lock:
            if self.active_run:
                raise TradeOffError("Another run is active; wait for it to finish", 409)
            run_id = uuid.uuid4().hex
            self.active_run = run_id
            result = dict(run_id=run_id, scenario_id=scenario, status="running", rounds=[], transcript=[], agent_actions=[],
                          ai=dict(live_llm_calls=0, fallback_used=False), created_at=time.time())
            self.store.create(result)
        threading.Thread(target=self.execute, args=(run_id,), daemon=True).start()
        return result

    def _exchange(self, participant, path, payload, result):
        peer = self.config["peers"][participant]
        run_id = result["run_id"]
        request = sign(payload, peer["key"], "coordinator", participant, path, run_id)
        envelope = post_json(peer["url"] + path, request)
        response = verify(envelope, peer["key"], participant, "coordinator", path + ":response", run_id,
                          db_path=self.config["db_path"])
        if path == "/bid":
            fields = ("primary_capacity", "alternate_capacity", "alternate_unit_cost") if participant == "supplier_s" else ("requested_qty", "priority_signal", "deadline")
            object_fields(response, fields)
        else:
            object_fields(response, ("proposal_id", "accept"), ("minimum_external_qty",))
            if type(response["accept"]) is not bool or response["proposal_id"] != payload["proposal"]["proposal_id"]:
                raise TradeOffError("Participant feedback binding rejected", 502)
            if response["accept"] and "minimum_external_qty" in response:
                raise TradeOffError("Accepted feedback cannot introduce a floor", 502)
            if not response["accept"]:
                integer(response.get("minimum_external_qty"), "minimum_external_qty", high=result["bids"][participant]["requested_qty"])
        message = dict(direction="participant_to_coordinator", participant=participant, path=path,
                       payload=response, authenticated=True, envelope_bytes=len(canonical(envelope)))
        result["transcript"].append(message)
        self.store.event(run_id, "approved_message", message)
        return response

    def execute(self, run_id):
        result = self.store.get(run_id)
        started = time.perf_counter()
        feedback, floors = {}, {}
        try:
            result["bids"] = {n: self._exchange(n, "/bid", dict(scenario_id=result["scenario_id"]), result) for n in FACTORIES}
            result["offer"] = self._exchange("supplier_s", "/bid", dict(scenario_id=result["scenario_id"]), result)
            validate_inputs(result["offer"], result["bids"], {})
            agent = self.agent_factory()
            result["ai"].update(agent.metadata())
            fallback = not agent.configured
            if fallback:
                if agent.mode == "required":
                    raise TradeOffError("Live LLM is required but not configured", 503)
                result["ai"].update(fallback_used=True, fallback_reason="Live LLM disabled or not configured")
            budget = min(120, max(5, float(os.getenv("TRADEOFF_RUN_TIMEOUT", "45"))))
            for step in range(12):
                if not result["rounds"]:
                    self._solve(result, floors)
                proposal = result["rounds"][-1]
                if proposal["status"] != "optimal":
                    result.update(status="unresolved", error="The solver could not produce an optimal proposal under submitted floors")
                    break
                snapshot = dict(bids=result["bids"], supply=result["offer"], proposal=proposal_message(proposal),
                                feedback=feedback, rounds_used=len(result["rounds"]), round_limit=2, shipping_contexts=SHIPMENT_CONTEXTS)
                expected = safe_action(proposal, feedback, len(result["rounds"]))
                remaining = budget - (time.perf_counter() - started)
                if remaining <= 1:
                    fallback = True
                    result["ai"].update(fallback_used=True, fallback_reason="Overall live-model time budget reached")
                if not fallback:
                    try:
                        action = agent.choose(snapshot, timeout=remaining)
                        if action["source"] == "live_llm":
                            result["ai"]["live_llm_calls"] += 1
                        elif action["source"] == "local_ml_assisted_controller":
                            result["ai"].update(local_ml_inferences=agent.prediction_count, risk_predictions=agent.risk_predictions)
                        # Early stop is allowed, but bypassing validation/repair ordering isn't.
                        if action["name"] not in (expected, "declare_unresolved"):
                            raise TradeOffError("LLM action violated the current negotiation state")
                    except TradeOffError as exc:
                        if agent.mode == "required":
                            raise
                        fallback = True
                        result["ai"].update(fallback_used=True, fallback_reason=str(exc))
                if fallback:
                    action = dict(name=expected, arguments=dict(proposal_id=proposal["proposal_id"]), source="deterministic_fallback", latency_ms=0)
                result["agent_actions"].append(action)
                self.store.event(run_id, "agent_action", action)
                name = action["name"]
                if name == "request_validation":
                    order = action.get("validation_order", list(FACTORIES))
                    if len(order) != 2 or set(order) != set(FACTORIES):
                        raise TradeOffError("Invalid validation participant order")
                    feedback = {n: self._exchange(n, "/validate", dict(scenario_id=result["scenario_id"], proposal=proposal_message(proposal)), result) for n in order}
                    for n, item in feedback.items():
                        if not item["accept"]:
                            floors[n] = max(floors.get(n, 0), item["minimum_external_qty"])
                    proposal["feedback"] = feedback
                elif name == "reoptimize_with_feedback":
                    if len(result["rounds"]) >= 2 or not feedback or all(v["accept"] for v in feedback.values()):
                        raise TradeOffError("Reoptimization preconditions failed")
                    self._solve(result, floors)
                    feedback = {}
                elif name == "finalize":
                    if set(feedback) != set(FACTORIES) or not all(v["accept"] for v in feedback.values()):
                        raise TradeOffError("Both factories must accept the current proposal")
                    check_proposal(proposal, result["offer"], result["bids"], floors)
                    result.update(status="completed", final_proposal=proposal)
                    result["explanation"] = (f"Both factories accepted round {proposal['round_id']}. External allocations: "
                                             f"A {proposal['allocations']['factory_a']}, B {proposal['allocations']['factory_b']}; "
                                             f"alternative supply {proposal['alternate_qty']}. "
                                             "Submitted quantity floors were enforced while original priority signals were retained.")
                    break
                else:
                    result.update(status="unresolved", error="No mutually accepted proposal within the bounded negotiation", feedback=feedback)
                    break
                self.store.save(result)
            else:
                result.update(status="unresolved", error="Negotiation step budget reached")
        except TradeOffError as exc:
            result.update(status="failed", error=str(exc))
        except Exception:
            result.update(status="failed", error="Internal coordination error; run the verification suite")
        finally:
            result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
            result["disclosure"] = disclosure_metrics(result["transcript"])
            self.store.save(result)
            head = self.store.event(run_id, "run_finished", dict(status=result["status"], ai=result["ai"], elapsed_ms=result["elapsed_ms"]))
            result["audit_head_at_completion"] = head
            self.store.save(result)
            # This is a public evaluation request, not a private-data query.
            job = {k: result[k] for k in ("run_id", "scenario_id", "status", "rounds")}
            try:
                write_json(Path(self.config["exchange_dir"]) / f"{run_id}.json", job, mode=0o640)
            except OSError:
                result["evaluation_error"] = "Could not publish the separate evaluator's job"
                self.store.save(result)
            finally:
                with self.active_lock:
                    self.active_run = None

    def _solve(self, result, floors):
        round_id = len(result["rounds"]) + 1
        if round_id > 2:
            raise TradeOffError("Two-round solve limit reached")
        proposal = solve_restricted(result["offer"], result["bids"], floors)
        proposal.update(run_id=result["run_id"], round_id=round_id, proposal_id=f"{result['run_id']}_r{round_id}", enforced_floors=dict(floors))
        if proposal["status"] == "optimal":
            check_proposal(proposal, result["offer"], result["bids"], floors)
        result["rounds"].append(proposal)
        self.store.event(result["run_id"], "optimization", proposal)

    def evaluation(self, run_id):
        identifier(run_id)
        path = Path(self.config["reports_dir"]) / f"{run_id}.json"
        return load_json(path) if path.exists() else dict(status="pending", label="Waiting for the separate privileged evaluator")

    def denial_test(self):
        run_id = "denial_" + uuid.uuid4().hex
        target, attacker = self.config["peers"]["factory_a"], self.config["peers"]["factory_b"]
        forged = sign(dict(scenario_id="baseline"), attacker["key"], "factory_b", "factory_a", "/bid", run_id)
        try:
            post_json(target["url"] + "/bid", forged)
            code = 200
        except TradeOffError as exc:
            code = exc.status
        result = dict(denied=code == 403, http_status=code, identity="factory_b", target="factory_a",
                      filesystem_enforcement=self.config["isolation_mode"],
                      note="Real credential-bound API request. Local same-user mode does not enforce filesystem isolation.")
        self.store.event(run_id, "denied_access_test", result)
        return result

    def ml_model(self):
        from .ml import RiskModel
        default = Path(__file__).resolve().parent.parent / "models" / "delivery-risk.json"
        path = Path(os.getenv("TRADEOFF_ML_MODEL_PATH", str(default)))
        if not path.is_file():
            raise TradeOffError("Local risk model is not trained/configured", 503)
        return RiskModel(path)


def coordinator_server(config):
    coordinator = Coordinator(config)
    web = Path(__file__).parent / "web"

    class CoordinatorHandler(Handler):
        def route(self, path):
            if self.command == "GET" and path == "/health":
                return self.send(200, coordinator.health())
            if self.command == "GET" and path == "/site-config.json":
                return self.send(200, dict(mode="live", repository="https://github.com/SushantBotla/TradeOff"))
            if self.command == "GET" and path in ("/", "/index.html", "/workspace.html", "/guide.html", "/app.js", "/home.js", "/style.css", "/favicon.svg"):
                file_name = "index.html" if path == "/" else path[1:]
                content_type = {"html": "text/html", "js": "application/javascript", "css": "text/css", "svg": "image/svg+xml"}[file_name.rsplit(".", 1)[1]]
                return self.send(200, (web / file_name).read_bytes(), content_type + "; charset=utf-8")
            if not bearer_matches(self.headers.get("Authorization"), config["api_token"]):
                coordinator.store.event("security", "dashboard_access_denied", dict(credentials_logged=False))
                raise TradeOffError("Dashboard bearer token required", 401)
            if self.command == "POST":
                body = self.read_json()
                if path == "/api/runs":
                    object_fields(body, ("scenario_id",))
                    return self.send(202, coordinator.start(body["scenario_id"]))
                if path == "/api/demo/reset":
                    object_fields(body, ())
                    with coordinator.active_lock:
                        if coordinator.active_run:
                            raise TradeOffError("Cannot reset while a run is active", 409)
                        coordinator.store.hide()
                    coordinator.store.event("demo", "demo_reset", dict(archived=True, audit_preserved=True))
                    return self.send(200, dict(archived=True, audit_preserved=True))
                if path == "/api/demo/denial-test":
                    object_fields(body, ())
                    return self.send(200, coordinator.denial_test())
                if path == "/api/ml/predict":
                    object_fields(body, ("shipping_mode", "scheduled_days", "market"))
                    return self.send(200, coordinator.ml_model().predict(**body))
            if self.command == "GET":
                if path == "/api/scenarios":
                    return self.send(200, dict(scenarios=SCENARIOS))
                if path == "/api/runs":
                    return self.send(200, coordinator.store.list())
                if path == "/api/audit":
                    return self.send(200, coordinator.store.verify())
                if path == "/api/ml":
                    return self.send(200, {k: v for k, v in coordinator.ml_model().model.items() if k != "weights"})
                parts = path.split("/")
                if len(parts) in (4, 5) and parts[1:3] == ["api", "runs"]:
                    run_id = identifier(parts[3])
                    result = coordinator.store.get(run_id)
                    if not result:
                        raise TradeOffError("Run not found", 404)
                    if len(parts) == 4:
                        return self.send(200, result)
                    if parts[4] == "events":
                        return self.send(200, coordinator.store.events(run_id))
                    if parts[4] == "evaluation":
                        return self.send(200, coordinator.evaluation(run_id))
            raise TradeOffError("Endpoint not found", 404)

    serve(CoordinatorHandler, config["port"])

