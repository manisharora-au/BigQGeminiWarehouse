# Hackathon Implementation Plan
**BigQuery & Gemini Data Warehouse Challenge**
*intelia Hackathon — v2.0*

---

This plan follows the sequence in which the platform must be built. Each phase is a hard dependency on the one before it — nothing in Phase 3 can be tested without Phase 2 complete, and so on. The order is not arbitrary.

---

## Phase 1: Project Setup & Infrastructure (Day 1)

**Goal:** Provision every GCP resource from scratch using Terraform so the entire platform can be torn down and rebuilt in a single run.

### 1.1 GCP Project Bootstrapping

- GCP project `manish_sandpit` is already created and accessible — no bootstrapping required
- Enable required APIs via Terraform `modules/project`:
  - Cloud Storage, BigQuery, Cloud Functions, Cloud Run, Eventarc, Pub/Sub
  - Dataform, Vertex AI, Dataplex, Cloud Monitoring, Cloud Logging, Secret Manager
- Budget and billing alerts are already configured on `manish_sandpit` — no action required

### 1.2 Secret Manager

Secret Manager is not yet configured on `manish_sandpit` — this must be completed before Terraform runs, as it is a prerequisite for all subsequent steps.

- Enable the Secret Manager API on `manish_sandpit`
- Create the following secrets manually via the GCP console or `gcloud`:
  - Terraform state bucket access credentials
  - Vertex AI API connection credentials
  - Any additional API tokens required by ADK agents
- Terraform will reference these via `data "google_secret_manager_secret_version"` blocks — nothing is hardcoded in `.tfvars` or source code
- Confirm all secrets are accessible before running `terraform apply`

### 1.3 Terraform Modules

Provision all resources via seven composable modules. Run `terraform apply` once to create everything:

| Module | What it creates |
|---|---|
| `modules/project` | API enablement and project labels only — budget and billing alerts already configured on `manish_sandpit` |
| `modules/storage` | Bucket `gs://intelia-hackathon-dev-raw-data/` already created — Terraform will manage the six prefixes (`inbox/`, `raw/`, `validated/`, `quarantine/`, `archive/`, `temp/`), lifecycle rules (Nearline 30 days, Coldline 90 days), and 365-day retention lock on `raw/` |
| `modules/bigquery` | Four datasets: `validated_external`, `curated`, `marts`, `governance` — plus table schemas for `validation_log`, `quality_failures`, `ingestion_log`, `ai_insights` |
| `modules/iam` | Service accounts already created on `manish_sandpit` — Terraform will manage IAM role bindings and Workload Identity configuration only |
| `modules/networking` | VPC Service Controls perimeter restricting BigQuery, GCS, and Vertex AI to within the project boundary; Private Google Access for Cloud Run and Dataform |
| `modules/dataplex` | `intelia-retail-lake` with three zones: `raw-zone`, `curated-zone`, `consumption-zone`; GCS and BigQuery assets registered per zone |
| `modules/monitoring` | Log-based metric watching `cloud-run-validator` for ERROR severity; alert policy firing on first error; notification channel to team email/Slack — budget alert policies already configured, no action required |

### 1.4 Cloud Build CI/CD Pipeline

Configure Cloud Build to chain the full deployment in one trigger:

```
Stage 1: terraform init → plan → apply
Stage 2: Deploy Dataform models
Stage 3: Copy source files to inbox/ (initial load)
Stage 4: Full pipeline run + assertions
```

**Validation:** `terraform plan` must show zero changes after `apply`. All eight service accounts visible in IAM console. All six GCS prefixes exist. All four BigQuery datasets exist.

---

## Phase 2: Raw Ingestion Layer (Day 1–2)

**Goal:** Build the event-driven file ingestion chain from `inbox/` through to validated BigQuery external tables.

### 2.1 Cloud Functions — File Router

Deploy a Cloud Function triggered by a GCS Object Finalised event on the `inbox/` prefix:

- Reads the file name and matches against known patterns:
  - `customers_*.csv` → `raw/customers/`
  - `products_*.csv` → `raw/products/`
  - `orders_*.csv` → `raw/orders/`
  - `order_items_*.csv` → `raw/order_items/`
- Unrecognised files → `quarantine/inbox_unrecognised/` + Cloud Logging ERROR entry
- Moves matched files to the correct `raw/{entity}/` subfolder (flat — no partition structure)
- Deletes the original from `inbox/` once the move completes
- Writing to `raw/` fires a second GCS Object Finalised event picked up by Eventarc

