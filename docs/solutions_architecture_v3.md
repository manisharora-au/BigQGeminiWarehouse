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
3. [Architecture Overview](#3-architecture-overview)
4. [Infrastructure &amp; Automation](#4-infrastructure--automation)
5. [Data Ingestion &amp; Raw Layer](#5-data-ingestion--raw-layer)
6. [Transformation &amp; Curated Layer](#6-transformation--curated-layer)
7. [Consumption Layer &amp; Data Marts](#7-consumption-layer--data-marts)
8. [Generative AI Integration](#8-generative-ai-integration)
9. [Data &amp; AI Governance](#9-data--ai-governance)
10. [Scalability &amp; Security](#10-scalability--security)
11. [End-to-End Data Flow &amp; Workflow Orchestration](#11-end-to-end-data-flow--workflow-orchestration)

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

The Raw layer holds source data exactly as it arrived — no transformations, no corrections, no interpretation of any kind. Files land in Google Cloud Storage (GCS) as CSVs. Before a file is permitted to enter this layer, a validation gate checks that it conforms to a known schema contract: correct column names, column count, column order, encoding, delimiter, and date format. A file that fails this check is quarantined and never enters the platform. This gate exists to protect all downstream layers from malformed or unexpected input — a problem that, if undetected, would silently corrupt marts and dashboards.

Files that pass validation are made available to BigQuery as **external tables**. An external table is a typed SQL lens over a file that remains in GCS — BigQuery can query it without physically ingesting the data into its own storage. This preserves the raw file as an immutable audit record and avoids storage duplication.

What the data looks like here: three external tables (`ext_customers`, `ext_products`, `ext_orders`) whose columns mirror the CSV headers exactly. If the source sent a null, a duplicate, or a malformed date, it exists here unchanged. The Raw layer is a faithful record of what was received, not what was intended.

---

#### 2.1.2 Layer 2 — Curated: cleaned, conformed, and trustworthy

The Curated layer is not a dimensional model. It is not a star schema. It contains one table per business entity — customers, products, orders — each representing a single, trusted, deduplicated version of that entity with a meaningful and consistent schema.

Transformation from Raw to Curated happens in three sequential steps:

*Staging* casts every column to the correct data type, renames columns to a consistent `snake_case` standard, filters fully null rows, and attaches ingestion metadata (`_loaded_at`, `_source_file`). This is structural cleanup — the data is not yet interpreted, just made consistent and typed.

*Intermediate* applies business logic: referential enrichment (joining customer region onto orders, product category onto order lines) and derivation of calculated fields such as `days_since_signup` and `is_repeat_customer`. This is where raw data becomes meaningful.

*Curated* materialises the final conformed entity tables in BigQuery native storage using an **append-only** approach. Every record that arrives — whether from a full load or a delta drop — is written as a new row stamped with `_loaded_at` and `_source_file`. No existing record is ever updated or deleted during the pipeline run. This means the curated tables hold a complete, immutable history of every version of every entity as it arrived over time.

Downstream models in the Consumption layer always derive the current state of an entity at query time using a simple `ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY _loaded_at DESC) = 1` pattern — selecting the most recently arrived record per entity. This keeps the curated layer simple and safe to reprocess: because nothing is mutated, any pipeline run can be replayed from scratch without risk of data corruption.

Older records are culled on a defined schedule — delta records beyond a 90-day retention window are removed by a scheduled Dataform maintenance model. Full load records are retained for the lifetime of the project as the baseline. This balances auditability with cost efficiency.

What the data looks like here: three append-only entity tables — `curated_customers`, `curated_products`, and `curated_orders` — each containing all historical arrivals for that entity, stamped with ingestion metadata. Clean types, consistent naming, no nulls on key fields. This is the single source of truth that all downstream consumption is built from.

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

`fact_orders` is the central fact table, one row per order line. It joins to dimension surrogate keys — not natural keys — ensuring every historical query resolves to the correct version of each dimension at the time of the transaction.

**Persona-specific marts**

On top of the star schema, persona-specific mart tables pre-aggregate and pre-compute the metrics each persona needs. Three serve the CCO — `mart_revenue`, `mart_customer_retention`, and `mart_customer_segments` — and two serve the CTO — `mart_system_adoption` and `mart_pipeline_performance`. These marts are materialised tables or views over the star schema, not independent flat tables. They inherit the historical accuracy of the dimensional model beneath them.

AI-generated columns — `churn_risk_score` from BigQuery ML and `ai_generated_summary` from `ML.GENERATE_TEXT` — are written into the CCO marts during the pipeline run.

What the data looks like here: a star schema foundation of four tables with SCD Type 2 on key dimensions, and five persona-specific mart tables sitting on top providing fast, pre-aggregated query surfaces for dashboards and AI agents.

---

### 2.2 Why These Layers Are Separate

Separating Raw, Curated, and Consumption into distinct physical layers is not a stylistic choice — it has concrete operational consequences.

If a transformation bug is discovered in a curated model, the Raw layer is untouched and can be fully reprocessed without re-ingesting data from the source. If a mart is rebuilt with a new metric definition, the Curated layer is untouched and does not need to be re-cleansed. Each layer can fail, be corrected, and be rerun independently. This is what makes the platform reproducible and recoverable rather than fragile.

It also means each layer has a clear data contract. The Raw layer's contract is structural: the file must match the expected schema. The Curated layer's contract is semantic: every record must be valid, consistently typed, and enriched with meaningful metadata before it is trusted as a source for downstream consumption. The Consumption layer's contract is dimensional: every fact record must join accurately to the correct version of every dimension at the time of the transaction, and every mart must answer its persona's questions correctly and efficiently. Governance, quality checks, and access controls are applied at the boundary of each layer — not as an afterthought at the end.

---

### 2.3 Where GCP Services Map to Each Layer

The table below gives a single-sentence orientation for every GCP service used in this platform. Each service is explained in full in its respective section.

| Layer                    | GCP Service                                  | What it does                                                                                                                                                                                                                                                                                 |
| :----------------------- | -------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Infrastructure** | Terraform                                    | Provisions every GCP resource from scratch — storage buckets, BigQuery datasets, service accounts, networking controls, governance, and monitoring — as code, so the entire platform can be torn down and rebuilt on a new project without manual steps                                    |
| **Infrastructure** | Cloud Build                                  | Runs the full deployment sequence automatically in order: provision infrastructure, deploy transformation logic, load initial data, run the pipeline                                                                                                                                         |
| **Infrastructure** | Secret Manager                               | Stores all passwords, API keys, and access credentials in one secure place; the pipeline reads from it but never writes to it                                                                                                                                                                |
| **Infrastructure** | Cloud Monitoring                             | Watches the platform for problems — fires alerts when a file fails validation or the budget approaches its limit, and provides the CTO with a live operational dashboard                                                                                                                    |
| **Infrastructure** | IAM & Service Accounts                       | Controls who and what can access each part of the platform; every component runs under its own dedicated account with access limited to only what it needs                                                                                                                                   |
| **Infrastructure** | VPC Service Controls                         | Creates a security boundary around the platform so that data in BigQuery and Cloud Storage cannot be accessed from outside the project, even if credentials were compromised                                                                                                                 |
| **Infrastructure** | Private Google Access                        | Allows internal platform components to communicate with Google services over Google's private network rather than the public internet, reducing exposure                                                                                                                                     |
| **All layers**     | Dataplex                                     | Provides a single governance view across all three data layers — cataloguing every table, tracking where data came from, running daily data quality checks, and enforcing access controls on sensitive fields such as customer names and email addresses                                    |
| **Raw**            | Google Cloud Storage                         | The initial landing zone for all incoming data files, organised into separate areas for newly arrived files, validated files, rejected files, and archived files                                                                                                                             |
| **Raw**            | Eventarc                                     | Detects when a new file lands in Cloud Storage and immediately triggers the validation check — no manual intervention or polling required                                                                                                                                                   |
| **Raw**            | Cloud Run — Validator                       | Checks every incoming file against a known set of rules before anything else touches it — correct column names, correct structure, correct encoding; files that pass move forward, files that fail are isolated and an alert is raised (see Section 2.5 for how schema changes are handled) |
| **Raw**            | BigQuery External Tables                     | Makes validated source files immediately queryable using SQL without copying the data — the file stays in Cloud Storage and BigQuery reads it directly                                                                                                                                      |
| **Raw**            | BigQuery (`governance` dataset)            | Records the outcome of every file validation and every data quality check, giving the CTO a full audit trail of what was accepted, what was rejected, and why                                                                                                                                |
| **Curated**        | Google ADK — Pipeline Coordinator Agent     | An AI agent that decides what transformation work needs to run after a file is validated — it checks the current state of the pipeline, identifies what is affected, and handles failures by deciding whether to retry, isolate the problem, or raise an alert                              |
| **Curated**        | Dataform                                     | Runs the data transformation steps in the correct order — cleaning, enriching, and conforming the raw data into trusted entity tables that the Consumption layer can rely on                                                                                                                |
| **Curated**        | BigQuery (`curated` dataset)               | Stores cleaned and enriched versions of the three core entities — customers, products, and orders — retaining the full history of every record that has ever arrived, with records older than 90 days automatically removed                                                                |
| **Consumption**    | BigQuery (`marts` dataset)                 | Stores the dimensional model — dimension tables for customers, products, and dates, a central orders fact table, and five summary tables tailored to the specific questions the CCO and CTO need answered                                                                                   |
| **Consumption**    | BigQuery ML                                  | Runs two AI tasks during the pipeline: scoring every customer with a churn risk probability, and generating a plain-English summary of each customer's profile using Gemini                                                                                                                  |
| **Consumption**    | BigQuery Data Agent                          | Allows the CCO and CTO to ask questions about the data in plain English directly from the BigQuery console and receive answers without writing any SQL                                                                                                                                       |
| **Consumption**    | Google ADK — Insight Generation Agent       | An AI agent that runs every night, identifies what changed most significantly in the data since the previous day, and writes a plain-English summary of those findings for both personas to read the following morning                                                                       |
| **Consumption**    | Google ADK — Conversational Analytics Agent | An AI agent that answers natural language questions from the CCO and CTO — it identifies the right data, runs the query, interprets the result, and responds in plain English with a link to the relevant dashboard                                                                         |
| **Consumption**    | Cloud Scheduler                              | Triggers the nightly Insight Generation Agent automatically, ensuring fresh insights are ready before business hours each day                                                                                                                                                                |
| **Consumption**    | Looker Studio                                | Delivers two visual dashboards — one for the CCO covering revenue, customer retention, and churn risk, and one for the CTO covering pipeline health, data quality, and platform cost                                                                                                        |

---

### 2.4 Agentic Design Principle

Not every component in this platform should reason. Deterministic automation — infrastructure provisioning, schema validation, file routing — must behave identically every time it runs. Introducing reasoning into those components would add unpredictability where correctness is the only acceptable outcome. A file either passes schema validation or it does not. Terraform either provisions a resource or it fails. There is no judgement call to be made.

Agentic workflows are appropriate precisely where a fixed decision tree is insufficient — where the right action depends on context, where conditions change between runs, and where a human would otherwise need to intervene to make a call. This platform uses the **Google Agent Development Kit (ADK)** to implement three agents, each replacing a component that would otherwise be a static script.

**Agent 1 — Pipeline Coordinator Agent (Curated layer)**

The previous design used a Cloud Run script to receive a PASS signal from the validator, map entity type to a Dataform tag, and trigger the execution. This works for the happy path. It cannot handle what happens when things go wrong mid-pipeline: an assertion fails on the third model in a DAG, a delta file passes validation but produces referential integrity violations downstream, or two delta files for the same entity arrive in rapid succession and need to be sequenced.

The Pipeline Coordinator Agent replaces this script. It receives the PASS event, queries the pipeline run history to understand current state, reasons over what models are stale and what dependencies are affected, and calls the Dataform Workflow API with the correct execution scope. If an assertion fails, the agent evaluates the failure record in `governance.quality_failures`, determines whether it is a data anomaly or a structural issue, and decides whether to retry the affected models, quarantine the source file, or write an escalation record and halt. This is not a decision tree — it is reasoning over state.

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
        "order_id", "customer_id", "product_id",
        "order_date", "quantity", "total_amount", "status"
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

| Field              | Example value                                                                     |
| ------------------ | --------------------------------------------------------------------------------- |
| `failed_check`   | `column_name_mismatch`                                                          |
| `expected_value` | `order_id, customer_id, product_id, order_date, quantity, total_amount, status` |
| `actual_value`   | `order_id, customer_id, product_id, order_date, quantity, amount, status`       |

In this example the diff is immediately obvious: `total_amount` has been renamed to `amount` in the source.

**Scenario 3 — Gradual drift: encoding, delimiter, or date format shift**

This is the subtler risk. The column structure is unchanged but the file's encoding shifts from UTF-8 to Latin-1, the delimiter changes from comma to pipe, or date values in a sample row no longer parse against the expected format. These changes do not always arrive in a single file — they may appear gradually across delta drops.

The validator catches these at the gate on the first affected file. The specific checks that cover this scenario are: encoding detection (UTF-8 required, BOM and Latin-1 rejected), delimiter assertion (comma required), and date format sampling across the first ten data rows. Any of these failing produces a quarantine event with the specific check named in `failed_check`.

Dataplex daily quality scans on the `curated.*` and `marts.*` datasets provide a second layer of detection for drift that accumulates between runs. Dataform assertions provide a third layer at the row level during every pipeline execution. These are complementary — not substitutes for the gate.

**The reprocessing path for quarantined files**

Every file moved to `quarantine/` is retained there for the full 365-day GCS retention window. Once the schema contract has been updated and redeployed, the quarantined file can be manually copied back to `raw/{entity}/delta/`, which re-triggers the Eventarc → Validator → Pipeline flow from the beginning. The file is re-validated against the updated contract. If it now passes, it proceeds through the pipeline as normal. The original quarantine record in `governance.validation_log` is preserved — it is never deleted or updated — providing a complete audit trail of the rejection, the resolution, and the reprocessing.

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

*(To be completed)*

---

## 6. Transformation & Curated Layer

*(To be completed)*

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
