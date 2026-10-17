# TradeOff

**Find the balance. Keep your edge.**

[Public showcase](https://sushantbotla.github.io/TradeOff/) · [Workspace](https://sushantbotla.github.io/TradeOff/workspace.html) · [Usage guide](https://sushantbotla.github.io/TradeOff/guide.html) · [Six-person execution plan](TradeOff-15-hour-plan.md)

![Product verification](https://github.com/SushantBotla/TradeOff/actions/workflows/ci.yml/badge.svg)
![Showcase deployment](https://github.com/SushantBotla/TradeOff/actions/workflows/pages.yml/badge.svg)

A runnable LinuxONE hackathon product for restricted-information shortage coordination. Two factories and a supplier expose authenticated, minimal messages. An optimizer proposes allocations, participant services validate privately, and a separate evaluator measures true simulated costs against an oracle. The responsive homepage and mission cockpit expose the negotiation, actual disclosure inventory, benchmark, model inference and verification evidence.

The **public showcase** replays five actual LinuxONE recordings and performs fresh risk inference in your browser using learned coefficients. It requires no login. **New optimization jobs** run in the authenticated Python app, locally or on LinuxONE behind SSH. The UI labels these modes explicitly.

The default AI feature is **real local delivery-delay prediction**: a logistic regression trained on the supplied DataCo dataset, evaluated on a chronological holdout, and used to prioritize participant validation requests. The coordination state machine and allocation solver are deterministic. This is not presented as an LLM. Optional Responses API / OpenAI-compatible tool-calling adapters are included for a generative coordinator.

## Quick start: no package installation required

Requires Python 3.10+; tested on Windows Python 3.14 and LinuxONE Ubuntu Python 3.12.

```powershell
python -m tradeoff dev
```

Open `http://127.0.0.1:8000`, choose **Open workspace**, then paste the token from `.tradeoff/coordinator/dashboard-token.txt`. On a fresh clone, select the included local model before starting:

```powershell
Copy-Item .env.example .env
python -m tradeoff dev
```

The launcher starts five processes: Factory A, Factory B, supplier, coordinator and evaluator. Ctrl+C stops them. Local development uses one OS user and therefore does **not** enforce filesystem isolation. The LinuxONE installer creates separate service users.

## Demonstrate

1. Run **Baseline shortage**. Initial allocation A560/B240 fails B's local service rule. B reveals a minimum quantity of 300. The second solve produces A560/B300 and 60 alternative units; both factories accept.
2. Inspect true cost **$15,000**, oracle **$14,700**, gap **2.040816%**, actual messages and local model predictions.
3. Run **Primary capacity loss**: A480/B300, 300 alternate units, true cost **$45,000**, oracle **$44,900**.
4. **Combined disruption** deliberately ends unresolved after two rounds; never falsely finalizes a rejected proposal.
5. Try **local delivery-risk inference**, inspect the historical holdout metrics, and run the real credential-based access-denial test.
6. Reset the view. The durable audit history is preserved.

`no_scarcity` shows a zero-cost oracle and therefore an N/A relative gap; the absolute regret remains available in the evaluation API. The coarse policy still draws internal stock, so it is not universally optimal. No percentages or allocations are hardcoded as live solver outputs.

## Tests and verification

```powershell
python -m unittest discover -s tests -v
python -m tradeoff smoke
python -m tradeoff smoke --scenario primary_loss
python -m tradeoff doctor
python -m tradeoff benchmark
python -m tradeoff verify-audit --tamper-demo
```

The suite checks exact solving against independent brute force, oracle values, real HTTP service boundaries, validation/finalization guards, local model inference, malformed LLM outputs, both provider protocols using a **mock provider**, HMAC/replay/identity binding, private sentinel leakage, audit mutation and externally anchored truncation detection. Mock protocol tests do not constitute an actual external LLM call.

## LinuxONE installation

The source installer is in `infra/install_linuxone.sh`. It targets Ubuntu `s390x`, creates `/opt/tradeoff`, state under `/var/lib/tradeoff`, five Linux service users and systemd units. It does not modify the existing `/home/linux1/TradeOff` notebook project. Root/VM administrators remain trusted.

From Windows, after verifying the VM host key:

```powershell
.\infra\deploy.ps1 -HostName YOUR_VM -UserName linux1 -KeyPath C:\path\to\private-key
```

Alternatively upload the source ZIP, extract it, then on the VM:

```bash
sudo bash infra/install_linuxone.sh
sudo bash /opt/tradeoff/infra/verify_isolation.sh
cd /opt/tradeoff
sudo -u tradeoff-coordinator ./venv/bin/python -m tradeoff doctor --config /var/lib/tradeoff/coordinator/config.json
sudo -u tradeoff-coordinator ./venv/bin/python -m tradeoff smoke --config /var/lib/tradeoff/coordinator/config.json
sudo -u tradeoff-coordinator ./venv/bin/python -m tradeoff token --config /var/lib/tradeoff/coordinator/config.json
```

Presentation tunnel from your laptop:

```powershell
ssh -i C:\path\to\private-key -L 8000:127.0.0.1:8000 linux1@YOUR_VM
```

If local port 8000 is occupied, use `-L 8080:127.0.0.1:8000`, then open `http://127.0.0.1:8080`. The app permits loopback Host headers and requires a matching browser origin, including the forwarded local port.

Services bind loopback. Do not expose the standard-library HTTP server directly to the public internet. This is a hackathon prototype behind SSH, not a production internet deployment.

## Configuration

Only the coordinator reads `.env` locally or `/etc/tradeoff/llm.env` on LinuxONE. Environment values take precedence. No API keys are needed for local ML.

| Setting | Purpose |
|---|---|
| `TRADEOFF_AI_MODE=local_ml` | Included learned DataCo predictor plus deterministic coordination controller |
| `TRADEOFF_AI_MODE=auto` | Use a configured LLM, otherwise clearly labeled deterministic fallback |
| `TRADEOFF_AI_MODE=required` | Require successful external LLM tool coordination; fail honestly on errors |
| `TRADEOFF_AI_MODE=disabled` | Deterministic controller without AI; does not satisfy an AI demonstration |
| `TRADEOFF_ML_MODEL_PATH` | JSON learned model artifact; default `models/delivery-risk.json` |
| `TRADEOFF_LLM_PROVIDER` | `openai` for Responses API; `openai-compatible` for Chat Completions |
| `TRADEOFF_LLM_BASE_URL`, `...MODEL`, `...API_KEY` | Provider endpoint/model/credential, if using an LLM |
| `TRADEOFF_SOLVER=auto` | OS CBC with PuLP 3.x if available, otherwise exact integer solver |
| `TRADEOFF_SOLVER=exact` / `cbc` | Explicit backend; CBC mode fails if unavailable |

Change LinuxONE configuration using `sudoedit /etc/tradeoff/llm.env`, then `sudo systemctl restart tradeoff@coordinator`. Never paste keys into repository files. Provider model availability and external API access are not assumed or purchased by this project.

The exact solver exploits the two-factory objective's piecewise linear structure and enumerates integer A quantities plus B endpoints/kinks. It is exact for this bounded toy model. The oracle independently enumerates feasible quantity pairs. CBC is an optional general solver adapter, pinned to `PuLP==3.3.1` with the OS `cbc` executable. See docs/MATH.md.

## Data and training

Raw DataCo data is excluded from source bundles and runtime model inputs. Download/train locally:

```powershell
python infra/fetch_dataco.py
python -m tradeoff import-dataco .tradeoff/datasets/DataCoSupplyChainDataset.csv
python -m tradeoff train-risk-model .tradeoff/datasets/DataCoSupplyChainDataset.csv
```

The included artifact records the source SHA-256, timestamp cutoff, features, sampled training size, seed, metrics and limitations. Selected features are shipping mode, scheduled days and market, all available before delivery. Actual shipping days define the training outcome only. Customer rows are not exported. Historical retail performance is not validated chip-manufacturing performance. Synthetic shortage capacities, safety stocks and penalties are explicitly separate. See docs/DATA.md.

## API / replacing the UI

Static files live in `tradeoff/web/`. All API routes except public `/health` require `Authorization: Bearer <dashboard token>`. Browser APIs reject cross-origin requests and unknown JSON fields. Schemas/examples are in docs/API.md.

```text
GET  /health
GET  /api/scenarios
POST /api/runs                         {"scenario_id":"baseline"}
GET  /api/runs
GET  /api/runs/{id}
GET  /api/runs/{id}/events
GET  /api/runs/{id}/evaluation
GET  /api/ml
POST /api/ml/predict                   {"shipping_mode":"First Class","scheduled_days":1,"market":"USCA"}
GET  /api/audit
POST /api/demo/denial-test             {}
POST /api/demo/reset                   {}
```

The evaluator is not a coordinator tool. It independently reads public allocation exchange files, accesses the private synthetic stores through its privileged identity, and writes only benchmark reports to a directory the coordinator can read but cannot write on LinuxONE. The dashboard displays those reports as a privileged research view, clearly separate from model inputs.

## Showcase, design and publishing

The public site is built without third-party JavaScript or fonts. The same HTML/CSS/JS serves both the authenticated runtime and GitHub Pages. `site-config.json` selects recorded showcase mode; the coordinator serves its own live configuration.

```powershell
python infra/build_site.py
python -m http.server 8090 --bind 127.0.0.1 --directory _site
```

Pushes to `main` run the tests and publish `_site` to GitHub Pages. Refresh the approved public synthetic recordings from an authenticated loopback runtime with `python infra/export_demo.py --token-file PATH_TO_LOCAL_TOKEN`. The exporter checks for s390x, allowlists public fields and rejects accidental token inclusion. Raw customer rows, participant databases and credentials are never site assets.

See [design handoff](docs/PRODUCT-DESIGN.md) for colors, typography, layouts and the importable SVG board for Figma. See [release verification](docs/VERIFICATION.md), [deployment](docs/DEPLOYMENT.md), and [math](docs/MATH.md) for evidence and limitations.

## Project map

- `optimization.py`: restricted allocation solver and feasibility checks.
- `participants.py`, `security.py`: private participant logic and authenticated APIs.
- `coordinator.py`, `agent.py`: bounded workflow, local ML integration and optional LLM tools.
- `ml.py`, `models/`: real local model, training, chronological metrics and learned coefficients.
- `evaluation.py`: privileged independent oracle and true-cost worker.
- `audit.py`: SQLite events, run persistence and HMAC/hash chain.
- `infra/`: LinuxONE install, OS-isolation check, Windows launcher and deployment helper.
- `tests/`: numerical, HTTP, model and security acceptance.
- `docs/`: architecture, math, data, API, deployment and pitch.

Package source with `python -m tradeoff package`. The ZIP contains a SHA-256 manifest and excludes runtime databases, raw datasets, `.env`, SSH keys, logs and dashboard credentials.

## Limits

Cooperative participants; no incentive-compatible mechanism or payments. No batch constraints or multi-day scheduling. Restricted disclosure is not formal secrecy; aggregate benchmarks and feedback reveal additional information. Shared-key authentication is not encryption or nonrepudiation. The local audit chain is tamper-evident only under stated key and external-anchor assumptions. No CPACF acceleration or hardware performance advantage is asserted. The application does not automatically submit to a hackathon platform without the actual submission details.

