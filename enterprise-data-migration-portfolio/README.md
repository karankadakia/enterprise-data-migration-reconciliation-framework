# Enterprise Data Migration & Reconciliation Framework

A self-contained, runnable demonstration of how a senior data engineer approaches a
**legacy-to-cloud data migration**: profile the source, design a source-to-target
mapping, land raw data, apply transformation rules, validate business rules, track
defects, and produce **reconciliation and cutover sign-off** artifacts.

> **100% synthetic, non-confidential data. Standard-library Python + SQLite only —
> no `pip install` required. Runs end to end with a single command.**

This project mirrors the kind of work done on enterprise migration platforms
(e.g. ChainSys-style data migration / data quality tooling, Informatica, Talend,
or hand-rolled ETL) but distilled into transparent, readable Python so a reviewer
can see *exactly* what each step does.

---

## Why this exists (recruiter-facing overview)

Real migrations rarely fail on the "move the bytes" part — they fail on **data
quality, reconciliation, and cutover governance**. This repo demonstrates the
disciplines that actually de-risk a cutover:

| Capability | Where it lives |
|---|---|
| **Data profiling** (discovery) | `src/02_profile_source.py` → `outputs/profiling_report.csv` |
| **Source-to-target mapping** | `docs/templates/source_to_target_mapping.csv` |
| **Transformation rules** | `src/04_transform_load.py` + `src/common.py` |
| **Validation / business rules** | `src/05_validate.py` + `docs/templates/validation_rules.csv` |
| **Exception handling** | `exceptions` table → `outputs/exception_report.csv` |
| **Defect tracking** | `docs/templates/defect_tracker.csv` |
| **Reconciliation reporting** | `src/06_reconcile.py` → `outputs/reconciliation_report.md` |
| **Cutover sign-off** | `docs/templates/cutover_signoff.md` |
| **Reusable templates** | everything under `docs/templates/` |

---

## Architecture

A layered **ELT** design (land raw, transform in place) — the same pattern used by
modern cloud data platforms (Snowflake, BigQuery, Databricks):

```
                 ┌──────────────────────────────────────────────────────────┐
                 │                    SQLite: outputs/migration.db            │
  data/source/   │                                                            │
  ┌───────────┐  │  RAW / STAGING            CONFORMED / TARGET               │
  │customers  │  │  ┌─────────────┐          ┌──────────────┐                 │
  │orders     │──┼─▶│ stg_customers│──┐      │ dim_customers │                 │
  │products   │  │  │ stg_products │  │ ───▶ │ dim_products  │                 │
  │ (CSV)     │  │  │ stg_orders   │  │      │ fact_orders   │                 │
  └───────────┘  │  └─────────────┘  │      └──────────────┘                 │
        │         │        ▲          │             │                         │
        │ profile │        │ load     │ transform   │ validate                │
        ▼         │        │          ▼             ▼                         │
  profiling_      │   CONTROL / AUDIT:  exceptions   run_log                  │
  report.csv      │                         │                                │
                 └──────────────────────────┼────────────────────────────────┘
                                            ▼
                          exception_report.csv + reconciliation_report.md
```

**Stages (run in order by `run_pipeline.py`):**

1. **Init** – build staging, target, and control schemas (`sql/01`, `sql/02`).
2. **Profile** – measure completeness / distinct values / lengths per source column.
3. **Load staging** – land CSVs verbatim as `TEXT` with lineage columns
   (`_source_file`, `_source_row`, `_loaded_at`).
4. **Transform** – cleanse, standardize code-sets, parse dates/numbers, deduplicate
   on the natural key, derive financial measures, reject unkeyable rows.
5. **Validate** – apply business rules; write ERROR/WARN rows to `exceptions`.
6. **Reconcile** – emit the defect log + a reconciliation report with a GO / NO-GO
   cutover verdict.

---

## How to run (end to end)

Requires **Python 3.8+** only. No dependencies.

```bash
cd enterprise-data-migration-portfolio
python3 run_pipeline.py
```

That single command rebuilds the database and regenerates every report. You can
also run any stage on its own, e.g. `python3 src/02_profile_source.py`.

Inspect the resulting database directly:

```bash
sqlite3 outputs/migration.db "SELECT severity, COUNT(*) FROM exceptions GROUP BY severity;"
```

---

## Expected outputs

