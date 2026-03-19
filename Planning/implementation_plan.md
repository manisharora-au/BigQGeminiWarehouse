# Hackathon Implementation Plan

This document outlines the detailed, step-by-step implementation plan to execute the Solutions Architecture for the intelia Hackathon.

## Phase 1: Project Setup & Infrastructure as Code (Day 1)
**Goal:** Establish a reproducible, secure foundation on GCP using Terraform.

1.  **GCP Project Bootstrapping:**
    *   Initialize GCP project (using personal project or requesting a new one).
    *   Enable required APIs: Compute Engine, Cloud Storage, BigQuery, Eventarc, Cloud Run, Vertex AI, Dataplex.
    *   Set up billing alerts to ensure the project stays within the $200 budget.
2.  **Service Accounts & IAM:**
    *   Create dedicated service accounts for Terraform (provisioning) and Cloud Run/dbt (execution).
    *   Assign least-privilege roles necessary for each component.
3.  **Terraform Base Configuration:**
    *   Create a GCS bucket to store Terraform state securely.
    *   Provision the raw GCS bucket for data ingestion.
    *   Provision BigQuery datasets for the 3 layers: `raw_ext`, `curated`, and `consumption_marts`.

## Phase 2: Data Ingestion & Raw Layer Setup (Day 1-2)
**Goal:** Ingest the initial dataset and establish the immutable raw layer.

1.  **Initial Data Load:**
    *   Use `gcloud storage` or scripts to copy the initial `.csv` files from `gs://intelia-hackathon-files/` to the newly provisioned raw GCS bucket.
2.  **BigQuery External Tables:**
    *   Define schema for `customers.csv`, `products.csv`, `orders.csv`, and `order_items.csv`.
    *   Create BigQuery External Tables in the `raw_ext` dataset pointing to the GCS bucket to allow direct querying without full ingestion.

## Phase 3: Transformation & Orchestration (Dataform + Cloud Run) (Day 2-3)
**Goal:** Build the curated layer and automate the pipeline for delta updates.

1.  **Dataform Repository Initialization:**
    *   Initialize a new Dataform repository within the GCP project.
    *   Configure workspace settings to connect to the BigQuery project using the execution service account.
2.  **Develop Dataform Models:**
    *   **Staging:** Create `.sqlx` files to clean, cast data types, and standardize column names from the `raw_ext` tables.
    *   **Curated:** Create conformed dimension and fact tables (e.g., handling deduplication or slowly changing dimensions if required).
    *   Add Dataform assertions (unique, not null, referential integrity) and inline documentation.
3.  **Containerize & Orchestrate (Cloud Run + Eventarc):**
    *   Write a script or service to trigger the Dataform workflow execution via API.
    *   Deploy the service as a Cloud Run container.
    *   Configure Eventarc to listen for GCS file creation events in the raw bucket and trigger the Cloud Run job, automating the pipeline when delta datasets arrive.

## Phase 4: Consumption Layer & Data Marts (Day 3-4)
**Goal:** Serve the CCO and CTO personas with tailored data marts and dashboards.

1.  **Develop Data Mart Models (Dataform):**
    *   Build the CCO Data Mart: Tables focused on revenue, customer lifetime value, and retention.
    *   Build the CTO Data Mart: Tables focused on system metrics, data freshness, and processing volumes.
2.  **Looker Studio Dashboards:**
    *   Connect Looker Studio to the BigQuery consumption datasets.
    *   Design the CCO Dashboard: Visualizations for key revenue and customer KPIs.
    *   Design the CTO Dashboard: Visualizations highlighting platform health and SLA metrics.

## Phase 5: Generative AI Integration (Day 4-5)
**Goal:** Implement meaningful GenAI capabilities to drive actionable insights.

1.  **BigQuery ML (`ML.GENERATE_TEXT`):**
    *   Create BQML models that connect to Vertex AI's Gemini models.
    *   Write SQL queries to automate insight generation (e.g., summarizing top product trends or analyzing customer purchasing patterns) directly within the data warehouse.
2.  **Conversational Analytics (Vertex AI Studio):**
    *   Prototype a data agent using Vertex AI Studio capable of querying the data marts based on natural language questions from the CCO.

## Phase 6: Governance, Polish, & Presentation (Day 6-7)
**Goal:** Elevate the solution to enterprise-grade and prepare for judging.

1.  **Dataplex Setup (Bonus):**
    *   Configure Dataplex to scan GCS and BigQuery.
    *   Establish the Data Catalogue and map data lineage across the 3 layers.
    *   Set up automated data quality rules.
2.  **Code Hardening & Cleanup:**
    *   Review IAM permissions (ensure no leaks).
    *   Clean up Terraform modules and verify deployment from scratch works flawlessly.
3.  **Presentation Prep:**
    *   Finalize the Architecture diagram.
    *   Draft the overview presentation, ensuring it speaks directly to the CCO and CTO personas.
    *   Record a concise demo of the end-to-end automated pipeline (from dropping a delta file in GCS to seeing the Looker dashboard update and querying the AI agent).
