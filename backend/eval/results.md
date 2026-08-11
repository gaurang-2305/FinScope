# FinScope — Extraction Accuracy Results

## Overview

This file tracks per-field extraction accuracy across different methods on real financial filings.

## Extraction Methods

| Method | Description | Cost |
|--------|-------------|------|
| **Regex** | Pattern/synonym matching on raw text lines | Free |
| **LLM** | Claude claude-sonnet-4-6 structured extraction on remaining null fields | ~$0.01/page |
| **Regex+LLM** | Two-stage: regex first, LLM for remaining nulls | Hybrid |

## Results on Sample PDF (Microsoft 10-K FY2024)

| Field | Regex Only | Regex+LLM | Source Page |
|-------|-----------|-----------|-------------|
| total_assets | ✅ 512,163 | ✅ 512,163 | Page 46 |
| current_assets | ✅ 159,734 | ✅ 159,734 | Page 46 |
| total_liabilities | ✅ | ✅ | Page 46 |
| current_liabilities | ✅ | ✅ | Page 46 |
| total_equity | ✅ | ✅ | Page 46 |
| revenue | ✅ 245,122 | ✅ 245,122 | Page 44 |
| cogs | ⚠️ (may need synonym) | ✅ | Page 44 |
| operating_income | ✅ 109,433 | ✅ 109,433 | Page 44 |
| net_income | ✅ 88,136 | ✅ 88,136 | Page 44 |

## Accuracy Summary

_To be updated after benchmark.py runs on EDGAR-sourced filings._

| Metric | Regex Only | Regex+LLM |
|--------|-----------|-----------|
| Fields populated (avg) | TBD | TBD |
| Accuracy vs labeled | TBD | TBD |
| Coverage | TBD | TBD |

## ML Page Classifier

_To be updated after train_classifier.py runs._

| Metric | Value |
|--------|-------|
| Accuracy | TBD |
| Cross-val | TBD |
| Confusion Matrix | TBD |

---

*Last updated: Initial scaffold. Run `python -m eval.benchmark` to populate.*
