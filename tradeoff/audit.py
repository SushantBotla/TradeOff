"""Durable run storage and a hash/HMAC chain with explicit anchor semantics."""

import hashlib
import hmac
import json
import threading
import time

from .common import canonical, database


class Store:
    def __init__(self, path, key, recover=False):
        self.path, self.key = path, bytes.fromhex(key)
        self.lock = threading.RLock()
        with database(path) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, status TEXT, result TEXT, hidden INTEGER DEFAULT 0, created REAL);
                CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, run_id TEXT, kind TEXT, payload TEXT, created REAL);
                CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, previous TEXT, payload TEXT, digest TEXT, mac TEXT);
            """)
            rows = db.execute("SELECT id,result FROM runs WHERE status='running'").fetchall() if recover else []
            for row in rows:
                result = json.loads(row["result"])
                result.update(status="interrupted", error="Process restarted before the run completed")
                db.execute("UPDATE runs SET status='interrupted',result=? WHERE id=?", (canonical(result).decode(), row["id"]))

    def create(self, result):
        with database(self.path) as db:
            db.execute("INSERT INTO runs(id,status,result,created) VALUES (?,?,?,?)", (result["run_id"], result["status"], canonical(result).decode(), time.time()))

    def save(self, result):
        with database(self.path) as db:
            db.execute("UPDATE runs SET status=?,result=? WHERE id=?", (result["status"], canonical(result).decode(), result["run_id"]))

    def get(self, run_id):
        with database(self.path) as db:
            row = db.execute("SELECT result FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self):
        with database(self.path) as db:
            rows = db.execute("SELECT result FROM runs WHERE hidden=0 ORDER BY created DESC LIMIT 40").fetchall()
        return [json.loads(row[0]) for row in rows]

    def hide(self):
        with database(self.path) as db:
            db.execute("UPDATE runs SET hidden=1")

    def event(self, run_id, kind, payload):
        event = dict(run_id=run_id, kind=kind, payload=payload, timestamp=time.time())
        with self.lock, database(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT digest FROM audit ORDER BY id DESC LIMIT 1").fetchone()
            previous = row[0] if row else "0" * 64
            encoded = canonical(event).decode()
            digest = hashlib.sha256(previous.encode() + encoded.encode()).hexdigest()
            mac = hmac.new(self.key, digest.encode(), hashlib.sha256).hexdigest()
            db.execute("INSERT INTO audit(previous,payload,digest,mac) VALUES (?,?,?,?)", (previous, encoded, digest, mac))
            db.execute("INSERT INTO events(run_id,kind,payload,created) VALUES (?,?,?,?)", (run_id, kind, canonical(payload).decode(), event["timestamp"]))
        return digest

    def events(self, run_id):
        with database(self.path) as db:
            rows = db.execute("SELECT id,kind,payload,created FROM events WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        return [dict(id=r["id"], kind=r["kind"], payload=json.loads(r["payload"]), timestamp=r["created"]) for r in rows]

    def verify(self, anchor=None, mutate_copy=False):
        with database(self.path) as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM audit ORDER BY id")]
        if mutate_copy and rows:
            rows[len(rows) // 2]["payload"] += "tampered"
        previous = "0" * 64
        valid, failure = True, None
        for row in rows:
            digest = hashlib.sha256(previous.encode() + row["payload"].encode()).hexdigest()
            mac = hmac.new(self.key, digest.encode(), hashlib.sha256).hexdigest()
            if row["previous"] != previous or row["digest"] != digest or not hmac.compare_digest(row["mac"], mac):
                valid, failure = False, row["id"]
                break
            previous = digest
        anchor_matches = anchor is None or hmac.compare_digest(previous, anchor)
        return dict(valid=valid and anchor_matches, checked=len(rows), head=previous, failure_event=failure,
                    anchor_checked=anchor is not None, anchor_matches=anchor_matches,
                    assumptions="Local chain verification; privileged key holders can rewrite it. Export an external anchor to detect truncation/rewrite.")
