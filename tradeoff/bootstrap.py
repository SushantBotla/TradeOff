"""Administrative provisioning only. The coordinator does not import this."""

import os
import secrets
from pathlib import Path

from .common import canonical, database, load_json, write_json
from .fixtures import factory_profiles, supplier_profiles
from .security import initialize_replays


def initialize(root, port=8000, isolated=False):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    existing = root / "coordinator" / "config.json"
    if existing.exists():
        return load_json(existing)
    for name in ("factory_a", "factory_b", "supplier_s", "coordinator", "evaluator", "exchange", "reports", "logs"):
        directory = root / name
        directory.mkdir(exist_ok=True)
        os.chmod(directory, 0o700)
    peers = {}
    private_databases = {}
    for offset, name in enumerate(("factory_a", "factory_b", "supplier_s"), 1):
        directory = root / name
        db_path = directory / "private.db"
        profiles = supplier_profiles() if name == "supplier_s" else factory_profiles(name)
        with database(db_path) as db:
            db.execute("CREATE TABLE profiles (scenario_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE run_bindings (run_id TEXT PRIMARY KEY, scenario_id TEXT, latest_round INTEGER DEFAULT 0)")
            db.execute("CREATE TABLE denied_events (id INTEGER PRIMARY KEY, reason TEXT, created REAL)")
            for scenario, profile in profiles.items():
                profile["private_canary"] = "PRIVATE_" + secrets.token_hex(24)
                db.execute("INSERT INTO profiles VALUES (?,?)", (scenario, canonical(profile).decode()))
        initialize_replays(db_path)
        os.chmod(db_path, 0o600)
        key = secrets.token_hex(32)
        config = dict(role=name, db_path=str(db_path), key=key, port=port + offset)
        write_json(directory / "config.json", config)
        peers[name] = dict(url=f"http://127.0.0.1:{port + offset}", key=key)
        private_databases[name] = str(db_path)
    coordinator = dict(role="coordinator", port=port, db_path=str(root / "coordinator" / "audit.db"),
                       audit_key=secrets.token_hex(32), api_token=secrets.token_urlsafe(32), peers=peers,
                       exchange_dir=str(root / "exchange"), reports_dir=str(root / "reports"),
                       isolation_mode="linux_service_users" if isolated else "local_same_user")
    initialize_replays(coordinator["db_path"])
    write_json(existing, coordinator)
    token_file = root / "coordinator" / "dashboard-token.txt"
    token_file.write_text(coordinator["api_token"] + "\n", encoding="utf-8")
    os.chmod(token_file, 0o600)
    write_json(root / "evaluator" / "config.json", dict(role="evaluator", private_databases=private_databases,
               exchange_dir=str(root / "exchange"), reports_dir=str(root / "reports")))
    return coordinator

