# Migration Cutover Sign-off Checklist

**Project:** Enterprise Data Migration & Reconciliation
**Wave / Cutover window:** ________________________
**Cutover lead:** ________________________  **Date:** ____________

> A cutover is only authorized when every gate below is **GO** and all
> ERROR-severity defects in `defect_tracker.csv` are Closed.

## 1. Pre-cutover gates

| # | Gate | Owner | Status (GO / NO-GO) | Evidence |
|---|---|---|---|---|
| 1 | Source extract complete & frozen | Source System Team | | extract manifest |
| 2 | Data profiling reviewed | Data Quality Lead | | `profiling_report.csv` |
| 3 | Source-to-target mapping signed off | Solution Architect | | `source_to_target_mapping.csv` |
| 4 | Transformation rules unit-tested | ETL Lead | | test log |
| 5 | All ERROR defects remediated | Migration Lead | | `defect_tracker.csv` |
| 6 | Row-count reconciliation balanced | Reconciliation Lead | | `reconciliation_report.md` |
| 7 | Financial control totals match | Finance | | `reconciliation_report.md` |
| 8 | Rollback plan validated | Infra/DBA | | rollback runbook |

## 2. Reconciliation summary (paste from reconciliation_report.md)

- Row-count delta by entity: ____________________________
- Completed-order net revenue (target): ____________________________
- Orphan orders: ____________________________
- Open ERROR defects: ____________________________

## 3. Decision

- [ ] **GO** — proceed with cutover
- [ ] **NO-GO** — defer; reasons below

Reasons / conditions: ___________________________________________

## 4. Approvals

| Role | Name | Signature | Date |
|---|---|---|---|
| Business Owner | | | |
| Solution Architect | | | |
| Migration Lead | | | |
| Data Quality Lead | | | |
| IT Operations | | | |
