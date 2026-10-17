# TradeOff: validated scope and six-person, 15-hour execution plan

Prepared October 17, 2026. Requirements supplied by the team: approximately 15 hours remaining; LinuxONE and an AI/LLM feature are mandatory. Times below are elapsed hours from team kickoff, not local clock times.

**Final requirement clarification:** the team confirmed that a real AI/ML feature is sufficient. The shipped product therefore uses a trained DataCo logistic regression for delivery-risk inference on LinuxONE, rather than requiring an external LLM. The controller is deterministic and the exact solver remains authoritative. References below to mandatory LLM access describe the initial proposal and are superseded by this clarification. The six-role ownership and integration tasks remain applicable.

## Decision and objective

**Proceed with a reduced prototype.** TradeOff has a concrete problem, a visible disruption demo, a defensible optimization component, and a useful role for an LLM. The full pasted specification is too broad for the remaining time and contains incorrect numerical and security claims.

**Objective:** On a real LinuxONE VM, demonstrate an LLM coordination agent helping two manufacturers and one supplier replan a component shortage through restricted messages. A deterministic solver produces allocations; participant services validate them locally; a dashboard shows the negotiation, true simulated cost, disclosed messages, and a full-information benchmark.

One-sentence pitch: **“TradeOff helps companies coordinate during a shortage while keeping their underlying inventory and customer cost curves within participant services.”**

Go/no-go dependencies in hour 1: a reachable LinuxONE VM, permission to install/run the app, working solver, and a successful real LLM API call originating from the VM. Confirm that an externally hosted model called by the LinuxONE application satisfies the event rules. Local model inference is a separate requirement and is not assumed. If required access is unavailable, the team lead must contact organizers immediately while the other five continue against fixtures; a laptop-only demo does not meet the supplied LinuxONE requirement.

## Corrections to the pasted plan

### Mathematics and experiment

The equations in the supplied plan do not include batch constraints. For those equations, the baseline full-information optimum is:

| Quantity | Value |
|---|---:|
| External allocation A / B | 500 / 300 |
| Internal stock used A / B | 40 / 50 |
| Shortage A / B | 60 / 150 |
| Alternative supply | 0 |
| True cost | $14,700 |

Cost = 40×45 + 50×30 + 60×90 + 150×40 = $14,700. A's mild shortage costs $90 per chip, below the $95 alternative supply cost. The asserted optimum with 60 alternative chips costs $15,000 and is not optimal under the written objective.

Exhaustive integer-chip checks reproduce these results:

| Policy at baseline | xA | xB | Alternative | True cost | Gap vs oracle |
|---|---:|---:|---:|---:|---:|
| Full-information oracle | 500 | 300 | 0 | $14,700 | 0% |
| Initial coarse bids 165 / 75 | 560 | 240 | 0 | $15,900 | 8.16% |
| Original revision: raise all B priority to 110 | 560 | 450 | 210 | $23,250 | 58.16% |
| Proposed repair: retain bids; add B floor of 300 | 560 | 300 | 60 | $15,000 | 2.04% |

B needs external allocation 500 − 50 − 150 = **300** to avoid its severe shortage tier in this example. A floor of 350 is not implied by the stated costs. Raising B's entire linear priority above the alternative unit cost makes the coordinator buy all of B's remaining demand. A local quantity floor is a smaller, interpretable revision; it does reveal information and must be counted in the transcript.

At primary capacity 480 and alternative capacity 300, the oracle cost is $44,900; the proposed repaired allocation is A=480, B=300, alternative=300, true cost=$45,000, gap≈0.22%. These are synthetic fixture results, not expected performance guarantees.

An alternative-capacity change from 300 to 150 has no effect on the baseline oracle because it buys zero alternative chips. Use primary capacity loss as the required second demo. A combined primary=480, alternative=150 case can test unresolved negotiation: disclosed service floors A=460 and B=300 require 760 external units, above the available 630. Physical allocations with shortages remain possible; all declared floors cannot be met together.

For the MVP:

- Omit batches entirely from both oracle and coordinated modes. If added later, specify whether batches constrain received chips or production after stock draw, and implement the same feasible set in both modes.
- Treat priorities as deterministic policy signals for cooperative simulated participants. Do not claim truthful bidding. Payment-backed bids alone do not make a mechanism incentive compatible.
- Do not implement payments. Transfers between participants are not extra network resource costs. Primary production cost is treated as committed/sunk in this toy objective.
- Do not promise a 4–7% gap, an improvement every round, or nonzero gaps in every scenario. Report measured values, including zero and poor results.
- A hard guarantee to fully serve medical orders would require an additional constraint in both modes and would change the benchmark. The current objective permits some A shortages.
- If avoiding severe shortage is a mandatory service rule, impose `x_i + u_i >= demand_i - mild_threshold_i` in the oracle too, and enforce it through participant acceptance in coordinated mode. Both reported baseline and primary-loss oracle solutions already satisfy that rule, so their numbers stay unchanged. When the rule is impossible, report unresolved service requirements rather than compare an unaccepted candidate as a successful outcome.
- This experiment measures decision quality under restricted/coarse information, not a formal privacy guarantee or a proven privacy-efficiency frontier.

### Deployment and security

- PuLP 4.0.1 does have breaking APIs and a Rust core, but its current release includes CPython 3.12 s390x wheels. “PuLP 4 always fails on s390x” is incorrect. Pinning PuLP 3.3.1 remains a reasonable way to retain the intended 3.x API. Use the OS CBC executable explicitly through `COIN_CMD`, not an assumed bundled native binary. Ubuntu 24.04 lists a CBC s390x package. [PuLP 4.0.1](https://pypi.org/project/PuLP/4.0.1/), [PuLP 3.3.1](https://pypi.org/project/PuLP/3.3.1/), [Ubuntu CBC](https://packages.ubuntu.com/noble/coinor-cbc).
- FastAPI with Pydantic 2 is not a dependency-free escape route: Pydantic uses a Rust core, and the pinned core 2.23.4 release has no listed s390x wheel. Timebox the actual VM install to 20 minutes. Keep FastAPI if it already works; otherwise use Flask/Jinja2 with explicit JSON schema checks and preserve the agreed API contract. Freeze that decision by hour 1. Avoid building a new web stack twice. [Pydantic core](https://github.com/pydantic/pydantic-core), [2.23.4 files](https://pypi.org/project/pydantic_core/2.23.4/), [Flask installation](https://flask.palletsprojects.com/en/stable/installation/).
- Use SSH forwarding for the single presentation port. The community deployment guide documents SSH-only inbound access by default. Confirm the actual VM rules. [LinuxONE guide](https://github.com/linuxone-community-cloud/technical-resources/blob/master/faststart/deploy-virtual-server.md).
- Four database files and router namespaces do not enforce isolation when one process/user can read everything. Use separate unprivileged Linux service users and private directories, or existing container volume isolation. Test actual filesystem denial. One VM still trusts its host administrator.
- Authenticate callers from credentials, never from `?requester=factory_b`. Authenticate signed messages with per-participant HMAC keys, round/run binding and replay checks. HMAC authenticates message integrity; it does not encrypt messages or prove truthful contents. Shared-key HMAC is not a public-key signature. [Python HMAC](https://docs.python.org/3/library/hmac.html).
- Call the audit log **tamper-evident under the stated key/anchor assumptions**, not immutable. A privileged key holder can rewrite a local chain. Keep a copy of the final chain digest outside the service if demonstrating tamper detection.
- Architecture detection shows s390x; use the actual VM deployment record to support the LinuxONE claim. Python HMAC plus s390x does not independently prove which hardware crypto path ran. CPACF-specific proof is a stretch item. [IBM OpenSSL guidance](https://www.ibm.com/docs/en/linux-on-systems?topic=linuxone-about-this-document).
- Field counts are a disclosure inventory, not a privacy score. The pasted 20 raw fields versus 9 derived fields mix different information categories and omit later revisions. Count actual approved payloads, feedback, values and bytes, and acknowledge inference from them.

## MVP to freeze now

Required:

1. Two deterministic factory services, one deterministic supplier service, one LLM coordination agent.
2. Synthetic data matching the corrected example, with separate private stores.
3. A full-information oracle in a separate evaluation process and a restricted-information optimizer in the coordinator.
4. At most two allocation rounds, local validation after every proposal, and explicit unresolved/failure states.
5. A real LLM tool/action trace used in the negotiation, with grounded explanation.
6. Baseline and primary-loss presets, live restricted-mode computation, cost/quality comparison and message inspection.
7. A live LinuxONE deployment, real credential-based denial test, restart/reset path and rehearsed demo.

Cut now: batching, financial settlement, strategic-bid truthfulness claims, real customer data, ERP connectors, blockchain, multi-day scheduling, model fine-tuning, large agent frameworks, continuous sliders, large scenario sweeps and CPACF performance claims. Use fixed deadline metadata; the alternate capacity means capacity available before that deadline.

## Architecture and AI behavior

```text
Presentation browser -> SSH tunnel -> LinuxONE dashboard/coordinator :8000
                                           |
                           approved messages and authenticated APIs
                              /            |            \
                     Factory A         Factory B      Supplier S
                     own user/DB       own user/DB    own user/DB
                                           |
                         LLM API receives allowlisted transcript only

Separate evaluator: private synthetic fixture -> oracle + true-cost report
Dashboard may display evaluator report; coordinator/LLM cannot query raw data.
```

Participant services may listen only on loopback. Use distinct identities and credentials despite sharing a VM. The dashboard's benchmark pane is a privileged research/demo view; do not pretend that publishing true costs and oracle allocations reveals no extra information.

The LLM should perform a real coordination task, not merely add a decorative paragraph:

1. Read approved bids and the initial solver proposal.
2. Choose participant validation requests through `request_validation(participant, proposal_id)`.
3. Read accept/revise feedback. If a participant submits a floor, choose `reoptimize_with_feedback(feedback_ids)`; the tool uses stored authenticated feedback and accepts no invented numeric constraints.
4. After all validations accept, choose `finalize(proposal_id)` and write a brief explanation tied to observed quantities. If unresolved, describe the conflict without inventing a resolution.

Host code enforces valid actions, required validation from both factories, known IDs, maximum two solver rounds and a small LLM call budget. The solver sets all quantities. A schema validator rejects invented participants, unauthorized tools, unrecognized fields and unsupported numeric claims. Log the allowed action/observation trace; do not request or expose hidden model reasoning.

Use a provider/model the team can call successfully now. Run the agent/client on LinuxONE; an external provider hosts inference unless the rules say otherwise. Do not train or port a model in this build window. On timeout or invalid output, show a clearly labeled deterministic fallback. A fallback keeps the app useful but does not replace the required successful live AI demonstration.

## Shared contracts: finish in the first 30 minutes

Person 3 owns the contract file; Persons 2 and 4 co-review it. Others build against sample JSON immediately. Freeze version 1 after 30 minutes. Schema changes require an example and direct notice to the other owners.

| Contract | Required content |
|---|---|
| Factory bid | run_id, round_id, participant_id, requested_qty, priority_signal, deadline; authenticated envelope |
| Supply offer | run_id, primary_capacity, alternate_capacity, alternate_unit_cost, deadline; authenticated envelope |
| Proposal | proposal_id, run_id, round_id, xA, xB, alternate_qty, surrogate_cost, solver_status, solve_ms |
| Local feedback | proposal_id, participant_id, accept; optional minimum_external_qty; authenticated envelope |
| Agent action | one allowed tool name and validated IDs/arguments; displayable short rationale |
| Run result | status, final proposal if accepted, round history, approved transcript, model/provider label, AI/fallback flag, timing |
| Evaluation report | fixture_id/version, policy/version, oracle_status/cost, candidate true cost, gap or N/A, public benchmark label |

Keep business fields separate from envelope metadata such as nonce, timestamp, key_id and HMAC. Canonicalize exactly the authenticated payload. Bind feedback to a proposal; reject stale or duplicate submissions.

Minimum external endpoints: `GET /health`, `POST /api/runs` with preset ID, `GET /api/runs/{id}`, `GET /api/runs/{id}/events`, `POST /api/demo/reset`, and a controlled credential-based denial-test action. Participant endpoints: authenticated `POST /bid` and factory `POST /validate`; no raw-database endpoint is needed. The evaluator is a separate CLI/job, not a coordinator tool.

Minimum fixtures: `baseline` (800/300) and `primary_loss` (480/300). Put both under version control and mark synthetic. Person 2 produces oracle results; Person 6 independently checks costs. A continuous dashboard scenario slider is outside scope.

## Six roles: independent ownership and exact tasks

All six start together. No person waits for another person's complete implementation; fixtures and stubs are the first deliverables. Each owner also writes focused tests for their numerical, security or failure-handling behavior. Person 6 owns integrated acceptance.

### Person 1 — LinuxONE platform, isolation and release

Own: `infra/`, dependency lock, startup scripts and telemetry. Do not edit API or solver files.

- [ ] P1.1 (H0–1) SSH into the actual VM, record architecture/OS/Python, verify install permissions, available memory and outbound LLM connectivity with Person 4. **Done:** VM evidence and successful outbound test recorded.
- [ ] P1.2 (H0–1) Install/test PuLP 3.3.1 plus OS CBC; run a tiny solve. Timebox web dependency installation and freeze FastAPI or Flask. **Done:** imports, HTTP health route and solver pass on s390x; exact versions saved.
- [ ] P1.3 (H1–3) Create four unprivileged service users/private directories, or reuse functioning containers with exclusive mounts. Give no coordinator access to participant files. Provide a separate evaluator identity for synthetic benchmark access. **Done:** actual coordinator and B users cannot open A's DB.
- [ ] P1.4 (H1–4) Create start/stop/status scripts, bind internal services to loopback and expose the UI through an SSH tunnel. **Done:** another teammate opens the VM-served dashboard.
- [ ] P1.5 (H3–6) Deploy integrated increments, set credentials through environment/protected config, serve CSS/JS locally and add architecture/build/health metadata. **Done:** no CDN dependency and no secrets in repo or UI.
- [ ] P1.6 (H6–10) Exercise restart, reseed and tunnel recovery; package the repository and runbook. **Done:** restart/reseed succeeds from documented steps without manual source edits.
- [ ] P1.7 (H10–15) Own the release freeze, final build identifier, deployment verification, backup recording storage and submission package with Person 6. **Done:** submitted version matches the rehearsed VM version.

First handoff: base URL, selected Python/web stack and solver smoke result by H1. Dependencies: API stub from Person 3; model test from Person 4. Parallel fallback: deploy a health-only service while application modules are still stubs.

### Person 2 — Optimization, mathematical correctness and oracle

Own: `optimization/`, `evaluation/`, mathematical fixture definitions. No web or LLM code.

- [ ] P2.1 (H0–0.5) Freeze units, true cost formula, variable bounds, no-batch scope, stock treatment and synthetic parameters with Person 3. **Done:** shared fixture and function signatures published.
- [ ] P2.2 (H0.5–2) Implement pure `solve_restricted(offers, bids, feedback)` using the system solver; constrain allocations to requests, supply and authenticated floors. **Done:** baseline first-round proposal reproduces A560/B240/y0.
- [ ] P2.3 (H1–3) Implement `solve_oracle(private_fixture)` and `evaluate_true_cost(allocation, private_fixture)` in the separate evaluation path. Apply the same service rules as participant acceptance. **Done:** oracle baseline $14,700 and primary-loss $44,900 reproduced; impossible service requirements identified.
- [ ] P2.4 (H2–4) Implement floor-only repair while retaining original priority signals. **Done:** baseline A560/B300/y60, cost $15,000; primary-loss A480/B300/y300, cost $45,000.
- [ ] P2.5 (H3–5) Handle solver errors, invalid inputs, time limits and infeasible floors explicitly; report actual solver status. **Done:** no fake optimum, negative allocation or silent constraint relaxation.
- [ ] P2.6 (H4–7) Generate versioned oracle reports; ensure coordinator imports neither private fixtures nor oracle functions. **Done:** both candidate and oracle are evaluated using identical true cost definitions.
- [ ] P2.7 (H7–10) Cross-check with Person 6's independent tiny-instance checker, record solver latency and resolve numerical discrepancies. **Done:** numeric acceptance tests pass and gaps cannot be materially negative under equivalent constraints.

First handoff: fixture and stub signatures by H0.5; working restricted solve by H2. Dependencies: schema from Person 3, CBC path from Person 1. Parallel fallback: use the supplied stdlib checker locally to establish expected outputs while CBC is installed.

### Person 3 — Backend, participant services and authenticated data exchange

Own: `contracts/`, `services/`, persistence and audit implementation. No optimizer internals or prompt changes.

- [ ] P3.1 (H0–0.5) Publish versioned request/response examples, shared schema and endpoint contract. **Done:** Persons 2, 4 and 5 can implement against fixtures.
- [ ] P3.2 (H0.5–2) Create API skeleton, run IDs, scenario selection, status/events, reset route and stubs for solver and agent. **Done:** frontend can complete a mocked run over HTTP.
- [ ] P3.3 (H1–4) Seed three private participant stores plus coordinator audit DB; implement factory bid export and supplier offer export with field allowlists. **Done:** raw stock and penalty fields do not leave participant APIs.
- [ ] P3.4 (H2–5) Implement local validation: check capacity/request validity and reject severe-shortage exposure using approved minimum-quantity feedback. Keep cost curves private. **Done:** B's first baseline response asks for minimum 300 without raw cost fields.
- [ ] P3.5 (H2–5) Implement credential-derived identity, per-participant HMAC verification, run/round/proposal binding and replay rejection. **Done:** modified, stale, duplicate and cross-identity requests fail.
- [ ] P3.6 (H4–7) Add hash-chained audit events and verification command; persist only approved messages, actions and public outputs in the coordinator DB. **Done:** changed audit payload fails verification against the saved chain digest.
- [ ] P3.7 (H5–9) Integrate solver and bounded LLM loop, cancellation/reset and final validation gating. **Done:** successful and unresolved runs have unambiguous statuses and reproducible event histories.
- [ ] P3.8 (H9–11) Remove private fixture imports from coordinator paths, redact secrets/logs and run contract tests with Persons 1 and 6. **Done:** no participant DB path accessible to the coordinator identity and no caller-selected identity bypass.

First handoff: JSON examples by H0.5; health/run stub by H1.5. Dependencies: optimizer callable from Person 2; action loop from Person 4; operating-system identities from Person 1. Use stubs until those arrive.

### Person 4 — LLM coordination agent and grounded explanation

Own: `agent/`, prompt, tool adapters, action validation and agent trace. Do not edit private participant databases.

- [ ] P4.1 (H0–1) Verify provider access with a real call from LinuxONE; record model name, timeout and event eligibility assumption. **Done:** successful response and timestamp visible to the team, without credentials.
- [ ] P4.2 (H0.5–2) Define allowlisted agent input and the three tools: validation request, reoptimization from stored feedback, finalization. **Done:** sample input/output and expected tool sequence agreed with Person 3.
- [ ] P4.3 (H1–4) Implement the actual LLM call loop against mock tools, then live adapters. **Done:** model actions invoke tools that participate in the final run; outputs are not canned text.
- [ ] P4.4 (H2–5) Enforce bounded calls, maximum two allocation rounds, JSON/action schema, valid IDs, required participant validations and no arbitrary code/tools. **Done:** invalid output cannot modify quantities or bypass acceptance.
- [ ] P4.5 (H3–6) Generate a short explanation from actual approved messages and solver results. Do not mention private reasons unless explicitly disclosed. **Done:** quantities and claims match tool observations.
- [ ] P4.6 (H4–7) Add latency/error handling and a visibly labeled deterministic fallback. **Done:** provider timeout leaves a usable, honest app and a recorded error; the demo still includes a real successful model run.
- [ ] P4.7 (H6–10) Inspect captured model requests for private canary values; test unsupported actions, prompt-like participant text and conflicting feedback. Keep transcript fields structured and bounded. **Done:** only approved data reaches the provider and no text field grants extra tool authority.

First handoff: real provider test by H1; working mock-tool loop by H3. Dependencies: contract from Person 3. Parallel fallback: mock participant APIs while live services are being implemented. Do not wait for UI.

### Person 5 — Dashboard and interaction design

Own: `templates/`, `static/` and browser presentation. Use fixture JSON until APIs are live.

- [ ] P5.1 (H0–1) Sketch one screen: scenario controls, network allocation, round timeline, actual LLM actions, benchmark cost and disclosure pane. **Done:** layout agreed without a second design cycle.
- [ ] P5.2 (H0.5–3) Build baseline/primary-loss buttons, Run/Reset and readable loading/error/unresolved states against sample responses. **Done:** complete mocked walkthrough.
- [ ] P5.3 (H2–5) Connect run creation and status/events; show allocations, alternate supply, model/provider and live/fallback indicators. **Done:** an actual backend run updates the screen.
- [ ] P5.4 (H3–6) Display surrogate objective separately from true benchmark cost, oracle status and measured gap. Label synthetic data and privileged evaluation view. **Done:** no metric misrepresents what the coordinator knows.
- [ ] P5.5 (H4–7) Add expandable approved-message transcript, business-field/value/byte counts and the feedback floor visibly added in round 2. **Done:** judge can inspect actual disclosures.
- [ ] P5.6 (H5–8) Add architecture/build banner and credential-based access-denial demo result; keep platform claims factual. **Done:** live VM status and real denial result shown.
- [ ] P5.7 (H7–11) Package local assets, improve projector readability and disable duplicate Run clicks. Exercise both presets and failure states with Person 6. **Done:** repeated presentation runs work without refreshing or editing data manually.

First handoff: mock-data dashboard by H3. Dependencies: JSON contract from Person 3; later live endpoints. Do not wait for finished optimization or model integration.

### Person 6 — Independent verification, demo narrative and submission

Own: `tests/acceptance/`, independent validation artifact, `docs/`, demo script and submission text. Begin technical QA immediately, not after coding finishes.

- [ ] P6.1 (H0–1) Check actual event requirements, judging rubric, submission format and remote-model eligibility; freeze success checklist with all owners. **Done:** mandatory requirements and deadline documented.
- [ ] P6.2 (H0–2) Run the supplied checker, independently verify the baseline cost arithmetic and make expected-output fixtures. Draft the “why companies would use this” story. **Done:** $14,700/$15,000 comparison understood independently of Person 2's solver.
- [ ] P6.3 (H1–4) Write black-box acceptance checks against the contract: health, reset, baseline, disruption and result status. **Done:** they run against stubs, then live services without rewriting contracts.
- [ ] P6.4 (H4–8) Execute numerical, privacy, identity/replay and model-failure checks below. Plant private sentinel strings and inspect coordinator/provider captures. **Done:** failures have named owners and are fixed before freeze.
- [ ] P6.5 (H6–10) Collect costs, field/value/byte counts, round count, solver time and end-to-end/model latency. Run 20 solver-only repetitions for descriptive p50/p95 and a few live AI runs. **Done:** report labels sample sizes and separates solver speed from AI/network time.
- [ ] P6.6 (H8–11) Write README, architecture diagram, limitations, sources and the three-minute pitch. Explain why the LLM coordinates and why the solver determines quantities. **Done:** claims match implemented behavior and actual measurements.
- [ ] P6.7 (H11–14) Rehearse baseline, disruption, disclosure inspection and denied-access sequence; record a backup of the real LinuxONE/LLM run. **Done:** two clean rehearsals and usable video.
- [ ] P6.8 (H14–15) Submit repository/build/version, required links, video and team credits with Person 1. **Done:** organizers' submission receipt/checklist completed before the deadline.

First handoff: acceptance checklist by H1; independent expected results by H2. Dependencies: published contract, then working endpoints. Early QA work runs in parallel with every implementation role.

## Integration schedule and decision gates

| Elapsed time | All-team milestone | Evidence / response if missed |
|---|---|---|
| H0–0.5 | Scope, schemas, file ownership and fixtures frozen; six branches/tasks started | Everyone has sample JSON and an independent deliverable |
| H0.5–1 | Actual LinuxONE health + solver + real LLM API smoke tests | Access problems go to organizers/team lead now; keep other work on fixtures |
| H1–3 | Backend stubs, numeric functions, mock-tool AI loop and mocked UI work independently | Freeze selected stack; do not migrate frameworks later |
| H3–5 | First real browser → LinuxONE → agent/tools → solver → result path | Drop nonessential charts and extra polish if late |
| H5–8 | Second round, benchmark report, real data boundaries, transcript and both presets integrated | Keep only baseline + primary-loss flow; do not remove required AI/LinuxONE |
| H8–10.5 | Integrated acceptance and failure cases pass | Stop feature work; assign each failure to its owner |
| H10.5–12 | Numerical/security fixes, documentation and final VM release | Freeze code at H12 except demo-blocking bugs |
| H12–14 | Two rehearsals, backup video, submission assembly | Freeze claims and pitch to match the actual build |
| H14–15 | Final deploy verification and submission | Preserve a final hour for upload/authentication surprises |

Person 1 is release owner; Person 3 is contract owner; Person 6 is acceptance/submission owner. Each person edits their own modules. Agree interfaces through examples; integrate small working increments at H3, H5, H8 and H10.5. Use one repository and six short branches if Git is already working. Avoid changing deployment tooling solely for this project.

Critical path: LinuxONE/LLM access → frozen contract → optimizer + services + agent → live UI → acceptance → rehearsal/submission. Frontend, QA, infrastructure, solver, services and AI all have work from minute one.

## Acceptance checklist: definition of done

- [ ] Application endpoints, participant services, optimization and agent client actually run on LinuxONE; architecture/VM evidence and build ID recorded.
- [ ] A real successful LLM action invokes an approved tool and appears in the UI; inference hosting and fallback status are stated accurately.
- [ ] Baseline oracle $14,700 and repaired candidate $15,000 reproduce with the same fixture/cost definition, no batch constraints, and accepted participant feedback.
- [ ] Primary-loss oracle $44,900 and repaired candidate $45,000 reproduce; measured values are shown, not hardcoded as live solver results.
- [ ] Solver status is optimal before reporting an “optimality gap.” If not optimal, label the comparison appropriately. Zero oracle cost gives gap N/A or an explicitly defined special case.
- [ ] Candidate feasibility and local acceptance are checked after every solve. Rounds stop at two; conflicting floors or later rejection produce UNRESOLVED, not a falsely finalized plan.
- [ ] No-scarcity case, unavailable alternate supplier and invalid/negative inputs return correct feasible or failure states; no division-by-zero metric.
- [ ] A and B private sentinel values are absent from coordinator storage and outbound model requests. Synthetic benchmark exports are clearly identified as an extra disclosure channel.
- [ ] Actual B/coordinator OS identity cannot read A's private DB; credential-based API denial works; changing a requester query string cannot spoof identity.
- [ ] Modified HMAC, wrong identity, stale run/proposal and replay are rejected. Changed audit data fails verification under the recorded digest/key assumptions.
- [ ] Invalid LLM action, provider timeout and solver error have visible, bounded behavior. No fake live AI label on replay/fallback output.
- [ ] Reset, restart and second consecutive demo run work. UI assets load locally; presentation SSH tunnel is tested.
- [ ] README, sources, backup recording and submission items match the exact final release.

Minimum quality bar: correct and honest end-to-end behavior, visible LinuxONE execution, one substantive real LLM tool flow, two rehearsed scenarios, and a disclosure transcript. A particular cost gap or speed target is not a delivery condition. Suggested usability budget: solver under 2 seconds for this tiny instance and total run under 30 seconds; measure and adjust the presentation if the provider is slower.

## Three-minute demo

1. **0:00–0:25 — Problem:** A chip shortage affects competing factories; neither wants to reveal customer penalties and internal inventory.
2. **0:25–1:10 — Baseline:** Show LinuxONE deployment, run the real LLM coordination, inspect initial proposal, B's restricted feedback and repaired allocation.
3. **1:10–1:40 — Evidence:** Show true simulated cost versus oracle and the exact approved messages. Explain that the 2.04% gap belongs to this fixture and that quantity feedback itself reveals some information.
4. **1:40–2:15 — Disruption:** Reduce primary capacity through the preset; show a new live solve and the changed allocations/cost.
5. **2:15–2:40 — Trust boundary:** Show credential-based denied request plus actual OS-level denial evidence. Describe trusted VM administrator and benchmark viewer assumptions.
6. **2:40–3:00 — Result:** State measured round/latency results, the real LLM's coordination role, and the next product validation step: test with a supply-chain operator and realistic cost/service policies.

Prepare one slide or README section for likely questions: strategic bidding is not solved; minimization is not formal secrecy; LLM output cannot bypass solver/validation; LinuxONE is the execution host, not a claim of measured performance advantage; the oracle is a separate research benchmark.

## Reproducing this review

Run `python tradeoff_validation.py` from this folder. It needs only Python's standard library and writes `tradeoff_validation_results.json`. It exhaustively enumerates the tiny integer-chip example, checks expected costs and demonstrates incompatible floors. It does not validate a real VM installation, external provider access, event eligibility or production security. Those are assigned first-hour/integration gates above.
