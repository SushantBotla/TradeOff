"""Small shared primitives; no private participant data lives in this module."""

import contextlib
import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path


class TradeOffError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def object_fields(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise TradeOffError("Payload fields do not match the documented contract")
    return value


def integer(value, name, low=0, high=5000):
    if type(value) is not int or not low <= value <= high:
        raise TradeOffError(f"{name} must be an integer between {low} and {high}")
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", value):
        raise TradeOffError("Invalid identifier")
    return value


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".tradeoff-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json.dumps(value, indent=2, allow_nan=False).encode() + b"\n")
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def database(path, readonly=False):
    if readonly:
        connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    else:
        connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def load_env(path):
    """Read simple KEY=value configuration without executing shell expressions."""
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise TradeOffError("Environment file requires KEY=value lines")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"TRADEOFF_[A-Z0-9_]+", key):
            raise TradeOffError("Only TRADEOFF_ settings are accepted in this file")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)
