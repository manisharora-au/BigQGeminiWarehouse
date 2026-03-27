# ==============================================================================
# Module: BigQuery Datasets and Tables
# Description: Four datasets for medallion architecture + governance tables
# ==============================================================================

# Dataset 1: validated_external - External tables over GCS
resource "google_bigquery_dataset" "validated_external" {
  dataset_id    = "validated_external"
  friendly_name = "Validated External Tables"
  description   = "External tables pointing to validated GCS files with hive partitioning"
  location      = var.region
  
  labels = merge(var.labels, {
    layer = "raw"
    type  = "external"
  })
}

# Dataset 2: curated - Cleaned and conformed tables
resource "google_bigquery_dataset" "curated" {
  dataset_id    = "curated"
  friendly_name = "Curated Data"
  description   = "Cleaned and conformed tables built by Dataform"
  location      = var.region
  
  labels = merge(var.labels, {
    layer = "curated"
  })
}

# Dataset 3: marts - Dimensional models and data marts
resource "google_bigquery_dataset" "marts" {
  dataset_id    = "marts"
  friendly_name = "Data Marts"
  description   = "Dimensional models and data marts for analytics"
  location      = var.region
  
  labels = merge(var.labels, {
    layer = "consumption"
  })
}

# Dataset 4: governance - Pipeline logs and metadata
resource "google_bigquery_dataset" "governance" {
  dataset_id    = "governance"
  friendly_name = "Data Governance"
  description   = "Pipeline logs, quality metrics, and governance metadata"
  location      = var.region
  
  labels = merge(var.labels, {
    purpose = "governance"
  })
}

# Governance table: validation_log
resource "google_bigquery_table" "validation_log" {
  dataset_id = google_bigquery_dataset.governance.dataset_id
  table_id   = "validation_log"
  
  schema = jsonencode([
    {
      name = "file_path"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "entity_type"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "validation_status"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "failed_check"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "expected_value"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "actual_value"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "processed_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "file_size_bytes"
      type = "INTEGER"
      mode = "NULLABLE"
    }
  ])
  
  labels = var.labels
}

# Governance table: quality_failures
resource "google_bigquery_table" "quality_failures" {
  dataset_id = google_bigquery_dataset.governance.dataset_id
  table_id   = "quality_failures"
  
  schema = jsonencode([
    {
      name = "assertion_name"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "failed_row_count"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "total_row_count"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "failure_sql"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "execution_time"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "dataform_run_id"
      type = "STRING"
      mode = "NULLABLE"
    }
  ])
  
  labels = var.labels
}

# Governance table: ingestion_log
resource "google_bigquery_table" "ingestion_log" {
  dataset_id = google_bigquery_dataset.governance.dataset_id
  table_id   = "ingestion_log"
  
  schema = jsonencode([
    {
      name = "pipeline_name"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "entity_type"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "load_type"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "rows_processed"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "bytes_processed"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "duration_seconds"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "status"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "started_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "completed_at"
      type = "TIMESTAMP"
      mode = "NULLABLE"
    },
    {
      name = "error_message"
      type = "STRING"
      mode = "NULLABLE"
    }
  ])
  
  labels = var.labels
}

# Governance table: ai_insights
resource "google_bigquery_table" "ai_insights" {
  dataset_id = google_bigquery_dataset.governance.dataset_id
  table_id   = "ai_insights"
  
  schema = jsonencode([
    {
      name = "insight_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "insight_type"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "narrative"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "supporting_metrics"
      type = "JSON"
      mode = "NULLABLE"
    },
    {
      name = "generated_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "target_persona"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "confidence_score"
      type = "FLOAT"
      mode = "NULLABLE"
    }
  ])
  
  labels = var.labels
}