After a run, `outputs/` contains:

| File | Description |
|---|---|
| `migration.db` | SQLite DB with staging, target, and control tables |
| `profiling_report.csv` | Column-level data profile of the source |
| `exception_report.csv` | Full defect log (every rule violation) |
| `reconciliation_report.md` | Counts + financial recon + GO/NO-GO verdict |

### Sample console output

```
==========================================================================
STEP 4  Transform & load conformed target tables
==========================================================================
  customers  -> dim_customers  15 rows (0 skipped)
  products   -> dim_products   15 rows (0 skipped)
  orders     -> fact_orders    23 rows (1 skipped)

==========================================================================
STEP 5  Validate business rules
==========================================================================
  customers  7 exceptions
  products   4 exceptions
  orders     8 exceptions
  total exceptions logged this run: 20

==========================================================================
STEP 6  Reconciliation & exception reporting
==========================================================================
  verdict: NO-GO  (ERROR=14, WARN=6)
```

### Sample reconciliation report (`reconciliation_report.md`)

```markdown
## 1. Row-count reconciliation (staging vs target)

| Entity | Staging rows | Target rows | Delta | Note |
|---|---|---|---|---|
| customers | 16 | 15 | 1 | dedup + rejected records |
| products | 16 | 15 | 1 | dedup + rejected records |
| orders | 25 | 23 | 2 | dedup + rejected records |

## 2. Financial reconciliation
- Net revenue of COMPLETED orders (target): 89,500,902.47
- Orphan orders (customer missing in target): 1

## 4. Verdict
14 blocking ERROR(s) must be remediated before cutover.
```

### Sample exception report (`exception_report.csv`)

```csv
entity,natural_key,source_row,rule_id,severity,field,bad_value,message,detected_at
customers,C006,,C-CREDIT-02,ERROR,credit_limit,-5000.0,Negative credit limit,...
customers,C015,,C-DATE-02,ERROR,signup_date,2050-04-01,Signup date is in the future,...
customers,C009,,C-EMAIL-01,ERROR,email,noah.wilson@example,Missing or malformed email,...
orders,O1007,,O-FK-01,ERROR,customer_id,C999,Customer not found in dim_customers (orphan),...
orders,O1011,,O-DISC-01,ERROR,discount_pct,200.0,Discount percent out of 0-100 range,...
```

> The verdict is intentionally **NO-GO**: the synthetic source data is seeded with
> realistic defects (missing emails, negative credit limits, orphan foreign keys,
> out-of-range discounts, duplicates, future dates, bad currencies, fat-finger
> quantities). The framework's job is to *find and report* them — which it does.

---

## The seeded data quality issues (and which rule catches each)

| Issue in source | Example | Caught by |
|---|---|---|
| Missing primary key | order with blank `product_id` | `O-PK-01` (rejected) |
| Duplicate records | `C008`, `P010`, `O1015` appear twice | dedupe keep-last |
| Malformed / missing email | `carlos@@example.com`, blank, `...@example` | `C-EMAIL-01` |
| Negative credit limit | `C006 = -5000` | `C-CREDIT-02` |
| Non-numeric number | `C011 credit_limit = abc` | `C-CREDIT-01` |
| Future date | `C015 signup_date = 2050-04-01` | `C-DATE-02` |
| Mixed date formats | `2022/01/28` vs `2022-01-28` | parsed to ISO |
| Inconsistent code-sets | `usa`/`US`/`United States`, `consumer` | standardized |
| Orphan foreign keys | order → `C999` / `P999` | `O-FK-01`, `O-FK-02` |
| Out-of-range discount | `200%` | `O-DISC-01` |
| Invalid quantity | `-1`, `1000000` | `O-QTY-01`, `O-QTY-02` |
| Bad currency | `XYZ` | `P-CCY-01` |
| Negative price | `P011 = -399` | `P-PRICE-02` |
| Unknown status | `UNKNOWN` | `O-STATUS-01` |

---

## How this maps to enterprise / ChainSys-style migration work