**Validation:** Drop a test file into `inbox/`. Confirm it appears in `raw/{entity}/` and is deleted from `inbox/`.

### 2.2 Eventarc + Cloud Run Validator

Configure Eventarc to watch the `raw/` prefix for Object Finalised events and trigger the Cloud Run Validator.

Deploy the Cloud Run Validator (`sa-cloudrun-validator@`):

- Reads the entity type from the GCS object path (`raw/orders/` → orders)
- Reads only the file header row — no full file scan
- Runs eight checks: column names, column count, column order, non-empty, UTF-8 encoding, comma delimiter, date format sample, file size guard
- Schema contracts defined in `EXPECTED_SCHEMAS` dictionary, version-controlled in Git

**On PASS:**
- Determines load type (full or delta) and today's date from file name
- Copies file to `validated/{entity}/load_type={full|delta}/date={YYYY-MM-DD}/`
- Writes PASS record to `governance.validation_log`
- Publishes JSON message to Pub/Sub topic `pipeline-coordinator-trigger`

**On FAIL:**
- Copies file to `quarantine/{entity}/`
- Writes FAIL record to `governance.validation_log` with failed check name and expected vs actual values
- Writes ERROR log entry to Cloud Logging → triggers Cloud Monitoring alert → notification sent to team

**Validation:** Drop a correctly structured file. Confirm it appears in `validated/` with the correct partition path. Drop a malformed file. Confirm it appears in `quarantine/` and an alert is received.

### 2.3 BigQuery External Tables

Create four external tables in the `validated_external` dataset, each pointing to the entity's `validated/` subfolder with hive partitioning:

```sql
CREATE OR REPLACE EXTERNAL TABLE `validated_external.ext_customers`
OPTIONS (
  format = 'CSV',
  uris = ['gs://intelia-hackathon-dev-raw-data/validated/customers/*.csv'],
  skip_leading_rows = 1,
  field_delimiter = ',',
  hive_partitioning_options = STRUCT(
    mode = 'AUTO',
    source_uri_prefix = 'gs://intelia-hackathon-dev-raw-data/validated/customers/'
  )
);
```

The two virtual partition columns created automatically — `load_type` and `date` — allow Dataform curated models to filter to exactly the files relevant to the current run:

```sql
WHERE load_type = 'delta' AND date = '2025-03-15'
```

Repeat for `ext_products`, `ext_orders`, `ext_order_items`.

**Validation:** Query each external table in BigQuery. Confirm rows are returned and the `load_type` and `date` virtual columns are visible and filterable.

---

## Phase 3: Curated Layer — Dataform (Day 2–3)

**Goal:** Build the single-step curated transformation models and data quality assertions.

### 3.1 Dataform Repository Initialisation

- Initialise a Dataform repository in the GCP project
- Configure `dataform.json` with `defaultDatabase`, `defaultSchema: curated`, `assertionSchema: governance`
- Connect to BigQuery using `sa-dataform@` service account
- Connect the repository to Git for version control

### 3.2 Source Declarations

In `definitions/sources/sources.js`, declare the four external tables as Dataform sources:

```javascript
declare({ schema: 'validated_external', name: 'ext_customers' });
declare({ schema: 'validated_external', name: 'ext_products' });
declare({ schema: 'validated_external', name: 'ext_orders' });
declare({ schema: 'validated_external', name: 'ext_order_items' });
```

### 3.3 Curated Models

Create one `.sqlx` file per entity in `definitions/curated/`. Each model reads directly from the external table source — no staging layer — and does the following in a single pass:

- Casts every column to the correct data type (`PARSE_DATE`, `SAFE_CAST`, `CAST`)
- Renames columns to `snake_case` standard
- Filters fully null rows
- Attaches `_loaded_at TIMESTAMP` and `_source_file STRING` metadata columns
- Appends to the curated table — no updates, no deletes

For delta runs, the model filters the source using the partition columns:

```sql
config {
  type: "incremental",
  schema: "curated",
  description: "Append-only curated customers table"
}

SELECT
  SAFE_CAST(customer_id AS STRING)    AS customer_id,
  SAFE_CAST(first_name AS STRING)     AS first_name,
  SAFE_CAST(last_name AS STRING)      AS last_name,
  SAFE_CAST(email AS STRING)          AS email,
  PARSE_DATE('%Y-%m-%d', signup_date) AS signup_date,
  SAFE_CAST(region AS STRING)         AS region,
  SAFE_CAST(loyalty_tier AS STRING)   AS loyalty_tier,
  CURRENT_TIMESTAMP()                 AS _loaded_at,
  _FILE_NAME                          AS _source_file
FROM ${ref('ext_customers')}
${ when(incremental(), `WHERE load_type = 'delta' AND date = '${date}'`) }
```

Four curated models: `curated_customers`, `curated_products`, `curated_orders`, `curated_order_items`.

### 3.4 Dataform Assertions

Create ten assertion files in `definitions/assertions/`. Each assertion is a SQL query expected to return zero rows:

| Assertion file | What it checks |
|---|---|
| `assert_no_null_customer_ids.sqlx` | `customer_id IS NOT NULL` in `curated_customers` |
| `assert_no_null_order_ids.sqlx` | `order_id IS NOT NULL` in `curated_orders` |
| `assert_no_null_order_item_ids.sqlx` | `order_item_id IS NOT NULL` in `curated_order_items` |
| `assert_order_amounts_positive.sqlx` | `total_amount > 0` for completed orders |
| `assert_order_item_quantities_positive.sqlx` | `quantity > 0` in `curated_order_items` |
| `assert_referential_integrity_orders.sqlx` | Every `customer_id` in orders exists in `curated_customers` |
| `assert_referential_integrity_order_items.sqlx` | Every `order_id` in order_items exists in `curated_orders` |
| `assert_referential_integrity_products.sqlx` | Every `product_id` in order_items exists in `curated_products` |
| `assert_product_price_non_negative.sqlx` | `unit_price >= 0` in `curated_products` |
| `assert_no_duplicate_order_items.sqlx` | No duplicate `order_item_id` in `curated_order_items` |

Failed assertions write to `governance.quality_failures`.

### 3.5 Curated Maintenance Model

Create a scheduled Dataform model that culls delta records older than 90 days from all four curated tables. Full load records are never culled.

**Validation:** Run Dataform full refresh. Confirm all four curated tables are populated. Confirm all ten assertions pass. Inspect `governance.quality_failures` — should be empty.

---

## Phase 4: Pipeline Coordinator Agent — Google ADK (Day 3)

**Goal:** Replace static orchestration scripts with an ADK agent that reasons over pipeline state.

### 4.1 Pipeline Coordinator Agent

Build and deploy the Pipeline Coordinator Agent using Google ADK. Deploy to Cloud Run (`sa-cloudrun-orchestrator@`). Subscribe to the `pipeline-coordinator-trigger` Pub/Sub topic.

**On receiving a PASS message from the Validator, the agent:**

1. Reads the `entity_type` and `validated_file_path` from the Pub/Sub message
2. Queries `governance.ingestion_log` to understand current pipeline state
3. Determines whether this is a delta run (entity-scoped) or full refresh
4. Calls the Dataform Workflow API to trigger the correct execution scope
5. Monitors execution and reads `governance.quality_failures` on completion
6. Decides the response to any assertion failure:
   - Small row count on referential integrity → retry once
   - Large row count on null check → quarantine source file, write escalation record, alert
   - Unknown failure type → write escalation record, alert

**Tools the agent uses:**
- BigQuery read tool (`governance.ingestion_log`, `governance.quality_failures`)
- Dataform Workflow API trigger tool
- GCS move tool (for quarantine operations)
- Pub/Sub publish tool (for escalation alerts)
- Cloud Logging write tool (for audit trail)

**Validation:** Drop a delta file into `inbox/`. Confirm the full chain fires: File Router → Validator → Pub/Sub → Agent → Dataform → curated table updated → assertions pass.

---

## Phase 5: Consumption Layer — Star Schema & Marts (Day 3–4)

**Goal:** Build the dimensional model and persona-specific mart tables from the curated entity tables.

### 5.1 Dimension Tables (Dataform — `definitions/consumption/dimensions/`)

**`dim_customer`** — built from `curated_customers`:
- Resolve current state per customer using `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY _loaded_at DESC) = 1`
- Derive `days_since_signup`, `customer_age_band`
- Implement SCD Type 2: on `loyalty_tier` or `region` change, close previous record (`valid_to`, `is_current = FALSE`), insert new record with new surrogate key
- Generate surrogate key: `FARM_FINGERPRINT(customer_id)`

