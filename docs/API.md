# API v1

The basic UI is replaceable. JSON endpoints use a bearer token generated at initialization. Only static UI assets and `/health` are public. No CORS permission is enabled. Requests require `Content-Type: application/json`, bounded sizes and exact known fields. Numeric fields reject booleans, strings, negatives and nonfinite values.

## Start and inspect

`POST /api/runs` body `{"scenario_id":"baseline"}` returns HTTP202 and a run with `run_id`, `status=running`, `rounds`, `transcript`, `agent_actions` and `ai`. Valid scenario IDs: baseline, primary_loss, combined_loss, no_scarcity, no_alternate. Concurrent starts while one run is active return409.

Poll `GET /api/runs/{id}` until status is completed/unresolved/failed/interrupted. Only completed runs have `final_proposal`. Each optimal proposal contains:

```json
{"proposal_id":"RUN_r2","run_id":"RUN","round_id":2,"status":"optimal","allocations":{"factory_a":560,"factory_b":300},"alternate_qty":60,"surrogate_cost":16950,"backend":"exact_integer","solve_ms":1.2,"enforced_floors":{"factory_b":300}}
```

`GET /api/runs/{id}/events` returns the durable approved event timeline. `GET /api/runs/{id}/evaluation` initially returns pending, then a separate privileged report with oracle status/cost, round true costs, accepted-candidate flag, final true cost, absolute regret and relative optimality gap. Gap is null for unaccepted candidates, infeasible oracle service rules or zero oracle cost.

`GET /api/runs` lists up to40 visible runs. `POST /api/demo/reset` body{} archives them without deleting audit history. Reset while a run is active returns409.

## AI

`GET /api/ml` returns model provenance, features, training/holdout sizes and metrics (no weights required for the UI).

`POST /api/ml/predict`:

```json
{"shipping_mode":"First Class","scheduled_days":1,"market":"USCA"}
```

Returns learned probability, model version, accepted inputs and a provenance/limitations label. Modes: Standard Class, Second Class, First Class, Same Day. Markets: Africa, Europe, LATAM, Pacific Asia, USCA. Scheduled days must be finite0–10. Runtime AI fields distinguish `local_ml_inferences`, successful external `live_llm_calls`, and explicit fallback flags.

## Participant endpoints (internal only)

`POST /bid`: authenticated envelope whose payload is `{"scenario_id":"baseline"}`. A/B return requested_qty, priority_signal and deadline. Supplier returns primary_capacity, alternate_capacity and alternate_unit_cost.

`POST /validate`: A/B only. Payload includes scenario_id and a proposal containing exactly proposal_id, run_id, round_id, allocations and alternate_qty. Returns proposal_id, accept, and minimum_external_qty only on rejection. Never returns stock, true cost curves or customer identifiers.

Envelope: version1, sender, recipient, methodPOST, exact path, run_id, timestamp, random nonce, payload, HMAC-SHA256 mac over canonical JSON excluding mac. Response envelopes reverse sender/recipient and bind `path + ':response'`. Nonces are persisted; timestamps expire; run/scenario/round/proposal binding is enforced.

## Security demo

`POST /api/demo/denial-test` body{} actually sends B's authenticated identity/key to A's endpoint. Expected403 is returned and audited. It separately labels whether OS filesystem isolation is configured; the API test alone does not prove it.

`GET /api/audit` verifies the local hash/HMAC chain and returns its head and assumptions. Use CLI `verify-audit --anchor DIGEST` for an externally retained anchor, or `--tamper-demo` to mutate an in-memory copy without damaging the live log.

