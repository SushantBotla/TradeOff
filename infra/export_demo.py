"""Export approved synthetic results from an authenticated loopback runtime.

Credentials are read from a local file, never included in the public export.
The allowlisted fields contain synthetic coordination messages, not private DBs.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

PROJECT = Path(__file__).resolve().parent.parent
SCENARIOS = ("baseline", "primary_loss", "combined_loss", "no_scarcity", "no_alternate")
RUN_FIELDS = ("run_id", "scenario_id", "status", "created_at", "elapsed_ms", "explanation", "error", "offer", "bids", "rounds", "final_proposal", "transcript", "disclosure", "ai", "agent_actions", "audit_head_at_completion")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--token-file", required=True)
    args = parser.parse_args()
    if args.base_url not in ("http://127.0.0.1:8080", "http://127.0.0.1:8000"):
        parser.error("Use a local runtime or SSH tunnel on port 8000/8080")
    token = Path(args.token_file).read_text().strip()
    opener = build_opener(ProxyHandler({}))

    def request(path, body=None):
        headers = {"Authorization": "Bearer " + token}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(args.base_url + path, headers=headers, data=None if body is None else json.dumps(body).encode())
        with opener.open(req, timeout=20) as response:
            return json.load(response)

    destination = PROJECT / "tradeoff" / "web" / "demo"
    destination.mkdir(parents=True, exist_ok=True)

    def save(name, value):
        serialized = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        if token in serialized:
            raise RuntimeError("Export rejected: credential detected")
        (destination / name).write_text(serialized, encoding="utf-8")

    health = request("/health")
    if health.get("architecture") != "s390x":
        raise RuntimeError("Public fixtures must be recorded on the verified s390x runtime")
    for scenario in SCENARIOS:
        started = request("/api/runs", {"scenario_id": scenario})
        deadline = time.monotonic() + 150
        while True:
            run = request("/api/runs/" + started["run_id"])
            if run["status"] != "running":
                break
            if time.monotonic() > deadline:
                raise RuntimeError("Run timed out")
            time.sleep(.2)
        while True:
            evaluation = request("/api/runs/" + run["run_id"] + "/evaluation")
            if "oracle" in evaluation:
                break
            if time.monotonic() > deadline:
                raise RuntimeError("Evaluator timed out")
            time.sleep(.2)
        save(scenario + ".json", {"provenance": "Recorded execution on the team's LinuxONE VM; synthetic-v1 fixtures; static public replay", "run": {k: run[k] for k in RUN_FIELDS if k in run}, "evaluation": evaluation})
        print(scenario + ": " + run["status"])
    denial = request("/api/demo/denial-test", {})
    audit = request("/api/audit")
    save("verification.json", {"recorded_at": datetime.now(timezone.utc).isoformat(), "runtime": {k: health[k] for k in ("architecture", "python", "isolation", "version") if k in health}, "denial": denial, "audit": audit, "note": "Recorded checks. Verification is rerunnable in the protected runtime; these public records do not contain audit signing keys."})
    save("model.json", json.loads((PROJECT / "models" / "delivery-risk.json").read_text()))


if __name__ == "__main__":
    main()