**`dim_product`** — built from `curated_products`:
- Resolve current state per product
- Derive `is_low_stock` flag, stock level band
- Implement SCD Type 2 on `category` and `unit_price`

**`dim_date`** — static date spine:
- Generate one row per date covering full order date range
- Columns: `date_id`, `calendar_date`, `day_of_week`, `week_number`, `month`, `quarter`, `year`, `is_weekend`

### 5.2 Fact Table (Dataform — `definitions/consumption/facts/`)

**`fact_orders`** — one row per order item line:
- Join `curated_order_items` to `curated_orders` (order-level context)
- Join to `dim_customer` on surrogate key current at order date
- Join to `dim_product` on surrogate key current at order date
- Join to `dim_date` on `order_date`
- Derive `line_revenue` (`quantity × unit_price`), `order_value_band`

### 5.3 CCO Mart Tables (Dataform — `definitions/consumption/marts/cco/`)

**`mart_revenue`** — pre-aggregated revenue by date, region, product category:
- `order_date`, `region`, `product_category`, `total_revenue`, `order_count`, `avg_order_value`, `revenue_wow_pct`

**`mart_customer_retention`** — cohort and retention analysis:
- `customer_id`, `cohort_month`, `months_since_first_order`, `is_active_30d`, `is_active_90d`, `lifetime_value`
- `churn_risk_score` column — populated by BigQuery ML in Phase 6

**`mart_customer_segments`** — RFM scoring and AI narratives:
- `customer_id`, `rfm_recency_score`, `rfm_frequency_score`, `rfm_monetary_score`, `rfm_segment`
- `ai_generated_summary` column — populated by BigQuery ML in Phase 6

### 5.4 CTO Mart Tables (Dataform — `definitions/consumption/marts/cto/`)

**`mart_system_adoption`** — pipeline run history per execution:
- `run_date`, `pipeline_name`, `rows_processed`, `duration_seconds`, `bytes_billed`, `status`, `assertion_failures`

**`mart_pipeline_performance`** — slot efficiency, cost per run, delta latency tracking against the $200 budget.

**Validation:** Run Dataform full refresh including consumption models. Query each dimension and fact table. Confirm surrogate keys are populated. Confirm SCD Type 2 history rows exist in `dim_customer`. Confirm all five mart tables are populated.

---

## Phase 6: Generative AI Integration (Day 4–5)

**Goal:** Embed AI as load-bearing pipeline components — not optional extras.

### 6.1 BigQuery ML — Churn Risk Model

Create a remote Gemini model connection in BigQuery pointing to Vertex AI:

```sql
CREATE OR REPLACE MODEL `curated.gemini_pro`
  REMOTE WITH CONNECTION `us.vertex-ai-connection`
  OPTIONS (endpoint = 'gemini-1.5-pro');
```

Train the churn logistic regression model on RFM features from `mart_customer_retention`:

```sql
CREATE OR REPLACE MODEL `marts.churn_model`
OPTIONS (
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['churned']
) AS
SELECT
  rfm_recency_score,
  rfm_frequency_score,
  rfm_monetary_score,
  is_active_90d AS churned
FROM `marts.mart_customer_segments`;
```

Score every customer and write `churn_risk_score` to `mart_customer_retention` as part of the Dataform mart build.

### 6.2 BigQuery ML — Customer Narrative Generation

Run `ML.GENERATE_TEXT` as part of the `mart_customer_segments` Dataform model build to populate `ai_generated_summary`:

```sql
SELECT
  customer_id,
  ML.GENERATE_TEXT(
    MODEL `curated.gemini_pro`,
    CONCAT(
      'You are a retail analyst. In 2 sentences, summarise this customer: ',
      'Segment: ', rfm_segment, ', ',
      'LTV: $', CAST(lifetime_value AS STRING), ', ',
      'Loyalty tier: ', loyalty_tier
    ),
    STRUCT(0.2 AS temperature, 100 AS max_output_tokens)
  ).ml_generate_text_llm_result AS ai_generated_summary
FROM mart_customer_segments_base
```

### 6.3 Google ADK — Insight Generation Agent

Build and deploy the nightly Insight Generation Agent using Google ADK. Triggered by Cloud Scheduler at a time before business hours.

