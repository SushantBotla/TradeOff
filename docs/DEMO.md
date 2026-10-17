# Three-minute demo and submission draft

**Pitch:** TradeOff helps manufacturers coordinate shortages through restricted messages. A learned shipping-risk model prioritizes validation, an optimizer proposes allocations, and each participant can reject a proposal without exposing its full inventory or cost curve.

0:00–0:25: Show live s390x runtime/VM evidence and identify the two factories and supplier. Explain that LinuxONE runs the services, local model inference, solver and evaluator.

0:25–1:10: Run baseline. Show actual local model predictions and validation order. B rejects the first proposal and sends only a minimum quantity. The second proposal is accepted.

1:10–1:40: Inspect approved messages and benchmark. Final true simulated cost15000, oracle14700, gap2.04%. Explain these are measured synthetic costs and that quantity feedback itself reveals information.

1:40–2:10: Run primary capacity loss. Show changed live allocations and costs45000/44900. The system does not promise a fixed gap.

2:10–2:35: Use the learned model's risk form. Show chronological historical holdout accuracy69.60% versus57.29% baseline and AUC0.7423. Be explicit: this is retail outcome prediction used illustratively, not a calibrated chip-procurement model.

2:35–3:00: Trigger the real cross-identity403 test and show OS-isolation verification. Explain bounded rounds, no severe-tier acceptance, trusted VM admin and the separate privileged benchmark. Mention combined disruption as an honest unresolved case if asked.

## Submission description

TradeOff is a LinuxONE-hosted prototype for restricted-information supply shortage coordination. Independent participant services retain private synthetic inventory/cost data and exchange authenticated bids and acceptance feedback. A bounded controller uses a learned DataCo shipping-delay predictor to prioritize validation requests, while an exact integer optimizer enforces supply and submitted quantity floors. A separate privileged evaluator reports true simulated cost against a full-information reference. The prototype includes a basic replaceable UI, source packaging, systemd deployment, filesystem isolation checks, cryptographic audit verification and automated numerical/API/model/security tests.

Local ML is the demonstrated AI feature; optional external generative tool-calling adapters are provided. No financial settlement, truthful-bidding mechanism, formal secrecy, hardware acceleration claim or prospective manufacturing-risk validation is asserted.

## Questions to prepare

- Why an optimizer? It enforces quantities/constraints and provides a reproducible objective; model guesses cannot replace it.
- Why AI? A model learned from historical delivery data estimates risk and prioritizes validation. Its quality is tested on a later time period; its domain-transfer limitations are visible.
- Why LinuxONE? This build actually executes the services, inference and optimization on it. It does not claim measured hardware superiority over other hosts.
- What stays private? Raw participant data through enforced service permissions/APIs; feedback and the privileged research dashboard still disclose information.
- Can participants manipulate bids? Yes, strategic truthfulness is outside this prototype's cooperative setting.
- Why not always optimal? Coarse requests/priority signals hide cost curves and stock decisions. Zero or large gaps are possible and displayed honestly.

Before submitting: fill in the actual event form, team credits and required repository/video links. The app cannot invent a submission destination. Capture a backup recording of the real VM run using the event team's normal screen recorder.

