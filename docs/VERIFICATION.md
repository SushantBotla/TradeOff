# Verification evidence

Verified October17,2026 against the actual user-provided LinuxONE VM and the local development checkout.

## Actual deployed flow

Browser on127.0.0.1:8080 → SSH tunnel → LinuxONE coordinator8000 → authenticated participant services → local learned-model inference and OS CBC → separate privileged evaluator → browser-rendered result.

- Architecture: `s390x`; Ubuntu24.04; Python3.12.3.
- Five dedicated systemd identities and services; loopback bindings.
- PuLP3.3.1 and native CBC2.10.11 installed and used (not a mocked solve).
- DataCo learned JSON model loaded; two actual local predictions recorded per run; no external LLM call or fallback represented as AI.
- Baseline: externalA560/B300/alternate60; true cost15000; oracle14700; gap2.040816%.
- Primary loss: externalA480/B300/alternate300; true cost45000; oracle44900; gap0.222717%.
- Actual OS reads of A's private DB by coordinator and B service users returned PermissionError. The intentionally privileged evaluator successfully read it.
- Actual B-identity authenticated request to A returned403 and was audited.
- The finished mission cockpit was exercised through the real SSH tunnel: existing session authentication, a fresh Run coordination, cost/benchmark rendering, model inference and denied-access result.

## Automated checks

**28 tests passed on Windows Python3.14 and on the actual s390x VM running Python3.12.** GitHub Actions also passed the suite on Python3.10,3.12 and3.14. The optional LLM protocol tests use a mock provider; the live deployment uses real local learned-model inference.

The stdlib unittest suite covers numerical results and randomized brute-force comparison, oracle behavior, real local HTTP API boundaries, signature mutation, identity/method/path/run/proposal/replay checks, model artifact/inputs, raw private canary leakage, both optional LLM protocols against a labeled mock provider, malformed/forbidden model actions, reset/audit preservation, local ML inference and forwarded-port origins.

The independent `tradeoff_validation.py` checker reproduces the pasted model's mathematical audit. JavaScript syntax and Linux shell syntax are checked separately. Source packaging excludes raw CSVs, private keys, API credentials, runtime DBs and login tokens.

External generative inference is optional and not demonstrated without provider access. No prospective manufacturing-risk validation, truthful-bidding proof, formal privacy guarantee, immutability or CPACF acceleration measurement is claimed.

## Public product release

- Public source: https://github.com/SushantBotla/TradeOff
- Public showcase: https://sushantbotla.github.io/TradeOff/
- GitHub Pages workflow successfully built and deployed with HTTPS.
- Browser verified hosted homepage/workspace, baseline and disruption records, no-scarcity zero-cost oracle, no-alternate record, fresh browser learned-model inference (45.12% for Standard Class/4 days/USCA and99.76% for First Class/1 day/USCA), recorded audit evidence, JSON export action, reset and history.
- Combined disruption was checked as unresolved, with no accepted true cost. The last feasible rejected proposal is explicitly labeled.
- Both a wide1265px viewport and a narrow699px viewport were visually inspected. Narrow layout stacks the homepage and moves cockpit navigation to a horizontal row.
- Public records contain only synthetic business messages, aggregated evaluation results, learned model coefficients and non-secret verification evidence. The live API remains protected behind loopback SSH access.
- Source paths and public site configuration were checked to keep static public files separate from authenticated runtime data. The suite verifies the route allowlist and access denial for private paths.
- Figma tools remained unavailable after retry. A native vector SVG design board and token documentation were supplied as an importable handoff; the remote Figma file was not edited.
