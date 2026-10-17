#!/usr/bin/env bash
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then echo "Run this check as root." >&2; exit 1; fi
for user in tradeoff-coordinator tradeoff-factory_b; do
  runuser -u "$user" -- /usr/bin/python3 -c '
from pathlib import Path
try:
    with Path("/var/lib/tradeoff/factory_a/private.db").open("rb") as stream:
        stream.read(1)
except PermissionError:
    print("PASS: private Factory A DB read denied")
else:
    raise SystemExit("FAIL: private Factory A DB was readable")
'
done
runuser -u tradeoff-evaluator -- /usr/bin/python3 -c '
import sqlite3
db=sqlite3.connect("file:/var/lib/tradeoff/factory_a/private.db?mode=ro",uri=True)
assert db.execute("SELECT count(*) FROM profiles").fetchone()[0] > 0
db.close()
print("PASS: privileged evaluator can read synthetic benchmark data")
'
echo "Filesystem checks pass. VM root/administrators remain trusted."

