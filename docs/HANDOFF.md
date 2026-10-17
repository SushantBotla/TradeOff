# Product and team handoff

## Access

- Share the public homepage: https://sushantbotla.github.io/TradeOff/
- Open the interactive showcase: https://sushantbotla.github.io/TradeOff/workspace.html
- Read the usage guide: https://sushantbotla.github.io/TradeOff/guide.html
- Source: https://github.com/SushantBotla/TradeOff

The showcase replays real LinuxONE records and computes new browser predictions. For new allocation jobs, use the protected runtime via an authorized SSH tunnel or run `python -m tradeoff dev` locally. The README documents both. No external LLM API key is needed for the included local ML feature.

## Delivered acceptance criteria

- Exact allocation optimization and independent full-information oracle.
- Bounded negotiation, private participant validation and no false agreement.
- Five scenarios including an unresolved case and a zero-cost oracle.
- Real trained local model, chronological evaluation and reproducible provenance.
- Five service identities on LinuxONE, credential checks and OS permission checks.
- Audit verification, transcript disclosure accounting and benchmark separation.
- Homepage, responsive cockpit, usage guide, export and public replay mode.
- Public repository, Python version matrix CI and automatic Pages deployment.
- Architecture, math, data, API, operations, six-person plan and design handoff.

## Six parallel owners for the remaining event time

The original15-hour build breakdown is in `TradeOff-15-hour-plan.md`. With the product implemented, these roles can work simultaneously without duplicating ownership:

| Person / role | Owns | Next concrete task | Done when |
| --- | --- | --- | --- |
| 1 — Product / demo lead | Story, judging mapping, submission | Rehearse baseline → primary loss → unresolved; prepare the event submission with actual required fields | A timed3-minute walkthrough and accurate LinuxONE/ML claims |
| 2 — Optimization lead | `optimization.py`, `evaluation.py`, MATH | Review objective/constraints and explain the $15,000 vs $14,700 difference | Can reproduce baseline and disruption oracle comparisons |
| 3 — Participant / security lead | `participants.py`, `security.py`, `audit.py` | Rehearse actual denied request and OS reads; retain an external audit head | Shows403 and PermissionError without exposing credentials |
| 4 — ML / data lead | `ml.py`, model artifact, DATA | Explain features, target, chronological split and domain limits; demonstrate new inference | Can distinguish trained ML from controller rules and retail from manufacturing evidence |
| 5 — Platform / integration lead | LinuxONE, systemd, SSH, CI | Confirm five services, tunnel, token access and fallback presentation recording | Live run works after coordinator restart; public showcase remains available |
| 6 — Experience / presentation lead | `tradeoff/web`, Figma board, screenshots | Refine branding if needed; review narrow layout, keyboard flow and instructions | Judges reach and understand workspace without assistance |

Use separate files or small branches for changes; agree on API schema changes before integration. Public assets must never include keys, login tokens, private databases or raw customer rows. Submit through the hackathon portal only after the team supplies its actual destination and required submission details.
