"""Message authentication, identity binding and persistent replay protection."""

import hashlib
import hmac
import secrets
import sqlite3
import time

from .common import TradeOffError, canonical, database, identifier, object_fields


def initialize_replays(db_path):
    with database(db_path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS replays (sender TEXT, nonce TEXT, timestamp INTEGER, PRIMARY KEY(sender, nonce))")


def sign(payload, key, sender, recipient, path, run_id, now=None):
    body = dict(version=1, sender=sender, recipient=recipient, method="POST", path=path,
                run_id=identifier(run_id), timestamp=int(time.time() if now is None else now),
                nonce=secrets.token_hex(16), payload=payload)
    body["mac"] = hmac.new(bytes.fromhex(key), canonical(body), hashlib.sha256).hexdigest()
    return body


def verify(envelope, key, sender, recipient, path, run_id=None, db_path=None, now=None):
    object_fields(envelope, ("version", "sender", "recipient", "method", "path", "run_id", "timestamp", "nonce", "payload", "mac"))
    if (type(envelope["version"]) is not int or envelope["version"] != 1 or envelope["sender"] != sender or envelope["recipient"] != recipient
            or envelope["path"] != path or envelope["method"] != "POST"):
        raise TradeOffError("Authenticated identity or request binding rejected", 403)
    identifier(envelope["run_id"])
    if run_id is not None and envelope["run_id"] != run_id:
        raise TradeOffError("Stale run binding rejected", 403)
    if type(envelope["timestamp"]) is not int or abs(int(time.time() if now is None else now) - envelope["timestamp"]) > 90:
        raise TradeOffError("Expired authentication envelope", 403)
    if not isinstance(envelope["nonce"], str) or len(envelope["nonce"]) != 32:
        raise TradeOffError("Invalid nonce", 403)
    if not isinstance(envelope["mac"], str):
        raise TradeOffError("Invalid authentication tag", 403)
    body = {k: v for k, v in envelope.items() if k != "mac"}
    expected = hmac.new(bytes.fromhex(key), canonical(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, envelope["mac"]):
        raise TradeOffError("Message authentication failed", 403)
    if db_path:
        try:
            with database(db_path) as db:
                db.execute("DELETE FROM replays WHERE timestamp < ?", (envelope["timestamp"] - 180,))
                db.execute("INSERT INTO replays VALUES (?,?,?)", (sender, envelope["nonce"], envelope["timestamp"]))
        except sqlite3.IntegrityError:
            raise TradeOffError("Replayed authentication envelope", 403) from None
    return envelope["payload"]


def bearer_matches(header, token):
    return isinstance(header, str) and hmac.compare_digest(header, "Bearer " + token)

