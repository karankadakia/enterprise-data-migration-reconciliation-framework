# Reconciliation Report

- **Run ID:** RUN-20260620-102230
- **Generated:** 2026-06-20 10:22:30 UTC
- **Cutover readiness:** **NO-GO** (14 ERROR, 6 WARN)

## 1. Row-count reconciliation (staging vs target)

| Entity | Staging rows | Target rows | Delta | Note |
|---|---|---|---|---|
| customers | 16 | 15 | 1 | dedup + rejected records |
| products | 16 | 15 | 1 | dedup + rejected records |
| orders | 25 | 23 | 2 | dedup + rejected records |

## 2. Financial reconciliation

- Net revenue of COMPLETED orders (target): **89,500,902.47**
- Orphan orders (customer missing in target): **1**

## 3. Exception summary by rule

| Rule | Severity | Entity | Count |
|---|---|---|---|
| C-EMAIL-01 | ERROR | customers | 3 |
| P-PRICE-01 | WARN | products | 2 |
| C-CREDIT-01 | WARN | customers | 1 |
| C-CREDIT-02 | ERROR | customers | 1 |
| C-DATE-01 | WARN | customers | 1 |
| C-DATE-02 | ERROR | customers | 1 |
| O-DATE-01 | WARN | orders | 1 |
| O-DISC-01 | ERROR | orders | 1 |
| O-FK-01 | ERROR | orders | 1 |
| O-FK-02 | ERROR | orders | 1 |
| O-PK-01 | ERROR | orders | 1 |
| O-PRICE-01 | ERROR | orders | 1 |
| O-QTY-01 | ERROR | orders | 1 |
| O-QTY-02 | WARN | orders | 1 |
| O-STATUS-01 | ERROR | orders | 1 |
| P-CCY-01 | ERROR | products | 1 |
| P-PRICE-02 | ERROR | products | 1 |

## 4. Verdict

14 blocking ERROR(s) must be remediated before cutover. See `exception_report.csv` for the defect log and route each to the owning team.
