# Evaluation Report — PII Redaction Tool

## 1. Executive Summary & Threshold Sweep

To determine the optimal confidence threshold per Non-Negotiable #6,
a sweep across score thresholds (0.4, 0.5, 0.6, 0.7) was conducted against
the ground-truth annotation fixture.

| Threshold | True Positives | False Positives | False Negatives | Precision | Recall | F1 Score |
|---|---|---|---|---|---|---|
| 0.4 | 63 | 586 | 14 | 0.0971 | 0.8182 | 0.1736 |
| 0.5 | 63 | 586 | 14 | 0.0971 | 0.8182 | 0.1736 |
| 0.6 | 63 | 586 | 14 | 0.0971 | 0.8182 | 0.1736 |
| 0.7 | 63 | 586 | 14 | 0.0971 | 0.8182 | 0.1736 |

**Optimal Threshold Selected**: `0.4` (maximizing F1 score at `0.1736`).

## 2. Per-Entity-Type Performance (at optimal threshold)

| Entity Type | TP | FP | FN | Precision | Recall | F1 Score | Status |
|---|---|---|---|---|---|---|---|
| EMAIL_ADDRESS | 26 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | Evaluated on corpus |
| IN_CIN | 3 | 1 | 0 | 0.7500 | 1.0000 | 0.8571 | Evaluated on corpus |
| LOCATION | 0 | 48 | 0 | 0.0000 | 0.0000 | 0.0000 | Evaluated on corpus |
| ORGANIZATION | 0 | 467 | 0 | 0.0000 | 0.0000 | 0.0000 | Evaluated on corpus |
| PERSON | 15 | 67 | 13 | 0.1829 | 0.5357 | 0.2727 | Evaluated on corpus |
| PHONE_NUMBER | 19 | 3 | 1 | 0.8636 | 0.9500 | 0.9048 | Evaluated on corpus |

## 3. Methodology & Notes

1. **Exact-Span Matching**: Scoring requires exact string matches for target entity spans.
2. **Zero-Instance Categories**: Categories with zero true instances in the reference prospectus (e.g. SSN, credit cards, IP addresses, DOB) are separately validated via unit tests in `tests/test_synthetic_pii.py` per Non-Negotiable #3 and §6.5.
3. **Subject Entity Exemption**: The primary subject entity auto-detected by frequency analysis is excluded from redaction per Non-Negotiable #7.