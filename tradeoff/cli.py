"""Development launcher and administrative commands; no shell-based secret handling."""

import argparse
import contextlib
import hashlib
import json
import os
import signal
import socket
import statistics
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

from .common import TradeOffError, load_env, load_json, write_json

PROJECT = Path(__file__).resolve().parent.parent


def get_json(url, token=None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    with build_opener(ProxyHandler({})).open(Request(url, headers=headers), timeout=3) as response:
        return json.load(response)


def dev(args):
    from .bootstrap import initialize
    config = initialize(args.root, args.port)
    root = Path(args.root).resolve()
    with socket.socket() as check:
        if check.connect_ex(("127.0.0.1", config["port"])) == 0:
            raise TradeOffError("The configured UI port is already in use; stop the existing launcher or initialize a different root/port")
    children, handles = [], []
    try:
        for role in ("factory_a", "factory_b", "supplier_s", "evaluator", "coordinator"):
            log = (root / "logs" / (role + ".log")).open("a", encoding="utf-8")
            handles.append(log)
            env = dict(os.environ)
            if role != "coordinator":
                env = {k: v for k, v in env.items() if not k.startswith("TRADEOFF_LLM_")}
            command = [sys.executable, "-m", "tradeoff", "serve", "--config", str(root / role / "config.json")]
            if role == "coordinator":
                command += ["--env-file", str(Path(args.env_file).resolve())]
            options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
            children.append(subprocess.Popen(command, cwd=PROJECT, env=env, stdout=log, stderr=log, **options))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if any(p.poll() is not None for p in children):
                raise TradeOffError("A service exited during startup; inspect runtime logs")
            try:
                get_json(f"http://127.0.0.1:{config['port']}/health")
                break
            except (OSError, URLError, ValueError):
                time.sleep(0.2)
        else:
            raise TradeOffError("Coordinator startup timed out; inspect runtime logs")
        print(f"TradeOff: http://127.0.0.1:{config['port']}", flush=True)
        print(f"Login token file: {root / 'coordinator' / 'dashboard-token.txt'}", flush=True)
        print("Five separate local processes are running under the current OS user. Use infra/install_linuxone.sh for enforced service-user isolation.", flush=True)
        print("Press Ctrl+C to stop all services.", flush=True)
        while True:
            if any(p.poll() is not None for p in children):
                raise TradeOffError("A service stopped unexpectedly; inspect runtime logs")
            time.sleep(0.5)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            with contextlib.suppress(subprocess.TimeoutExpired):
                child.wait(timeout=5)
            if child.poll() is None:
                child.kill()
        for handle in handles:
            handle.close()


def service(args):
    config = load_json(args.config)
    if config["role"] == "coordinator":
        load_env(args.env_file)
        from .coordinator import coordinator_server
        coordinator_server(config)
    elif config["role"] == "evaluator":
        from .evaluation import Evaluator
        Evaluator(config).watch()
    else:
        from .participants import participant_server
        participant_server(config)


def smoke(config, scenario="baseline"):
    from .http import post_json
    base = f"http://127.0.0.1:{config['port']}"
    result = post_json(base + "/api/runs", dict(scenario_id=scenario), headers={"Authorization": "Bearer " + config["api_token"]})
    deadline = time.monotonic() + 135
    while time.monotonic() < deadline:
        result = get_json(base + "/api/runs/" + result["run_id"], config["api_token"])
        if result["status"] != "running":
            break
        time.sleep(0.2)
    if result["status"] != "completed":
        raise TradeOffError("Smoke run did not complete: " + result.get("error", result["status"]))
    report = None
    for _ in range(40):
        report = get_json(base + "/api/runs/" + result["run_id"] + "/evaluation", config["api_token"])
        if "oracle" in report:
            break
        time.sleep(0.2)
    if "oracle" not in (report or {}):
        raise TradeOffError("Separate evaluator did not return a report")
    return dict(run_id=result["run_id"], status=result["status"], final_proposal=result["final_proposal"],
                ai=result["ai"], evaluation=report, elapsed_ms=result["elapsed_ms"])


def package(destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "tradeoff-source.zip"
    files = []
    for folder in ("tradeoff", "tests", "infra", "docs", "models"):
        files += [p for p in (PROJECT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    files += [PROJECT / p for p in ("README.md", "LICENSE", "pyproject.toml", "requirements-solver.txt", ".env.example", ".gitignore", "TradeOff-15-hour-plan.md", "tradeoff_validation.py") if (PROJECT / p).exists()]
    manifest = {}
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            relative = path.relative_to(PROJECT).as_posix()
            archive.write(path, relative)
            manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        archive.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
    return dict(artifact=str(output), sha256=hashlib.sha256(output.read_bytes()).hexdigest(), files=len(files), credentials_included=False)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tradeoff")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "dev"):
        command = sub.add_parser(name)
        command.add_argument("--root", default=".tradeoff")
        command.add_argument("--port", type=int, default=8000)
        command.add_argument("--env-file", default=".env")
        if name == "init":
            command.add_argument("--isolated", action="store_true")
    command = sub.add_parser("serve")
    command.add_argument("--config", required=True)
    command.add_argument("--env-file", default=".env")
    for name in ("doctor", "smoke", "verify-audit", "token"):
        command = sub.add_parser(name)
        command.add_argument("--config", default=".tradeoff/coordinator/config.json")
        if name == "smoke":
            command.add_argument("--scenario", default="baseline")
        if name == "verify-audit":
            command.add_argument("--anchor")
            command.add_argument("--tamper-demo", action="store_true")
    command = sub.add_parser("evaluate")
    command.add_argument("--config", default=".tradeoff/evaluator/config.json")
    command = sub.add_parser("package")
    command.add_argument("--output", default="dist")
    command = sub.add_parser("benchmark")
    command.add_argument("--repetitions", type=int, default=20)
    command.add_argument("--output", default="test-results/solver-benchmark.json")
    command = sub.add_parser("import-dataco")
    command.add_argument("csv_path")
    command.add_argument("--output", default=".tradeoff/dataco-summary.json")
    command = sub.add_parser("train-risk-model")
    command.add_argument("csv_path")
    command.add_argument("--output", default="models/delivery-risk.json")
    command.add_argument("--epochs", type=int, default=6)
    args = parser.parse_args(argv)
    try:
        if args.command == "dev":
            dev(args)
            return
        if args.command == "init":
            from .bootstrap import initialize
            config = initialize(args.root, args.port, args.isolated)
            result = dict(initialized=True, ui_port=config["port"], root=str(Path(args.root).resolve()))
        elif args.command == "serve":
            service(args)
            return
        elif args.command == "token":
            print(load_json(args.config)["api_token"])
            return
        elif args.command == "doctor":
            config = load_json(args.config)
            result = get_json(f"http://127.0.0.1:{config['port']}/health")
            result["participant_health"] = {n: get_json(peer["url"] + "/health") for n, peer in config["peers"].items()}
            result["evaluation_reports_present"] = any(Path(config["reports_dir"]).glob("*.json"))
        elif args.command == "smoke":
            result = smoke(load_json(args.config), args.scenario)
        elif args.command == "verify-audit":
            from .audit import Store
            config = load_json(args.config)
            store = Store(config["db_path"], config["audit_key"])
            result = store.verify(anchor=args.anchor)
            if args.tamper_demo:
                result["tampered_copy"] = store.verify(mutate_copy=True)
        elif args.command == "evaluate":
            from .evaluation import Evaluator
            Evaluator(load_json(args.config)).process_once()
            result = dict(processed=True)
        elif args.command == "package":
            result = package(args.output)
        elif args.command == "import-dataco":
            from .dataco import summarize
            result = summarize(args.csv_path)
            write_json(args.output, result)
        elif args.command == "train-risk-model":
            from .ml import train
            if not 1 <= args.epochs <= 30:
                raise TradeOffError("Training epochs must be between 1 and 30")
            result = train(args.csv_path, args.output, epochs=args.epochs)
        else:
            from .optimization import solve_restricted
            if not 1 <= args.repetitions <= 1000:
                raise TradeOffError("Repetitions must be between 1 and 1000")
            samples = []
            bids = {"factory_a": dict(requested_qty=560, priority_signal=165, deadline="day_5"),
                    "factory_b": dict(requested_qty=450, priority_signal=75, deadline="day_5")}
            for _ in range(args.repetitions):
                solved = solve_restricted(dict(primary_capacity=800, alternate_capacity=300, alternate_unit_cost=95), bids, {"factory_b": 300})
                samples.append(solved["solve_ms"])
            result = dict(sample_size=len(samples), p50_ms=statistics.median(samples), p95_ms=sorted(samples)[max(0, int(len(samples) * .95 + .999) - 1)],
                          backend=solved["backend"], scope="solver only; excludes model, HTTP and evaluator")
            write_json(args.output, result)
        print(json.dumps(result, indent=2))
    except KeyboardInterrupt:
        pass
    except (TradeOffError, OSError, ValueError) as exc:
        print("TradeOff: " + str(exc), file=sys.stderr)
        raise SystemExit(1) from None
