# Solutions Architecture
**BigQuery & Gemini Data Warehouse Challenge**
*intelia Hackathon — v3.0 DRAFT*

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Data Architecture Philosophy](#2-data-architecture-philosophy)
   - 2.1 The Medallion Architecture
   - 2.2 Why These Layers Are Separate
   - 2.3 Where GCP Services Map to Each Layer
   - 2.4 Agentic Design Principle
   - 2.5 Schema Evolution Protocol
   - 2.6 The Two Pipelines
3. [Architecture Overview](#3-architecture-overview)
4. [Infrastructure & Automation](#4-infrastructure--automation)
5. [Data Ingestion & Raw Layer](#5-data-ingestion--raw-layer)
   - 5.1 Cloud Storage — The Landing Zone
   - 5.2 Cloud Functions — The File Router
   - 5.3 Cloud Run Validator — The Validation Gate
   - 5.4 The Validation Log
   - 5.5 Alerting on Failure
   - 5.6 BigQuery External Tables
6. [Transformation & Curated Layer](#6-transformation--curated-layer)
   - 6.1 What Dataform Is and Why It Is Used
   - 6.2 The Three Transformation Steps
   - 6.3 Dataform Assertions — Data Quality Checks
   - 6.4 The Quality Failures Table and the Validation Log Together
7. [Consumption Layer & Data Marts](#7-consumption-layer--data-marts)
8. [Generative AI Integration](#8-generative-ai-integration)
9. [Data & AI Governance](#9-data--ai-governance)
10. [Scalability & Security](#10-scalability--security)
11. [End-to-End Data Flow & Workflow Orchestration](#11-end-to-end-data-flow--workflow-orchestration)

---

## 1. Executive Summary

This document describes the solutions architecture for the intelia Hackathon: BigQuery & Gemini Data Warehouse Challenge. The goal is to take raw synthetic retail data — Customers, Products, and Orders — and turn it into a working, governed data warehouse on Google Cloud Platform (GCP) that delivers clear, decision-ready insights to two stakeholders: a Chief Customer Officer and a Chief Technology Officer.

The platform is built entirely on native GCP services. It follows a three-layer data architecture — Raw, Curated, and Consumption — where data is progressively cleaned, transformed, and made available for reporting and AI-driven analysis. Infrastructure is fully automated and can be deployed to a brand new GCP project from scratch in a single pipeline run.

Generative AI is used throughout the platform as a working part of the pipeline — not a feature added on top. The detail of how and where is covered in Section 8.

The platform is designed to be scalable, secure, and reproducible. Every layer is governed, access is strictly controlled, and the entire solution can be torn down and rebuilt without data loss.

---

## 2. Data Architecture Philosophy

Before examining any component or diagram, it is essential to understand how data is shaped and what it represents at each stage of the platform. Every design decision in this document follows from this foundation.

### 2.1 The Medallion Architecture

This platform organises data into three progressive layers. Each layer has a distinct shape, a distinct level of trust, and a distinct consumer. Moving data from one layer to the next is a deliberate, governed act — not a copy.

---

#### 2.1.1 Layer 1 — Raw: exact replica of the source

The Raw layer holds source data exactly as it arrived — no transformations, no corrections, no interpretation of any kind. Files land in a flat `inbox/` prefix in Google Cloud Storage (GCS) as CSVs — the source simply drops a file with no folder convention required. A Cloud Function detects the arrival, identifies the entity type and load type from the file name, and moves the file into the correct partitioned subfolder under `raw/`. Eventarc then fires on that structured path and triggers the validation gate, which checks that the file conforms to a known schema contract: correct column names, column count, column order, encoding, delimiter, and date format. A file that fails this check is quarantined and never enters the platform. This gate exists to protect all downstream layers from malformed or unexpected input — a problem that, if undetected, would silently corrupt marts and dashboards.

Files that pass validation are moved to the `validated/` prefix and made available to BigQuery as **external tables**. The external tables point exclusively at the `validated/` prefix — they never read from `raw/`, `inbox/`, or any other area. An external table is a typed SQL lens over a file that stays in GCS — BigQuery can query it without physically copying the data. Only files that have cleared the validation gate are visible to BigQuery and therefore to Dataform. This is the enforcement point: no unvalidated data can enter the transformation layer.

What the data looks like here: four external tables (`ext_customers`, `ext_products`, `ext_orders`, `ext_order_items`) whose columns mirror the CSV headers exactly. If the source sent a null, a duplicate, or a malformed date, it exists here unchanged. The Raw layer is a faithful record of what was received, not what was intended.

---

#### 2.1.2 Layer 2 — Curated: cleaned, conformed, and trustworthy

The Curated layer is not a dimensional model. It is not a star schema. It contains one table per business entity — customers, products, orders, and order_items — each representing a single, trusted, deduplicated version of that entity with a meaningful and consistent schema.

Transformation from Raw to Curated happens in three sequential steps:

*Staging* casts every column to the correct data type, renames columns to a consistent `snake_case` standard, filters fully null rows, and attaches ingestion metadata (`_loaded_at`, `_source_file`). This is structural cleanup — the data is not yet interpreted, just made consistent and typed.

*Intermediate* applies business logic: referential enrichment (joining customer region onto orders, product category onto order lines) and derivation of calculated fields such as `days_since_signup` and `is_repeat_customer`. This is where raw data becomes meaningful.

*Curated* materialises the final conformed entity tables in BigQuery native storage using an **append-only** approach. Every record that arrives — whether from a full load or a delta drop — is written as a new row stamped with `_loaded_at` and `_source_file`. No existing record is ever updated or deleted during the pipeline run. This means the curated tables hold a complete, immutable history of every version of every entity as it arrived over time.

Downstream models in the Consumption layer always derive the current state of an entity at query time using a simple `ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY _loaded_at DESC) = 1` pattern — selecting the most recently arrived record per entity. This keeps the curated layer simple and safe to reprocess: because nothing is mutated, any pipeline run can be replayed from scratch without risk of data corruption.

Older records are culled on a defined schedule — delta records beyond a 90-day retention window are removed by a scheduled Dataform maintenance model. Full load records are retained for the lifetime of the project as the baseline. This balances auditability with cost efficiency.

What the data looks like here: four append-only entity tables — `curated_customers`, `curated_products`, `curated_orders`, and `curated_order_items` — each containing all historical arrivals for that entity, stamped with ingestion metadata. Clean types, consistent naming, no nulls on key fields. This is the single source of truth that all downstream consumption is built from.

---

#### 2.1.3 Layer 3 — Consumption: dimensional model with persona-specific marts

The Consumption layer transforms the append-only curated entity tables into a fully dimensional model — a star schema comprising dimension tables, a central fact table, and persona-specific mart tables built on top. This is where historical accuracy, scalability, and query performance are all achieved together.

**Why a star schema and not a flat mart**

A flat mart works well for a small, fixed set of questions from a known set of personas. But the judging criteria asks whether this platform could be taken to a real client tomorrow. In a real engagement, the first thing that happens is more personas, more questions, more dimensions, and more sources. A flat mart does not scale to that — it requires rebuilding from scratch each time a new analytical requirement appears. A star schema scales naturally: new questions are answered by new queries against existing tables, and new dimensions are added without restructuring what already exists.

A **Data Vault** (Hubs, Satellites, Links) would be the right choice if source systems were numerous, volatile, and poorly integrated — where tracking the provenance of every attribute across multiple feeds is a core requirement. That is not this problem. Three well-understood entities from a single source do not warrant that overhead.

A **star schema** is the correct choice here. It gives every fact record a permanently accurate join to the version of each dimension that was current at the time of the transaction. It is the industry standard for analytical workloads, and it is the most legible structure for a Vertex AI agent generating SQL at runtime.

**The dimensional model**

Four tables form the foundation of the star schema, all built from the curated entity tables:

`dim_customer` is built from `curated_customers` and implements **SCD Type 2** — the correct home for this pattern. When a customer's `loyalty_tier` or `region` changes, the previous dimension record is closed (`valid_to` stamped, `is_current = FALSE`) and a new record is inserted with a new surrogate key. Every order in `fact_orders` joins to the surrogate key that was current at the time of that transaction, not the customer's current state. Without this, a customer who moved from Bronze to Gold loyalty would retroactively appear as Gold on all their historical orders — corrupting every cohort and retention analysis the CCO depends on.

`dim_product` is built from `curated_products` and implements SCD Type 2 on `category` and `unit_price` — preserving the product state at the time each order was placed.

`dim_date` is a static date spine covering the full range of order dates. No SCD is needed — dates do not change.

`fact_orders` is the central fact table, one row per order item line. It is built from `order_items` joined to `orders`, `dim_customer`, `dim_product`, and `dim_date` using surrogate keys — not natural keys — ensuring every historical query resolves to the correct version of each dimension at the time of the transaction.

**Persona-specific marts**

On top of the star schema, persona-specific mart tables pre-aggregate and pre-compute the metrics each persona needs. Three serve the CCO — `mart_revenue`, `mart_customer_retention`, and `mart_customer_segments` — and two serve the CTO — `mart_system_adoption` and `mart_pipeline_performance`. These marts are materialised tables or views over the star schema, not independent flat tables. They inherit the historical accuracy of the dimensional model beneath them.

AI-generated columns — `churn_risk_score` from BigQuery ML and `ai_generated_summary` from `ML.GENERATE_TEXT` — are written into the CCO marts during the pipeline run.

What the data looks like here: a star schema foundation of four tables with SCD Type 2 on key dimensions, and five persona-specific mart tables sitting on top providing fast, pre-aggregated query surfaces for dashboards and AI agents.

**The natural evolution path — Data Vault**

The star schema with SCD Type 2 is the right choice for this platform at this stage. Three well-understood entities from a single source do not warrant additional complexity. However, the document would be incomplete without acknowledging where this architecture sits on the maturity curve and what comes next.

If the platform were to grow — more source systems feeding the same entities, more entities being introduced, stricter auditability requirements, or the need to track the history of individual attributes independently from one another — a Data Vault would become the appropriate foundation for the Consumption layer. In a Data Vault, Hubs store only the business key for each entity and never change. Links record relationships between entities and never change. Satellites hold all the attributes and are append-only by design — every attribute change produces a new row with a timestamp, preserving the full history of every value that entity has ever held, independently per attribute group.

This makes Data Vault significantly more resilient to change than a star schema. Adding a new attribute to track does not require altering an existing table — a new Satellite is added alongside what already exists. No existing queries break. No historical records are affected.

The trade-off is query complexity. Reconstructing the correct state of an entity at a given point in time requires joining Hubs, Links, and multiple Satellites with point-in-time logic. For this reason, Data Vault implementations always build an Information Mart layer on top — which is structurally identical to the star schema marts already present in this architecture — giving analysts and AI agents a clean query surface without needing to understand the vault structure beneath it.

The full maturity path for this platform is therefore:

```
Raw (append-only source files)
    → Curated (append-only cleaned entity tables)
        → Data Vault (Hubs, Links, Satellites)
            → Information Marts (star schema aggregations for CCO and CTO)
```

The current architecture implements the first, second, and fourth layers of this path. The Data Vault layer is the deliberate next step when the platform outgrows three entities from a single source.

---

### 2.2 Why These Layers Are Separate

Separating Raw, Curated, and Consumption into distinct physical layers is not a stylistic choice — it has concrete operational consequences.

If a transformation bug is discovered in a curated model, the Raw layer is untouched and can be fully reprocessed without re-ingesting data from the source. If a mart is rebuilt with a new metric definition, the Curated layer is untouched and does not need to be re-cleansed. Each layer can fail, be corrected, and be rerun independently. This is what makes the platform reproducible and recoverable rather than fragile.

It also means each layer has a clear data contract. The Raw layer's contract is structural: the file must match the expected schema. The Curated layer's contract is semantic: every record must be valid, consistently typed, and enriched with meaningful metadata before it is trusted as a source for downstream consumption. The Consumption layer's contract is dimensional: every fact record must join accurately to the correct version of every dimension at the time of the transaction, and every mart must answer its persona's questions correctly and efficiently. Governance, quality checks, and access controls are applied at the boundary of each layer — not as an afterthought at the end.

---

### 2.3 Where GCP Services Map to Each Layer

The table below gives a single-sentence orientation for every GCP service used in this platform. Each service is explained in full in its respective section.

| Layer | GCP Service | What it does |
|---|---|---|
| **Infrastructure** | Terraform | Provisions every GCP resource from scratch — storage buckets, BigQuery datasets, service accounts, networking controls, governance, and monitoring — as code, so the entire platform can be torn down and rebuilt on a new project without manual steps |
| **Infrastructure** | Cloud Build | Runs the full deployment sequence automatically in order: provision infrastructure, deploy transformation logic, load initial data, run the pipeline |
| **Infrastructure** | Secret Manager | Stores all passwords, API keys, and access credentials in one secure place; the pipeline reads from it but never writes to it |
| **Infrastructure** | Cloud Monitoring | Watches the platform for problems — fires alerts when a file fails validation or the budget approaches its limit, and provides the CTO with a live operational dashboard |
| **Infrastructure** | IAM & Service Accounts | Controls who and what can access each part of the platform; every component runs under its own dedicated account with access limited to only what it needs |
| **Infrastructure** | VPC Service Controls | Creates a security boundary around the platform so that data in BigQuery and Cloud Storage cannot be accessed from outside the project, even if credentials were compromised |
| **Infrastructure** | Private Google Access | Allows internal platform components to communicate with Google services over Google's private network rather than the public internet, reducing exposure |
| **All layers** | Dataplex | Provides a single governance view across all three data layers — cataloguing every table, tracking where data came from, running daily data quality checks, and enforcing access controls on sensitive fields such as customer names and email addresses |
| **Raw** | Google Cloud Storage | Stores all platform data across six prefixes: `inbox/` for files as they arrive from the source, `raw/` for files moved into the correct partitioned folder structure, `validated/`, `quarantine/`, `archive/`, and `temp/` |
| **Raw** | Cloud Functions — File Router | Triggered by a GCS event when any file lands in the `inbox/` prefix — inspects the file name to determine the entity type and whether it is a full load or a delta, derives today's date, and moves the file into the correct `raw/{entity}/` subfolder — partition structure is applied by the Validator when promoting to `validated/` |
| **Raw** | Eventarc | Detects when a file is written to the `raw/` prefix by the File Router and immediately triggers the Cloud Run Validator — no manual intervention or polling required |
| **Raw** | Pub/Sub | Carries the PASS signal from the Cloud Run Validator to the Pipeline Coordinator Agent — the validator publishes a message to a topic, the agent is subscribed and wakes up the moment it arrives |
| **Raw** | Cloud Logging | Receives structured ERROR log entries from the Cloud Run Validator on every validation failure, which Cloud Monitoring watches to fire the alerting pipeline |
| **Raw** | Cloud Run — Validator | Checks every incoming file against a known set of rules before anything else touches it — correct column names, correct structure, correct encoding; files that pass move forward, files that fail are isolated and an alert is raised (see Section 2.5 for how schema changes are handled) |
| **Raw** | BigQuery External Tables | Defined over the `validated/` prefix only — gives Dataform SQL access to files that have cleared the validation gate, while files in `raw/`, `inbox/`, and `quarantine/` remain invisible to BigQuery |
| **Raw** | BigQuery (`governance` dataset) | Records the outcome of every file validation and every data quality check, giving the CTO a full audit trail of what was accepted, what was rejected, and why |
| **Curated** | Google ADK — Pipeline Coordinator Agent | An AI agent that decides what transformation work needs to run after a file is validated — it checks the current state of the pipeline, identifies what is affected, and handles failures by deciding whether to retry, isolate the problem, or raise an alert |
| **Curated** | Dataform | Runs the data transformation steps in the correct order — cleaning, enriching, and conforming the raw data into trusted entity tables that the Consumption layer can rely on |
| **Curated** | BigQuery (`curated` dataset) | Stores cleaned and enriched versions of the four core entities — customers, products, orders, and order_items — retaining the full history of every record that has ever arrived, with records older than 90 days automatically removed |
| **Consumption** | BigQuery (`marts` dataset) | Stores the dimensional model — dimension tables for customers, products, and dates, a central orders fact table, and five summary tables tailored to the specific questions the CCO and CTO need answered |
| **Consumption** | BigQuery ML | Runs two AI tasks during the pipeline: scoring every customer with a churn risk probability, and generating a plain-English summary of each customer's profile using Gemini |
| **Consumption** | BigQuery Data Agent | Allows the CCO and CTO to ask questions about the data in plain English directly from the BigQuery console and receive answers without writing any SQL |
| **Consumption** | Google ADK — Insight Generation Agent | An AI agent that runs every night, identifies what changed most significantly in the data since the previous day, and writes a plain-English summary of those findings for both personas to read the following morning |
| **Consumption** | Google ADK — Conversational Analytics Agent | An AI agent that answers natural language questions from the CCO and CTO — it identifies the right data, runs the query, interprets the result, and responds in plain English with a link to the relevant dashboard |
| **Consumption** | Cloud Scheduler | Triggers the nightly Insight Generation Agent automatically, ensuring fresh insights are ready before business hours each day |
| **Consumption** | Looker Studio | Delivers two visual dashboards — one for the CCO covering revenue, customer retention, and churn risk, and one for the CTO covering pipeline health, data quality, and platform cost |


---

### 2.4 Agentic Design Principle

Not every component in this platform should reason. Deterministic automation — infrastructure provisioning, schema validation, file routing — must behave identically every time it runs. Introducing reasoning into those components would add unpredictability where correctness is the only acceptable outcome. A file either passes schema validation or it does not. Terraform either provisions a resource or it fails. There is no judgement call to be made.

Agentic workflows are appropriate precisely where a fixed decision tree is insufficient — where the right action depends on context, where conditions change between runs, and where a human would otherwise need to intervene to make a call. This platform uses the **Google Agent Development Kit (ADK)** to implement three agents, each replacing a component that would otherwise be a static script.

**Agent 1 — Pipeline Coordinator Agent (Curated layer)**

When a file passes validation and is cleared for processing, something needs to decide what transformation work to run, in what order, and what to do if something goes wrong. In the previous design that was a simple script: file arrives, identify what type it is (customers, products, orders, or order_items), trigger the corresponding transformation steps, done. That works when everything goes right.

It does not work when things go wrong. What if a data quality check fails halfway through? What if two files for the same entity arrive at the same time? What if the transformation steps complete successfully but the resulting data does not look right? A script has no way to reason about any of these situations — it either finishes or it fails, and a human has to step in.

The Pipeline Coordinator Agent replaces that script. It is an AI agent, which means it can read the situation and make a decision rather than follow a fixed path. When a file is cleared for processing, the agent checks what has already run, determines what needs to run next, and kicks off the right transformation steps in the right order. If a data quality check fails, the agent reads the failure, decides whether it is a problem with the data that just arrived or a deeper structural problem, and chooses the appropriate response — run the steps again, put the file aside for review, or raise an alert so a human can investigate.

The diagram in Section 3.3 shows how the agent responds to both a successful file and a failed data quality check — the two paths it can take and the three outcomes it can choose from when something goes wrong.

**Agent 2 — Insight Generation Agent (Consumption layer)**

The previous design used a Cloud Scheduler job to trigger a fixed suite of BQML queries nightly and write templated results to `governance.ai_insights`. Every morning, both personas received the same set of pre-defined metrics formatted as narrative text. The content was predictable and, over time, ignorable.

The Insight Generation Agent replaces this job. Each night it queries the mart tables autonomously, compares current metrics against the prior period, identifies the three to five dimensions that changed most significantly — whether that is a regional revenue shift, a loyalty tier migration, a pipeline latency spike, or an assertion failure pattern — and formulates targeted investigative SQL queries to understand why. It then writes a genuinely dynamic insight narrative to `governance.ai_insights`, contextually relevant to what actually happened that day. The CCO and CTO receive a different, substantive insight each morning rather than a static report with today's date on it.

**Agent 3 — Conversational Analytics Agent (Consumption layer)**

The CCO and CTO can ask questions in natural language. The Conversational Analytics Agent receives the question, reasons over the available mart schemas and the persona's domain context, selects the correct mart table or combination of tables, generates BigQuery SQL, executes it, interprets the result set, and returns a plain-English answer with a supporting data table and a Looker Studio deep-link to the relevant dashboard section. If the first query does not return a meaningful result, the agent reformulates and retries rather than returning an empty response.

This agent is also accessible directly from the BigQuery console via the **BigQuery Data Agent** — giving both personas a zero-friction entry point without needing to navigate to a separate interface.

**Why Google ADK specifically**

Google ADK is chosen over a bespoke Vertex AI Agent Builder configuration for three reasons. First, ADK agents are code-first — the agent logic, tools, and system prompts are defined in Python and version-controlled in Git alongside the Dataform SQLX models, giving the CTO a single auditable codebase. Second, ADK natively supports multi-turn reasoning and tool chaining, which the Pipeline Coordinator and Insight Generation agents both require. Third, ADK agents deploy directly to Cloud Run, keeping the infrastructure footprint consistent with the rest of the platform — no additional managed runtime is introduced.

The boundary between deterministic automation and agentic reasoning is a deliberate architectural line, not a default. Every component on the deterministic side of that line is there because correctness is non-negotiable. Every component on the agentic side is there because static logic is insufficient for the decisions it needs to make.

---

### 2.5 Schema Evolution Protocol

Schema validation is deterministic — a file either matches its contract or it does not. But source schemas are not static. The synthetic retail data used in this hackathon is controlled, but in any production deployment the source system will eventually change: a column gets renamed, a new field is added, a date format shifts. The architecture must have a documented, governed response to each scenario rather than treating schema change as an exceptional failure with no recovery path.

**Why validation must remain deterministic despite schema change**

An agent cannot be responsible for deciding whether a new or unexpected schema is acceptable. That decision has downstream consequences — a new column in the source file may need to propagate through the Dataform `stg_*` model, the `curated_*` table, and potentially a mart column and a dashboard panel. Accepting it silently at the gate would allow the change to enter the pipeline without any of those downstream components being updated. The validator's job is to enforce the current contract, not to interpret intent. Schema evolution is a human-governed change process, not an automated one.

**Schema contracts — where they live**

Schema contracts are defined as a Python dictionary in the Cloud Run Validator service and version-controlled in Git alongside the Dataform SQLX models:

```python
EXPECTED_SCHEMAS = {
    "customers": [
        "customer_id", "first_name", "last_name",
        "email", "signup_date", "region", "loyalty_tier"
    ],
    "products": [
        "product_id", "product_name", "category",
        "unit_price", "stock_quantity", "supplier_id"
    ],
    "orders": [
        "order_id", "customer_id", "order_date",
        "total_amount", "status"
    ],
    "order_items": [
        "order_item_id", "order_id", "product_id",
        "quantity", "unit_price", "line_total"
    ]
}
```

Any change to a schema contract requires a deliberate Git commit, code review, and redeployment via Cloud Build — preventing silent drift and ensuring every contract change is auditable.

**Scenario 1 — Additive change: new column added by the source**

The source file arrives with a column not present in `EXPECTED_SCHEMAS`. The validator rejects the file, moves it to `quarantine/`, writes a FAIL record to `governance.validation_log` with `failed_check = "unexpected_column"` and `actual_value` containing the full received column list, and fires a Cloud Monitoring alert.

Resolution process:
1. The team reviews the quarantine alert and determines whether the new column is intentional and valuable downstream
2. `EXPECTED_SCHEMAS` is updated in Git to include the new column
3. The corresponding `stg_*` Dataform model is updated to cast and rename the new column
4. If the column is needed in a mart or dashboard, the relevant `curated_*` model, mart model, and Looker Studio report are updated in the same Git branch
5. Cloud Build redeploys the validator and Dataform models
6. The quarantined file is manually reprocessed against the updated contract

This is a deliberate, end-to-end change — not a one-line fix. Adding a column to the pipeline has downstream implications that must be resolved before the file is accepted.

**Scenario 2 — Breaking change: column renamed or removed**

A column the contract expects is missing, or has been renamed. The validator rejects the file with `failed_check = "missing_column"` or `"column_name_mismatch"`, and the FAIL record in `governance.validation_log` contains the precise diff: expected column list versus actual column list received.

This is higher urgency than an additive change because a renamed or removed column will break existing Dataform models if it reaches them. The pipeline halt is protective. Resolution follows the same process as Scenario 1, but the Dataform model updates are mandatory rather than optional — the `stg_*` model references the old column name and will fail on execution if the contract is updated without a corresponding model change.

The `governance.validation_log` record provides the team with a precise diff to work from rather than a generic failure message:

| Field | Example value |
|---|---|
| `failed_check` | `column_name_mismatch` |
| `expected_value` | `order_id, customer_id, product_id, order_date, quantity, total_amount, status` |
| `actual_value` | `order_id, customer_id, product_id, order_date, quantity, amount, status` |

In this example the diff is immediately obvious: `total_amount` has been renamed to `amount` in the source.

**Scenario 3 — Gradual drift: encoding, delimiter, or date format shift**

This is the subtler risk. The column structure is unchanged but the file's encoding shifts from UTF-8 to Latin-1, the delimiter changes from comma to pipe, or date values in a sample row no longer parse against the expected format. These changes do not always arrive in a single file — they may appear gradually across delta drops.

The validator catches these at the gate on the first affected file. The specific checks that cover this scenario are: encoding detection (UTF-8 required, BOM and Latin-1 rejected), delimiter assertion (comma required), and date format sampling across the first ten data rows. Any of these failing produces a quarantine event with the specific check named in `failed_check`.

Dataplex daily quality scans on the `curated.*` and `marts.*` datasets provide a second layer of detection for drift that accumulates between runs. Dataform assertions provide a third layer at the row level during every pipeline execution. These are complementary — not substitutes for the gate.

**The reprocessing path for quarantined files**

Every file moved to `quarantine/` is retained there for the full 365-day GCS retention window. Once the schema contract has been updated and redeployed, the quarantined file can be manually copied back to `inbox/` with its original file name, which re-triggers the File Router and the full Eventarc → Validator → Pipeline flow from the beginning. The file is re-validated against the updated contract. If it now passes, it proceeds through the pipeline as normal. The original quarantine record in `governance.validation_log` is preserved — it is never deleted or updated — providing a complete audit trail of the rejection, the resolution, and the reprocessing.


---

### 2.6 The Two Pipelines

The word "pipeline" appears throughout this document. Before going further it is important to be precise about what that word means here, because there are two distinct pipelines in this architecture — they serve different purposes, run at different times, and are made of different services.

---

#### 2.6.1 The Deployment Pipeline

This pipeline runs once — when the platform is first set up, or whenever the codebase is updated. Its job is to take a completely empty GCP project and turn it into a fully operational data warehouse without any manual steps. A team member pushes code to the main Git branch, and Cloud Build takes over from there.

**Services involved:** Git, Cloud Build, Terraform, Secret Manager, Google Cloud Storage, BigQuery, Dataform, Cloud Run, Dataplex, Cloud Monitoring, IAM

**What it does, in order:**

Stage 1 — Terraform reads the infrastructure definitions and provisions every GCP resource that does not already exist: storage buckets, BigQuery datasets, service accounts, access controls, networking boundaries, the Dataplex governance lake, and monitoring dashboards. If the project is brand new, this creates everything from scratch. If the project already exists, Terraform checks what has changed and applies only the differences.

Stage 2 — The Dataform transformation logic is deployed to BigQuery. All of the SQL models that clean, enrich, and organise the data are registered and ready to run. Nothing runs yet — this step just makes the models available.

Stage 3 — The initial source CSV files are copied from the shared hackathon bucket directly into the `inbox/` prefix of the platform bucket. The File Router Cloud Function fires automatically, moves each file into the correct `raw/{entity}/` subfolder, and triggers the validation and pipeline flow from there.

Stage 4 — The full data pipeline (described below) runs end to end for the first time. Every layer is processed in order: the files are validated, the data is cleaned and enriched, the dimensional model is built, and the persona dashboards become live.

The entire sequence — from an empty project to a working data warehouse — completes in under 15 minutes.

---

#### 2.6.2 The Data Pipeline

This pipeline runs continuously during normal operations. It is event-driven, meaning it starts automatically the moment a new data file arrives — there is no schedule and no manual trigger. It has two modes depending on whether a single entity file has arrived (delta mode) or the entire dataset needs to be rebuilt (full refresh mode).

**Services involved:** Google Cloud Storage, Eventarc, Cloud Run (Validator), Google ADK Pipeline Coordinator Agent, Dataform, BigQuery, BigQuery ML, Google ADK Insight Generation Agent, Dataplex, Cloud Monitoring

**Delta mode — what happens when a new file arrives:**

A new data file lands in the `inbox/` prefix of Cloud Storage — the source drops a file with no folder convention required. A Cloud Function detects the arrival, reads the file name to determine the entity type and whether it is a full load or a delta, derives today's date, and moves the file into `raw/{entity}/`. Eventarc detects the arrival and triggers the Cloud Run Validator. If the file passes validation, the Validator promotes it to the correct `validated/{entity}/load_type=delta/date=YYYY-MM-DD/` subfolder — applying the partition structure at that point. The Validator reads the file header, checks the column structure against the known schema, and makes a decision. If the file fails, it is moved to the quarantine area, a record is written to the audit log, and an alert is raised. The pipeline stops. If the file passes, it is moved to the validated area and the Pipeline Coordinator Agent is notified.

The Pipeline Coordinator Agent checks what has already run, determines which transformation steps are affected by this particular file, and instructs Dataform to run those steps — and only those steps — in the correct order. Dataform cleans and enriches the data and writes it to the curated tables. Data quality checks run automatically as part of this process. If all checks pass, BigQuery ML runs to refresh the AI-generated columns in the affected mart tables. Dataplex then runs a quality scan across the updated tables. The end-to-end time from file arrival to updated dashboards is under five minutes.

**Full refresh mode — what happens when everything needs to be rebuilt:**

This mode is triggered either by the deployment pipeline on first load, or manually after a schema change or a significant data correction. Dataform runs all transformation models across all four entities in dependency order — customers, then products, then orders, then order_items — rebuilding every curated table and every mart table from scratch. BigQuery ML re-scores all customers and regenerates all AI summaries. Dataplex scans all updated tables. This mode takes longer but guarantees a completely consistent state across all layers.

---
## 3. Architecture Overview

The following sections (3.1 through 3.4) describe each layer in detail, one at a time. Each section is self-contained and can be read independently. The sequence follows the deployment and data flow order: Infrastructure first, then Raw, then Curated, then Consumption.

A cross-cutting **Governance & Security** plane — comprising Dataplex, VPC Service Controls, Secret Manager, Policy Tags, and audit logging — spans all layers and is described in full in Section 9.

---

### 3.1 Layer 0 — Infrastructure & Automation

*(To be completed)*

---

### 3.2 Layer 1 — Raw Ingestion & Validation Gate

*(To be completed)*

---

### 3.3 Layer 2 — Transformation & Curated Layer

*(To be completed)*

---

### 3.4 Layer 3 — Consumption, GenAI & Personas

*(To be completed)*

---

## 4. Infrastructure & Automation

*(To be completed)*

---

## 5. Data Ingestion & Raw Layer

The Raw layer is the entry point for all data into the platform. Its job is simple: receive source files, check them, and make them available for the transformation layer — without changing a single value. Everything in this section happens before any cleaning, enriching, or modelling takes place.

---

### 5.1 Cloud Storage — The Landing Zone

The platform uses two Cloud Storage buckets with distinct and separate roles.

**Source bucket — `gs://intelia-hackathon-files/`**

This bucket is provided by intelia and contains the synthetic retail dataset used for the hackathon. It is a read-only shared resource. The platform reads the initial full-load CSV files from this bucket during Stage 3 of the deployment pipeline and copies them into the platform's own storage. The platform has no write access to this bucket and does not use it for any other purpose.

**Platform bucket — `gs://intelia-hackathon-dev-raw-data/`**

This is the platform's own bucket, provisioned by Terraform and owned entirely by the platform. All ongoing data operations happen here. It is organised into six areas, each with a specific purpose and specific access controls:

| Path | Purpose |
|---|---|
| `gs://intelia-hackathon-dev-raw-data/inbox/` | Files land here first — the source drops files with no folder convention required |
| `gs://intelia-hackathon-dev-raw-data/raw/customers/` | Customer files staged here by the File Router — flat, no partition structure |
| `gs://intelia-hackathon-dev-raw-data/raw/products/` | Product files staged here by the File Router — flat, no partition structure |
| `gs://intelia-hackathon-dev-raw-data/raw/orders/` | Order files staged here by the File Router — flat, no partition structure |
| `gs://intelia-hackathon-dev-raw-data/raw/order_items/` | Order item files staged here by the File Router — flat, no partition structure |
| `gs://intelia-hackathon-dev-raw-data/validated/customers/load_type=full/` | Validated full customer extracts — partition structure applied by the Validator on promotion |
| `gs://intelia-hackathon-dev-raw-data/validated/customers/load_type=delta/date=YYYY-MM-DD/` | Validated delta customer files — one dated subfolder per successful drop |
| `gs://intelia-hackathon-dev-raw-data/validated/products/load_type=full/` | Validated full product extracts |
| `gs://intelia-hackathon-dev-raw-data/validated/products/load_type=delta/date=YYYY-MM-DD/` | Validated delta product files |
| `gs://intelia-hackathon-dev-raw-data/validated/orders/load_type=full/` | Validated full order extracts |
| `gs://intelia-hackathon-dev-raw-data/validated/orders/load_type=delta/date=YYYY-MM-DD/` | Validated delta order files |
| `gs://intelia-hackathon-dev-raw-data/validated/order_items/load_type=full/` | Validated full order item extracts |
| `gs://intelia-hackathon-dev-raw-data/validated/order_items/load_type=delta/date=YYYY-MM-DD/` | Validated delta order item files |
| `gs://intelia-hackathon-dev-raw-data/validated/` | Files that passed all validation checks — cleared for processing |
| `gs://intelia-hackathon-dev-raw-data/quarantine/` | Files that failed a check — held for manual review |
| `gs://intelia-hackathon-dev-raw-data/archive/` | Validated files moved here after processing completes |
| `gs://intelia-hackathon-dev-raw-data/temp/` | Temporary working space for Cloud Run jobs |

The `inbox/` prefix is where all incoming files land — the source has write access only to this prefix. The File Router Cloud Function is the only process permitted to move files from `inbox/` to `raw/`. The validator is the only process permitted to move files from `raw/` to `validated/` or `quarantine/`. No other service has write access to any of those prefixes. This two-step routing ensures that files are both correctly structured and validated before they can reach the transformation layer.

Files in `raw/` are kept for 365 days and cannot be deleted within that window. After 30 days they move to cheaper nearline storage, and after 90 days to coldline storage — preserving the full history without the cost of keeping everything in hot storage indefinitely.

---

### 5.2 Cloud Functions — The File Router

When a file lands in the `inbox/` prefix, a Cloud Function fires automatically via a GCS trigger. Its job is straightforward: inspect the file name, work out where it belongs in the partitioned folder structure, and move it there. The source system does not need to know anything about the `load_type=` or `date=` folder convention — it just drops a file into `inbox/` and the File Router handles the rest.

**How it determines the entity type**

The File Router reads the file name and matches it against a known set of naming patterns:

| File name pattern | Entity |
|---|---|
| `customers_*.csv` | customers |
| `products_*.csv` | products |
| `orders_*.csv` | orders |
| `order_items_*.csv` | order_items |

If the file name does not match any known pattern, the File Router moves it to `quarantine/inbox_unrecognised/` and writes a log entry. The validation pipeline is not triggered.

**How it determines full load vs delta**

The File Router checks whether the file name contains the word `delta`. A file named `customers_delta_20250315.csv` is treated as a delta. A file named `customers_20250101.csv` with no `delta` marker is treated as a full load.

**What it does with the file**

For both full load and delta files, the File Router moves the file to a flat entity subfolder:
```
raw/{entity}/filename.csv
```

The partition structure — `load_type=` and `date=` — is not applied here. The File Router's only job is to identify the entity and stage the file in the right place for the Validator. The Validator applies the partition structure when it promotes the file to `validated/`. The original file in `inbox/` is deleted once the move completes.

**Why Cloud Functions and not Cloud Run**

The File Router is a simple, single-purpose task: read a file name, derive a path, move a file. It takes milliseconds and requires no persistent container or HTTP endpoint. Cloud Functions is the correct tool for this — it starts instantly in response to a GCS event, runs the move, and terminates. Cloud Run would add unnecessary overhead for a task this lightweight.

---

### 5.3 Cloud Run Validator — The Validation Gate

The Cloud Run Validator is a lightweight Python service deployed to Cloud Run. It is triggered by Eventarc when a file appears in the `raw/` prefix — after the File Router has already placed it in the correct partitioned subfolder. It has one job: decide whether the file is safe to process. It does this without reading the full file — it reads only the header row and a small sample of data rows. This keeps the check fast and inexpensive regardless of file size.

**Why Cloud Run and not Dataflow**

Dataflow is Google's service for processing large volumes of data in parallel. It is well suited to transforming millions of rows. It is not suited to checking whether a file header matches an expected list of column names. Dataflow jobs take two to three minutes to start up, cost a minimum amount per job regardless of what they do, and require writing an Apache Beam pipeline to accomplish what a twenty-line Python function can do in under two seconds. Cloud Run starts in under two seconds, costs effectively nothing for a file header check, and runs a single Python container with no framework overhead.

Dataform assertions — which run inside BigQuery as part of the transformation process — handle row-level data quality checks after the file has been accepted. The validator handles structural checks before the file is accepted. These two layers are complementary and serve different purposes.

| What is being checked | Where it is checked |
|---|---|
| Is this file the right shape to enter the platform? | Cloud Run Validator — before anything else runs |
| Is the data inside the file correct and consistent? | Dataform assertions — after the file has been loaded |

**What the validator checks**

Every file is put through eight checks in sequence. If any check fails, the file is rejected immediately and the remaining checks are not run.

| Check | What it looks for |
|---|---|
| Column names | Every column name in the file header must exactly match the expected list for that entity type |
| Column count | The number of columns must equal the expected count — catches truncated or malformed files |
| Column order | Columns must appear in the expected sequence — external tables read columns by position, not by name |
| Non-empty file | The file must contain at least one data row beyond the header |
| Encoding | The file must be UTF-8 encoded — files with BOM markers or Latin-1 encoding are rejected |
| Delimiter | The field separator must be a comma — detects files that have been accidentally exported with tabs or pipes |
| Date format | The first ten data rows are sampled to verify that date values in date columns can be parsed correctly |
| File size | Files smaller than 100 bytes are rejected as likely empty or corrupted; anomalously large delta files trigger a warning |

**The schema contracts**

The expected column list for each entity is defined in a Python dictionary inside the validator service and stored in Git alongside the rest of the codebase:

```python
EXPECTED_SCHEMAS = {
    "customers": [
        "customer_id", "first_name", "last_name",
        "email", "signup_date", "region", "loyalty_tier"
    ],
    "products": [
        "product_id", "product_name", "category",
        "unit_price", "stock_quantity", "supplier_id"
    ],
    "orders": [
        "order_id", "customer_id", "order_date",
        "total_amount", "status"
    ],
    "order_items": [
        "order_item_id", "order_id", "product_id",
        "quantity", "unit_price", "line_total"
    ]
}
```

Changing a schema contract requires a deliberate code change, a review, and a redeployment through Cloud Build. This prevents silent schema drift — if the source system changes its file structure, the validator rejects the new file and raises an alert rather than silently accepting data that no longer matches what the platform expects. How schema changes are handled is covered in full in Section 2.5.

**How the validator identifies the entity type**

The validator does not rely on the file name to determine whether a file contains customers, products, or orders. It reads the GCS object path. A file at `gs://.../raw/order_items/order_items_delta_20250315.csv` is identified as an order_items file because it lives in the `raw/order_items/` prefix — not because of what it is named. This makes the check robust to file naming inconsistencies.

**Outcome routing**

Once all checks have run, the validator takes one of two paths.

**If the file passes:**

The validator determines whether the file is a full load or a delta from its name, derives today's date, constructs the correct partitioned path, and copies the file to `gs://intelia-hackathon-dev-raw-data/validated/{entity}/load_type={full|delta}/date={YYYY-MM-DD}/`. It then writes a PASS record to `governance.validation_log`. It then notifies the Pipeline Coordinator Agent by publishing a message to a **Pub/Sub topic**.

Pub/Sub is Google's messaging service. The validator publishes a JSON message to a dedicated topic — for example `pipeline-coordinator-trigger` — containing the entity type, the validated file path, and the validation timestamp. The Pipeline Coordinator Agent is subscribed to this topic. The moment the message is published, Pub/Sub delivers it to the agent, which wakes up and begins evaluating what transformation steps to run. This is a push-based, event-driven handoff — the validator does not call the agent directly, and the agent does not poll for new work. The message on the topic is the signal.

The JSON message published looks like this:

```json
{
  "entity_type": "orders",
  "validated_file_path": "gs://intelia-hackathon-dev-raw-data/validated/orders/load_type=delta/date=2025-03-15/orders_delta_20250315.csv",
  "validation_id": "a3f9c2d1-...",
  "validation_timestamp": "2025-03-15T09:42:11Z"
}
```

The Pipeline Coordinator Agent receives this message, reads the `entity_type`, checks the current pipeline state, and determines what Dataform models to run.

**If the file fails:**

The validator copies the file to `gs://intelia-hackathon-dev-raw-data/quarantine/{entity}/` and writes a FAIL record to `governance.validation_log` containing the name of the failing check and the exact difference between what was expected and what was found. The Pipeline Coordinator Agent is not notified — no Pub/Sub message is published. The transformation pipeline is not triggered.

The validator then writes a structured log entry to **Cloud Logging** — Google's centralised log management service — using the Python `logging` library. The log entry is written at `ERROR` severity and includes the validation ID, entity type, file name, failed check name, expected value, and actual value as structured JSON fields.

Cloud Monitoring watches Cloud Logging continuously via a **log-based alert** — a rule configured by Terraform that says: whenever a log entry with severity `ERROR` appears from the `cloud-run-validator` service, fire an alert. This alert requires no human to be watching a dashboard. It fires the moment the log entry is written.

The alert is delivered via a **notification channel** — also configured by Terraform — which in this platform points to either an email address or a Slack webhook. The notification contains a summary of the log entry: the file name, the entity type, the check that failed, and the exact expected versus actual values. It also includes a direct link to the Cloud Logging entry so the full detail can be inspected, and a direct link to the quarantine path in Cloud Storage so the file can be retrieved.

The full chain is therefore:

```
Validator writes ERROR log to Cloud Logging
    │
    ▼
Cloud Monitoring log-based alert fires (configured by Terraform — no manual setup)
    │
    ▼
Notification channel delivers alert to email or Slack
    │
    ▼
Team member receives: file name · entity type · failed check · expected vs actual · quarantine link
```

The alert is self-contained. A team member receiving it has everything needed to understand what went wrong and where the file is, without logging into any system first.

---

### 5.4 The Validation Log

Every file the validator processes — whether it passes or fails — produces a record in the `governance.validation_log` BigQuery table. This table is the authoritative audit trail for everything that has ever been submitted to the platform.

| Column | What it contains |
|---|---|
| `validation_id` | A unique identifier for this validation run |
| `file_name` | The full GCS path of the file that was checked |
| `entity_type` | Whether the file was customers, products, orders, or order_items |
| `validation_timestamp` | When the check ran |
| `outcome` | PASS or FAIL |
| `failed_check` | The name of the check that failed — null if the file passed |
| `expected_value` | What the validator expected to find — for example, the full expected column list |
| `actual_value` | What the validator actually found in the file |
| `row_count_sample` | How many data rows were sampled during the date format check |
| `file_size_bytes` | The size of the file at the time it was checked |

The `expected_value` and `actual_value` columns together produce an exact diff for every failure. A team member receiving a quarantine alert does not need to open the file to understand what went wrong — the log record tells them precisely which check failed and what the discrepancy was.

This table feeds into the CTO's Looker Studio dashboard as a live health indicator, and is scanned daily by Dataplex as part of the governance layer.

---

### 5.5 Alerting on Failure

The alert itself is described in the outcome routing section above. This section explains what is set up by Terraform to make it work.

Three things are configured automatically when the platform is deployed — no manual setup in the GCP console is required.

**Step 1 — Watch for failures.** Cloud Monitoring is told to watch the validator service for error messages. Every time the validator rejects a file, it writes an error log. Cloud Monitoring counts these and the moment it sees one, it moves to Step 2.

**Step 2 — Decide to alert.** A rule is in place that says: if even a single error appears from the validator, send an alert immediately. There is no waiting period and no minimum count — the very first failure triggers the notification.

**Step 3 — Deliver the notification.** The notification is sent to a team email address or Slack channel — whichever is configured as a deployment variable. The message contains the file name, the entity type, which check failed, what was expected, what was actually found, and a link to the quarantine area where the file is being held.

The destination address or Slack channel is stored as a variable in the deployment configuration, so changing it — for example, pointing alerts to a different team — requires updating one value and redeploying, not reconfiguring the monitoring setup from scratch.

If the platform is ever torn down and rebuilt on a new GCP project, all three steps are recreated automatically as part of the same deployment run that provisions everything else.

---

### 5.6 BigQuery External Tables

Once a file has passed all validation checks and been moved to the `validated/` prefix, it is made available to BigQuery as an external table. External tables are defined over the `validated/` prefix only — not `raw/`, not `inbox/`. This is the boundary that ensures Dataform can only ever read data that has been explicitly cleared by the validator. A file sitting in `raw/` or `quarantine/` is invisible to BigQuery entirely.

An external table is a SQL view over files that stay in Cloud Storage — BigQuery can query them using standard SQL without physically copying the data. The files remain in `validated/` as an immutable record of everything that entered the transformation layer.

Four external tables are defined — one per entity — each pointing to the entity's subfolder within `validated/`. All four tables live in the `validated_external` BigQuery dataset:

```sql
CREATE OR REPLACE EXTERNAL TABLE `validated_external.ext_customers`
OPTIONS (
  format = 'CSV',
  uris   = ['gs://intelia-hackathon-dev-raw-data/validated/customers/*.csv'],
  skip_leading_rows = 1,
  field_delimiter = ',',
  hive_partitioning_options = STRUCT(
    mode = 'AUTO',
    source_uri_prefix = 'gs://intelia-hackathon-dev-raw-data/validated/customers/'
  )
);
```

> The `validated/customers/` prefix contains subfolders using two levels of key-value partitioning: `load_type=full/` or `load_type=delta/` at the first level, and `date=YYYY-MM-DD/` at the second level within delta. BigQuery's `AUTO` mode reads these key-value folder names and automatically creates two virtual columns on the external table — `load_type` and `date` — that can be used in SQL `WHERE` clauses for partition pruning. Files must be placed in correctly named key-value subfolders for this to work — plain folder names such as `full/` or `delta/` would not be recognised.

**How hive partitioning works and why it matters**

Without hive partitioning, the `uris` wildcard `*.csv` tells BigQuery to read every CSV file under the `validated/customers/` prefix on every query — the full load file and every delta file that has ever arrived. As more delta files accumulate over the course of the hackathon, every transformation run would scan an ever-growing set of files regardless of whether they contain new data. This is wasteful and increasingly slow.

Hive partitioning solves this by turning folder names into queryable columns. The key requirement is that subfolders must be named as key-value pairs in the format `key=value`. This platform uses two levels of key-value partitioning under each entity prefix. The first level is `load_type=full` or `load_type=delta`. Delta files additionally carry a second level of `date=YYYY-MM-DD` identifying when the file arrived:

```
gs://intelia-hackathon-dev-raw-data/validated/customers/load_type=full/customers_20250101.csv
gs://intelia-hackathon-dev-raw-data/validated/customers/load_type=delta/date=2025-03-15/customers_delta_20250315.csv
gs://intelia-hackathon-dev-raw-data/validated/customers/load_type=delta/date=2025-03-18/customers_delta_20250318.csv
```

When `mode = 'AUTO'` is set and `source_uri_prefix` points to `validated/customers/`, BigQuery reads all folder name segments beyond that prefix, recognises each `key=value` pair, and automatically creates a virtual column for each one — `load_type` and `date` in this case. Neither column is stored in any file — BigQuery derives both from the path of each row's source file. Both can be used in a SQL `WHERE` clause exactly like any regular column.

A Dataform staging model running as part of a delta load filters to exactly the file that just arrived using both partition columns:

```sql
SELECT *
FROM ${ref('ext_customers')}
WHERE load_type = 'delta'
  AND date = '2025-03-15'
```

A full refresh run reads everything with no filter:

```sql
SELECT *
FROM ${ref('ext_customers')}
```

Critically, BigQuery uses both partition columns to perform **partition pruning** at the storage read level. When `WHERE load_type = 'delta' AND date = '2025-03-15'` is applied, BigQuery navigates directly to the `load_type=delta/date=2025-03-15/` subfolder and reads only the file inside it. The `load_type=full/` folder is skipped entirely, as are every other `date=` subfolder under `load_type=delta/`. None of those files are opened. The exclusion happens before any data is transferred — BigQuery does not scan and then discard, it never touches files outside the matching path.

In practical terms: on Day 1 the full load file is read. On Day 5 when the first delta arrives, only the `date=2025-03-05/` subfolder is read — not the full load file. On Day 10 when another delta arrives, only the `date=2025-03-10/` subfolder is read — not the full load and not the Day 5 delta. Each incremental run reads exactly one file regardless of how many files have accumulated. The cost and speed of every delta run stays constant over the entire life of the platform.

The same pattern is used for `ext_products`, `ext_orders`, and `ext_order_items`. These four external tables are the source that all Dataform staging models read from.

**What the data looks like at this point**

At the external table stage, the data is exactly as it arrived in the source file. Column names match the CSV headers. Values are strings — nothing has been cast to a date, a number, or a boolean yet. Nulls, duplicates, and formatting inconsistencies are all present as they were in the source. The external table is a faithful, unmodified view of what passed the structural gate — the semantic cleaning happens in the Curated layer.

| Table | Columns |
|---|---|
| `ext_customers` | `customer_id`, `first_name`, `last_name`, `email`, `signup_date`, `region`, `loyalty_tier` |
| `ext_products` | `product_id`, `product_name`, `category`, `unit_price`, `stock_quantity`, `supplier_id` |
| `ext_orders` | `order_id`, `customer_id`, `order_date`, `total_amount`, `status` |
| `ext_order_items` | `order_item_id`, `order_id`, `product_id`, `quantity`, `unit_price`, `line_total` |

---

## 6. Transformation & Curated Layer

The Transformation layer sits between the Raw layer and the Consumption layer. Its job is to take the validated, unmodified source data from the external tables and produce clean, trusted, consistently structured entity tables that the dimensional model can be built from. All transformation logic runs inside BigQuery using Dataform — a framework that manages SQL models as version-controlled code and understands the dependencies between them so every model runs in the right order automatically.

---

### 6.1 What Dataform Is and Why It Is Used

Dataform is not a separate compute service. It runs SQL directly inside BigQuery. The transformation logic is written as SQLX files — SQL with a small amount of configuration at the top — and stored in Git alongside the rest of the codebase. When Dataform runs, it reads those files, resolves the dependencies between them, and executes them in the correct order as BigQuery jobs.

The alternative would be writing raw SQL scripts and scheduling them manually, or building a Python pipeline that calls the BigQuery API. Both approaches require managing execution order by hand, have no built-in data quality checks, and produce no automatic lineage. Dataform handles all of this natively — dependencies, execution order, assertions, and lineage are all first-class features of the framework.

---

### 6.2 The Three Transformation Steps

Every entity — customers, products, orders, and order_items — passes through three model tiers in sequence. Each tier has a single, well-defined responsibility.

**Step 1 — Staging models (`stg_*`)**

The staging models are a direct, lightweight translation of the external table source. They do not apply business logic. Their only job is to make the data consistent and correctly typed so that everything downstream can rely on column names and data types without defensive casting.

Every staging model does the following:

- Casts every column to the correct data type — dates are parsed from strings, numeric columns are cast from string, boolean flags are derived
- Renames columns to a consistent `snake_case` naming standard
- Filters out any row where every column is null — these are structurally empty rows that add no value
- Adds two metadata columns: `_loaded_at` (the timestamp when this record was processed) and `_source_file` (the GCS path of the file it came from)

At the end of this step the data is clean in structure and type, but has not been interpreted in any way. A null value in a business field is still a null — it has not been defaulted or filled.

**Step 2 — Intermediate models (`int_*`)**

The intermediate models apply business logic. They take the typed, consistently named staging output and enrich it with derived fields and referential context that make the data meaningful rather than merely clean.

For customers: `days_since_signup` is derived from `signup_date`, and a `customer_age_band` is calculated for segmentation.

For orders: the customer's `region` and `loyalty_tier` are joined in from the customers staging model, and `order_value_band` is derived to group orders into size categories.

For order_items: the product's `category` and `unit_price` at the time of the order are joined in from the products staging model, giving every line item full context about what was purchased.

For products: stock level flags such as `is_low_stock` are derived from `stock_quantity` thresholds.

Nothing is deleted or deduplicated at this step. The append-only principle established in the Raw layer carries through — every record that arrived is still present. The intermediate models only add context, they do not remove records.

**Step 3 — Curated models (`curated_*`)**

The curated models write the final entity tables to the `curated` BigQuery dataset as native BigQuery tables — not views. Writing as tables means the data is physically stored in BigQuery and can be queried at full speed without re-executing the transformation logic each time.

Each curated model appends the output of the intermediate model to the corresponding curated table, stamping every row with `_loaded_at` and `_source_file`. No existing rows are updated or deleted. The full arrival history of every entity is preserved, and older delta records beyond the 90-day retention window are removed by a scheduled maintenance model.

The four curated tables produced are `curated_customers`, `curated_products`, `curated_orders`, and `curated_order_items`.

---

### 6.3 Dataform Assertions — Data Quality Checks

Assertions are the second line of data quality defence, running after the Cloud Run Validator has confirmed the file structure and after the staging models have loaded the data into BigQuery. Where the Cloud Run Validator checks whether a file is the right shape to enter the platform, Dataform assertions check whether the data inside the file is semantically correct.

**How assertions work**

An assertion in Dataform is a SQL query that is expected to return zero rows. If it returns any rows, those rows represent records that violate the rule — and the assertion fails. A failed assertion stops the pipeline run for the affected entity, writes a failure record to `governance.quality_failures`, and triggers the Pipeline Coordinator Agent to evaluate the failure and decide whether to retry, quarantine, or escalate.

Assertions run automatically as part of every Dataform execution — they do not need to be triggered separately. They run after the curated models have been written, which means they catch problems in the data itself rather than in the file structure.

**Why two layers of checking are needed**

The Cloud Run Validator and Dataform assertions are not redundant — they catch different categories of problem at different points in the pipeline.

| What is being checked | Where it is checked | When it runs |
|---|---|---|
| Is the file structurally correct? | Cloud Run Validator | Before the file enters the platform |
| Is the data inside semantically correct? | Dataform assertions | After the data has been loaded into BigQuery |

A file can pass the Cloud Run Validator — correct column names, correct structure, correct encoding — and still contain data that is semantically wrong: negative order amounts, customer IDs that do not exist in the customer table, duplicate order records. The validator cannot detect these because it only reads the file header. Dataform assertions catch them after the data is loaded.

**Assertions defined**

The following assertions run after every pipeline execution. Each one is a separate SQLX file in the `assertions/` folder of the Dataform project and is version-controlled in Git.

| Assertion | Entity | What it checks | Why it matters |
|---|---|---|---|
| `assert_no_null_customer_ids` | Customers | Every row in `curated_customers` has a non-null `customer_id` | A customer without an ID cannot be joined to orders — it would silently drop from all downstream analysis |
| `assert_no_null_order_ids` | Orders | Every row in `curated_orders` has a non-null `order_id` | An order without an ID cannot be joined to order items — the line-item detail would be lost |
| `assert_no_null_order_item_ids` | Order items | Every row in `curated_order_items` has a non-null `order_item_id` | Orphaned line items corrupt revenue calculations |
| `assert_order_amounts_positive` | Orders | `total_amount > 0` for all orders with status `completed` | A completed order with zero or negative value is either a data error or a refund that should be recorded differently |
| `assert_order_item_quantities_positive` | Order items | `quantity > 0` for all order item rows | A line item with zero or negative quantity is always a data error |
| `assert_referential_integrity_orders` | Orders | Every `customer_id` in `curated_orders` exists in `curated_customers` | An order linked to a non-existent customer cannot be attributed to a region, loyalty tier, or cohort |
| `assert_referential_integrity_order_items` | Order items | Every `order_id` in `curated_order_items` exists in `curated_orders` | An order item with no parent order cannot be included in any revenue or product analysis |
| `assert_referential_integrity_products` | Order items | Every `product_id` in `curated_order_items` exists in `curated_products` | An order item referencing a non-existent product cannot be categorised or priced correctly |
| `assert_product_price_non_negative` | Products | `unit_price >= 0` across all products | A negative unit price is always a data error |
| `assert_no_duplicate_order_items` | Order items | No duplicate `order_item_id` in `curated_order_items` | Duplicate line items would double-count revenue for every affected order |

**What happens when an assertion fails**

When any assertion returns rows, Dataform marks that model's execution as failed and writes a structured failure record to the `governance.quality_failures` table in BigQuery. The record contains the assertion name, the entity type, the number of failing rows, the timestamp, and a sample of the failing row values so the problem can be diagnosed without running a separate query.

| Column | What it contains |
|---|---|
| `assertion_id` | Unique identifier for this failure event |
| `assertion_name` | Name of the assertion that failed |
| `entity_type` | Which entity the assertion was checking |
| `failed_row_count` | How many rows violated the rule |
| `sample_failing_values` | A JSON sample of up to ten failing rows |
| `pipeline_run_id` | Links back to the pipeline run that produced the failure |
| `failure_timestamp` | When the assertion ran and failed |

The Pipeline Coordinator Agent reads this table when a failure is detected and uses the `assertion_name` and `failed_row_count` to decide on the appropriate response. A small number of failing rows on a referential integrity check may indicate a timing issue between two entity files and warrant a retry. A large number of failing rows on a null check may indicate a structural problem with the source data and warrant quarantine and escalation.

The `governance.quality_failures` table is also scanned daily by Dataplex and surfaced in the CTO's Looker Studio dashboard as part of the platform health report.

---

### 6.4 The Quality Failures Table and the Validation Log Together

The `governance.validation_log` (written by the Cloud Run Validator) and `governance.quality_failures` (written by Dataform assertions) together give the CTO a complete, end-to-end audit trail of every data quality event that has occurred on the platform — from the moment a file arrived to the moment its data was confirmed as trustworthy inside BigQuery.

A file that passes the Cloud Run Validator but fails a Dataform assertion will have a PASS record in `validation_log` and a failure record in `quality_failures`. A file that fails the Cloud Run Validator will have only a FAIL record in `validation_log` — it never reaches Dataform. Both tables are scanned by Dataplex and both feed the CTO dashboard.

---

## 7. Consumption Layer & Data Marts

*(To be completed)*

---

## 8. Generative AI Integration

Generative AI is used in three distinct ways in this platform. Each one is a working part of the pipeline — if it does not run, something visible to the end user is missing or broken.

### 8.1 Churn Risk Scoring — in the pipeline

Every time the pipeline runs, a machine learning model scores every customer with a churn probability — a number between 0 and 1 that represents the likelihood they will stop purchasing. This score is written directly into the `mart_customer_retention` table as the `churn_risk_score` column.

The model is a logistic regression trained on three signals: how recently a customer ordered, how often they order, and how much they spend in total. It is built and run using BigQuery ML, which means the scoring happens inside BigQuery itself — no separate ML infrastructure is needed.

The CCO's churn risk scorecard in Looker Studio reads directly from this column. If the model does not run, the scorecard is empty.

### 8.2 Customer Narrative Generation — in the pipeline

Also during the pipeline run, a Gemini language model writes a plain-English two-sentence summary for every customer and stores it in the `ai_generated_summary` column of `mart_customer_segments`.

The summary is generated using `ML.GENERATE_TEXT` — a BigQuery ML function that calls Gemini via a remote connection to Vertex AI. The model is given each customer's RFM segment, lifetime value, days since last order, and loyalty tier, and asked to describe that customer in two sentences as a retail analyst would.

The Looker Studio CCO dashboard surfaces this column as an AI insight panel alongside the RFM segment breakdown. If this step does not run, the panel is blank.

### 8.3 Agentic Workflows — Google Agent Development Kit

Three agents are built using the Google Agent Development Kit (ADK). ADK is Google's framework for building agents that can reason, use tools, and make decisions — as opposed to scripts that follow a fixed set of steps. All three agents are deployed to Cloud Run and version-controlled in Git alongside the rest of the codebase.

**Pipeline Coordinator Agent**

When a new file passes validation and enters the pipeline, this agent decides what to run and in what scope. It checks the current pipeline state, identifies which data models are affected by the incoming file, and triggers the correct Dataform execution. If something fails mid-pipeline — for example, a data quality assertion — the agent reads the failure, decides whether it is a data problem or a structural problem, and either retries, quarantines the file, or raises an alert. A static script cannot make this distinction.

**Insight Generation Agent**

Every night this agent queries the mart tables, identifies what changed most significantly since the day before, and writes a plain-English summary to `governance.ai_insights`. Both the CCO and CTO dashboards surface this as an "Insight of the Day" panel. Because the agent reasons over live data rather than running a fixed query, the insight is different every day and reflects what actually happened — not a templated output with today's date on it.

**Conversational Analytics Agent**

The CCO and CTO can ask questions in plain English. This agent receives the question, identifies the right mart table or combination of tables, writes and runs a BigQuery SQL query, and returns a plain-English answer with a supporting data table and a link to the relevant dashboard section. If the first query does not return a useful result, the agent tries again with a refined approach rather than returning nothing.

This agent is also accessible directly from the BigQuery console via the BigQuery Data Agent, giving both personas a zero-friction entry point without needing a separate interface.

### 8.4 Why AI is load-bearing, not decorative

Removing the churn model leaves the CCO retention dashboard with an empty scorecard. Removing narrative generation leaves the customer segments panel blank. Removing the agents leaves the pipeline without intelligent orchestration and both personas without a conversational interface. These are not enhancements — they are structural parts of what the platform delivers.

---

## 9. Data & AI Governance

*(To be completed)*

---

## 10. Scalability & Security

*(To be completed)*

---

## 11. End-to-End Data Flow & Workflow Orchestration

*(To be completed)*
