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
- Basic UI was exercised through the real SSH tunnel: sign-in, Run coordination, cost/benchmark rendering, model metrics and denied-access result.

## Automated checks

**27 tests passed on Windows Python3.14 and on the actual s390x VM running Python3.12.** The optional LLM protocol tests use a mock provider; the live deployment uses real local learned-model inference.

The stdlib unittest suite covers numerical results and randomized brute-force comparison, oracle behavior, real local HTTP API boundaries, signature mutation, identity/method/path/run/proposal/replay checks, model artifact/inputs, raw private canary leakage, both optional LLM protocols against a labeled mock provider, malformed/forbidden model actions, reset/audit preservation, local ML inference and forwarded-port origins.

The independent `tradeoff_validation.py` checker reproduces the pasted model's mathematical audit. JavaScript syntax and Linux shell syntax are checked separately. Source packaging excludes raw CSVs, private keys, API credentials, runtime DBs and login tokens.

External generative inference is optional and not demonstrated without provider access. No prospective manufacturing-risk validation, truthful-bidding proof, formal privacy guarantee, immutability or CPACF acceleration measurement is claimed.

