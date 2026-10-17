# Data provenance and local AI

User-supplied source: [DataCo Smart Supply Chain for Big Data Analysis on Kaggle](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis).

The public download contains `DataCoSupplyChainDataset.csv`; the file used in this build has SHA-256 `fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6`. Raw CSV and ZIP stay under ignored `.tradeoff/datasets/`, are not in source bundles and are not sent to an LLM. Preserve the dataset publisher's attribution and applicable dataset terms when redistributing derived work. This application's MIT code license does not relicense the dataset.

## Actual model

Binary logistic regression, implemented using standard Python to avoid native dependency problems on s390x. The model artifact is JSON coefficients plus provenance/metrics, not executable pickle.

Features: scheduled shipping days (scaled), shipping mode (one-hot), market (one-hot) and intercept. No actual shipping outcome, late-risk label, delivery status or customer PII appears in the feature vector. Target: `actual shipping days > scheduled shipping days`. Canceled/suspected-fraud orders and invalid rows are excluded. Rows are line items rather than necessarily distinct orders.

The timestamp cutoff is `2017-04-22T03:43:00`. Rows before the cutoff form the training pool (138,211); a reproducible sample of60,000 is fitted for6 epochs. Rows on/after the cutoff form the chronological holdout (34,554). Shared timestamps are kept together, avoiding splitting same-timestamp line items between train/test.7,754 rows were skipped by the documented rules. Random seed74129.

| Historical holdout metric | Value |
|---|---:|
| Accuracy | 0.696012 |
| Majority-label accuracy | 0.572871 |
| ROC AUC | 0.742317 |
| Brier score | 0.189643 |
| Log loss | 0.540986 |

These are measured results on the downloaded release, not prospective manufacturing validation or evidence of causal business savings. They are recorded in `models/delivery-risk.json` and can be reproduced with the training command. The model is not tuned on the test partition. Market categories are fixed from the documented schema; unknown categories are rejected.

At runtime the local learned model predicts risks for public illustrative shipping choices and prioritizes participant validation order. It cannot change solver quantities, invent floors or bypass local acceptance. The basic UI also exposes a standalone risk prediction form and historical evaluation metrics. No generative LLM is implied by local ML mode. An optional external tool-calling adapter is separate and requires actual credentials/model access.

## What DataCo does not establish

Retail order lines do not establish private chip inventory, a shared interchangeable component, supplier available capacity, severe-shortage cost curves, medical priority, or emergency procurement costs. Those optimizer inputs remain explicitly synthetic. The streaming importer creates aggregate category/lead-time summaries for context and does not silently convert unrelated categories into competing manufacturers.