The agent:
1. Queries mart tables to identify the three to five metrics that changed most significantly since the previous run
2. Formulates targeted investigative SQL queries to understand why
3. Writes a plain-English narrative to `governance.ai_insights`
4. Both CCO and CTO Looker Studio dashboards surface this as "Insight of the Day"

### 6.4 Google ADK — Conversational Analytics Agent

Build and deploy the Conversational Analytics Agent using Google ADK and Gemini 1.5 Pro. Deploy to Cloud Run (`sa-vertexai@`).

The agent:
- Accepts natural language questions from the CCO and CTO
- Reasons over mart schemas to identify the correct table(s)
- Generates and executes BigQuery SQL
- Returns a plain-English answer with a supporting data table and a Looker Studio deep-link
- Reformulates and retries if the first query returns no useful result

Also configure the BigQuery Data Agent in the BigQuery console to provide a zero-friction entry point for both personas without requiring a separate interface.

**Validation:** Ask the agent "Which customers are at highest churn risk this month?" Confirm it returns a populated result table with `churn_risk_score` values. Confirm `ai_generated_summary` is populated in `mart_customer_segments`. Confirm `governance.ai_insights` is written to nightly.

---

## Phase 7: Looker Studio Dashboards (Day 5)

**Goal:** Deliver clear, decision-ready visualisations for the CCO and CTO.

### 7.1 CCO Dashboard — "Customer & Revenue Intelligence"

Connect to `marts` dataset. Build the following panels:

| Panel | Source table | Chart type |
|---|---|---|
| Revenue trend (daily / weekly / monthly) | `mart_revenue` | Line chart with date filter |
| Revenue by region | `mart_revenue` | Bar chart with region breakdown |
| Customer retention cohort heatmap | `mart_customer_retention` | Heatmap by cohort month × months since first order |
| RFM segment distribution | `mart_customer_segments` | Pie chart + trend |
| Churn risk scorecard | `mart_customer_retention` | Scorecard: count of customers with `churn_risk_score > 0.7` |
| AI customer summary panel | `mart_customer_segments` | Table: `customer_id`, `rfm_segment`, `ai_generated_summary` |
| Insight of the Day | `governance.ai_insights` | Text panel |

### 7.2 CTO Dashboard — "Platform Health & Adoption"

Connect to `marts` and `governance` datasets. Build the following panels:

| Panel | Source table | Chart type |
|---|---|---|
| Pipeline run history | `mart_system_adoption` | Bar chart: SUCCESS / FAILED / PARTIAL by date |
| Cost vs $200 budget | `mart_pipeline_performance` | Gauge |
| Data freshness per entity | `mart_system_adoption` | Scorecard: latest `run_date` per entity |
| Row volume trends | `mart_system_adoption` | Line chart: `rows_processed` per entity over time |
| Validation log — recent failures | `governance.validation_log` | Table: FAIL records with `failed_check`, `expected_value`, `actual_value` |
| Assertion failure log | `governance.quality_failures` | Table: recent failures with `assertion_name`, `failed_row_count` |
| Dataplex quality scores | Dataplex scan results | Scorecard per dataset |
| Insight of the Day | `governance.ai_insights` | Text panel |

**Validation:** Drop a delta file into `inbox/`. Confirm the CCO dashboard reflects updated revenue and customer data within five minutes. Confirm the CTO dashboard shows the new pipeline run record.

---

## Phase 8: Governance & Security Hardening (Day 6)

**Goal:** Ensure the platform meets enterprise-grade governance and security standards — a scored judging criterion.

### 8.1 Dataplex Configuration

- Verify `intelia-retail-lake` is active with three zones registered
- Confirm all BigQuery tables in `curated` and `marts` are auto-catalogued
- Attach business glossary terms to key columns: `customer_id`, `churn_risk_score`, `total_revenue`
- Configure daily data quality scans on `curated.*` and `marts.*`
- Verify lineage is captured from Dataform job history through to mart tables

### 8.2 PII Policy Tags

- Apply `policy_tag:pii` to `email`, `first_name`, `last_name` in `curated_customers`
- Confirm `sa-looker@` and `sa-vertexai@` cannot query PII columns — access denied
- Confirm `sa-dataform@` can query PII columns during transformation

### 8.3 IAM Hardening Checklist