| Enterprise migration concept | This repo's equivalent |
|---|---|
| Source system extract / landing zone | `data/source/*.csv` → `stg_*` tables |
| Data quality assessment / profiling | `02_profile_source.py` |
| Mapping specification (STM) | `source_to_target_mapping.csv` |
| Transformation / harmonization rules | `04_transform_load.py`, `common.py` |
| Data validation / business rule engine | `05_validate.py`, `validation_rules.csv` |
| Error / exception management | `exceptions` table, `exception_report.csv` |
| Defect triage & remediation tracking | `defect_tracker.csv` |
| Reconciliation (counts + control totals) | `06_reconcile.py`, `reconciliation_report.md` |
| Mock / cutover rehearsal & sign-off | `cutover_signoff.md` |
| Audit / lineage | `_source_file`/`_source_row`/`_loaded_at`, `run_log` |

The pattern — **profile → map → land → transform → validate → reconcile → sign off**
— is platform-agnostic. Swap SQLite for Snowflake and CSVs for an Oracle/SAP
extract and the methodology is unchanged.

---

## What to discuss in an interview

- **Why ELT (land raw, then transform)?** Auditability and replay: you can always
  re-derive the target from immutable raw, and prove what arrived from the source.
- **Why not enforce the FK as a hard constraint?** Because you must be able to
  *land* orphan records to detect and remediate them. A failed `INSERT` hides the
  problem; an exception row surfaces it. (See the note in `sql/02_target_schema.sql`.)
- **ERROR vs WARN severity:** ERROR blocks cutover (GO/NO-GO gate); WARN is tracked
  but non-blocking. This is how you keep a migration moving without ignoring risk.
- **Reconciliation = trust:** row-count deltas explained by dedupe/rejects, plus a
  financial control total, are what convince the business to sign the cutover.
- **Idempotency:** `run_pipeline.py` rebuilds from scratch every run — safe to
  re-run, which matters for mock-cutover rehearsals.
- **Deduplication policy:** "keep last" is a deliberate, documented choice; in a
  real engagement you'd confirm the survivorship rule with the data owner.

---

## How to extend toward a modern cloud platform

This repo is deliberately a *clean seam* for modernization:

- **Snowflake / BigQuery:** Replace `src/common.connect()` with a warehouse
  connector. The `stg_*` → `dim_*`/`fact_*` layering maps directly to
  `RAW` → `STAGING` → `MART` schemas. Load CSVs via `COPY INTO` / external stages.
- **dbt:** Move the SQL in `sql/` and the transforms in `04_transform_load.py` into
  dbt models (`staging/`, `marts/`). The validation rules become **dbt tests**
  (`not_null`, `accepted_values`, `relationships`, plus singular tests for the
  custom rules). `source_to_target_mapping.csv` becomes your `schema.yml`.
- **Airflow / Dagster:** Each numbered script is already a discrete task. Wrap
  steps 1–6 as a DAG with dependencies `init >> profile >> load >> transform >>
  validate >> reconcile`, and gate the final cutover task on `ERROR == 0`.
- **Great Expectations / Soda:** The hand-rolled checks in `05_validate.py` map
  onto declarative expectation suites; `validation_rules.csv` is the rule catalog.
- **Data contracts:** Promote `source_to_target_mapping.csv` + `validation_rules.csv`
  into a versioned contract enforced in CI.
- **Orchestration of waves:** Add a `wave` / `batch_id` column to drive phased
  cutovers and per-wave reconciliation.

---

## Repository layout

```
enterprise-data-migration-portfolio/
├── README.md
├── LICENSE
├── .gitignore
├── run_pipeline.py                 # end-to-end orchestrator
├── data/source/                    # synthetic source CSVs (with seeded defects)
│   ├── customers.csv
│   ├── orders.csv
│   └── products.csv
├── sql/
│   ├── 01_staging_schema.sql
│   ├── 02_target_schema.sql
│   └── 03_reconciliation.sql
├── src/
│   ├── common.py                   # config + reusable cleanse/validate helpers
│   ├── 01_init_db.py
│   ├── 02_profile_source.py
│   ├── 03_load_staging.py
│   ├── 04_transform_load.py
│   ├── 05_validate.py
│   └── 06_reconcile.py
├── docs/templates/                 # reusable migration artifacts
│   ├── source_to_target_mapping.csv
│   ├── validation_rules.csv
│   ├── defect_tracker.csv
│   └── cutover_signoff.md
└── outputs/                        # generated DB + reports (git-ignored)
```

---

## License

Karan Kadakia — see [LICENSE](LICENSE). All data in this repository is synthetic and
contains no confidential or proprietary information.