- [ ] No `roles/editor` or `roles/owner` granted to any runtime service account
- [ ] No service account keys generated — Workload Identity in use for Cloud Run and Cloud Build
- [ ] `allUsers` and `allAuthenticatedUsers` bindings explicitly denied at org policy
- [ ] VPC Service Controls perimeter active — confirm BigQuery API inaccessible from outside the project
- [ ] `prevent_destroy = true` on `gs://intelia-hackathon-dev-raw-data/` (already exists — ensure Terraform imports it before applying) and curated BigQuery dataset

### 8.4 Audit Logging

- Confirm Data Access audit logs are enabled for BigQuery and GCS
- Confirm log sink is exporting to BigQuery for review
- Spot-check: query `cloudaudit_googleapis_com_data_access` table and confirm recent read/write events are captured

---

## Phase 9: End-to-End Testing & Reproducibility (Day 6–7)

**Goal:** Prove the platform is reproducible and the full pipeline works end to end under hackathon conditions.

### 9.1 Full Reproducibility Test

Run the Cloud Build deployment pipeline against a clean GCP project:

```
Stage 1: terraform apply          → all resources provisioned from scratch
Stage 2: Dataform schema push     → all models deployed
Stage 3: Seed inbox/ with CSVs    → File Router fires, files reach validated/
Stage 4: Full pipeline run        → curated tables populated, marts built, AI columns written
```

Target: platform fully operational in under 15 minutes. Dashboards accessible. Agents responding.

### 9.2 Delta Pipeline Test

Simulate a mid-hackathon delta drop:

1. Drop `orders_delta_20250315.csv` into `inbox/`
2. Confirm: File Router → `raw/orders/` → Validator PASS → `validated/orders/load_type=delta/date=2025-03-15/`
3. Confirm: Pub/Sub message fired → Pipeline Coordinator Agent triggered → Dataform incremental run for orders scope only
4. Confirm: `curated_orders` has new rows → `fact_orders` updated → `mart_revenue` updated
5. Confirm: CCO dashboard reflects new data
6. Target: end-to-end under 5 minutes

### 9.3 Failure Path Test

Simulate a validation failure:

1. Drop a malformed `customers_bad.csv` (wrong column names) into `inbox/`
2. Confirm: File Router routes to `raw/customers/` → Validator FAIL → file in `quarantine/customers/`
3. Confirm: FAIL record in `governance.validation_log` with correct `failed_check` and `expected_value` vs `actual_value`
4. Confirm: Cloud Monitoring alert fires → notification received
5. Confirm: Dataform was NOT triggered — `curated_customers` unchanged

---

## Phase 10: Presentation Preparation (Day 7)

**Goal:** Present like a real client board — scored at 10% of total marks.

### 10.1 Architecture Diagram

Finalise the architecture diagram showing the full event chain:

```
inbox/ → File Router → raw/ → Validator → validated/ → External Tables
    → Dataform (curated) → Star Schema → Marts → Looker Studio
    → ADK Agents (Pipeline Coordinator, Insight Generation, Conversational)
    → CCO & CTO
```

### 10.2 Presentation Structure (5 minutes)

| Segment | Duration | Content |
|---|---|---|
| The problem | 30s | What intelia asked for and why it matters |
| The architecture | 60s | Three-layer medallion — Raw, Curated, Consumption — one sentence each |
| The demo | 120s | Drop a delta file → show it reach the dashboard; ask the agent a question |
| The AI story | 45s | Three load-bearing AI components — churn scoring, narrative generation, conversational agent |
| The scalability story | 30s | Star schema + Data Vault evolution path — could we take this to a real client? Yes |
| Governance | 15s | Dataplex, PII tags, VPC-SC, audit logging — enterprise-grade out of the box |

### 10.3 Demo Script

Prepare and rehearse the following live demo sequence:

1. Show the empty `inbox/` bucket in Cloud Storage
2. Drop `orders_delta_20250315.csv` into `inbox/`
3. Show the file move chain in real time: `inbox/` → `raw/` → `validated/`
4. Show the Dataform execution log running the orders incremental model
5. Refresh the CCO Looker Studio dashboard — revenue chart updates
6. Open the Conversational Analytics Agent and ask: *"Which regions saw the biggest revenue change this week?"*
7. Show the agent's plain-English response with the supporting data table
8. Open the CTO dashboard — show the new pipeline run record with bytes billed and duration
