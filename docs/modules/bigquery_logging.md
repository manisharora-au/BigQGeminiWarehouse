# BigQuery Logging Module Documentation

## Overview

The BigQuery Logging module handles long-term persistence of governance and audit data to BigQuery. This module focuses purely on BigQuery operations for compliance requirements, historical analysis, and data governance tracking. It provides structured record creation and batch insertion capabilities for validation results and batch processing metrics.

## Purpose

- **Governance Data Persistence**: Store validation results for compliance and audit
- **Long-term Analysis**: Enable historical trend analysis and reporting
- **Audit Trail Compliance**: Maintain complete audit trails for regulatory requirements
- **Batch Performance Tracking**: Record batch processing metrics and success rates
- **Data Quality Monitoring**: Track validation patterns across time and entity types

## Key Components

### Class: BigQueryLogging

A static utility class that provides methods for creating structured records and writing them to BigQuery tables for governance and audit purposes.

### Methods

#### `create_validation_log_record(...) -> Dict[str, Any]`
- **Purpose**: Create structured validation record for BigQuery insertion
- **Parameters**:
  - `validation_id` (str): Unique validation identifier
  - `bucket_name` (str): GCS bucket name
  - `filename` (str): Original filename
  - `metadata` (Dict): Extracted file metadata
  - `success` (bool): Validation success status
  - `failed_check` (Optional[str]): Failed validation check name
  - `expected_value` (Optional[str]): Expected value for failed check
  - `actual_value` (Optional[str]): Actual value found
  - `error_message` (Optional[str]): Detailed error message
- **Returns**: Structured dictionary with all validation details
- **Record Structure**:
  - Validation identifiers and timestamps
  - File path and metadata information
  - Validation status (PASS/FAIL) and failure details
  - Processor information and versioning

#### `write_validation_result_to_bigquery(...) -> bool`
- **Purpose**: Write single validation result to BigQuery governance table
- **Parameters**:
  - `project_id` (str): GCP project ID
  - `dataset_id` (str): BigQuery dataset (typically 'governance')
  - `table_id` (str): BigQuery table (typically 'validation_log')
  - `validation_record` (Dict): Record from `create_validation_log_record()`
- **Returns**: `True` if successful, `False` if failed
- **Error Handling**: Comprehensive logging of BigQuery API errors
- **Use Case**: Single file validation result persistence

#### `write_batch_validation_results_to_bigquery(...) -> Dict[str, int]`
- **Purpose**: Write multiple validation results to BigQuery in batch operation
- **Parameters**:
  - `project_id` (str): GCP project ID
  - `dataset_id` (str): BigQuery dataset ID
  - `table_id` (str): BigQuery table ID
  - `validation_records` (List[Dict]): List of validation records
- **Returns**: Statistics dictionary with successful/failed counts
- **Performance**: Optimized batch insertion for high-volume processing
- **Counting Logic**: Counts PASS/FAIL results from validation_status field
- **Error Recovery**: Continues processing on partial failures

#### `create_batch_processing_record(...) -> Dict[str, Any]`
- **Purpose**: Create batch processing record for governance tracking
- **Parameters**:
  - `batch_id` (str): Unique batch identifier
  - `total_files` (int): Total files processed
  - `successful_files` (int): Successfully processed files
  - `failed_files` (int): Failed files count
  - `processing_time_ms` (int): Total processing duration
  - `throughput_files_per_second` (float): Processing throughput
  - `entity_types_processed` (List[str]): Entity types in batch
- **Calculated Fields**:
  - `success_rate_percent`: Automatic calculation
  - `batch_timestamp`: Current UTC timestamp
- **Returns**: Structured batch processing record

#### `write_batch_processing_record(...) -> bool`
- **Purpose**: Write batch processing record to BigQuery for governance
- **Parameters**:
  - `project_id` (str): GCP project ID
  - `dataset_id` (str): BigQuery dataset ID
  - `table_id` (str): Table ID (e.g., 'batch_processing_log')
  - `batch_record` (Dict): Batch processing record
- **Returns**: `True` if successful, `False` if failed
- **Use Case**: Track batch job performance and success metrics

## Data Structures

### Validation Log Record Schema
```json
{
  "validation_id": "validation_a3f9c2d1",
  "file_path": "gs://my-bucket/inbox/customers_20260101.csv",
  "bucket_name": "my-bucket",
  "filename": "customers_20260101.csv",
  "entity_type": "customers",
  "load_type": "full",
  "batch_id": null,
  "file_date": "20260101",
  "validation_timestamp": "2026-04-14T16:30:00Z",
  "validation_status": "PASS",
  "failed_check": null,
  "expected_value": null,
  "actual_value": null,
  "error_message": null,
  "processor": "cloud-run-validator",
  "processor_version": "1.0"
}
```

### Batch Processing Record Schema
```json
{
  "batch_id": "batch_abc123_20260414",
  "batch_timestamp": "2026-04-14T16:30:00Z",
  "total_files": 50,
  "successful_files": 48,
  "failed_files": 2,
  "processing_time_ms": 15000,
  "throughput_files_per_second": 3.2,
  "success_rate_percent": 96.0,
  "entity_types_processed": ["customers", "orders"],
  "processor": "cloud-run-validator",
  "processor_version": "1.0"
}
```

## Integration Points

### BigQuery Tables

#### governance.validation_log
- **Purpose**: Individual file validation results
- **Partitioning**: Recommended by validation_timestamp
- **Usage**: Compliance audits, validation trend analysis
- **Retention**: Based on compliance requirements

#### governance.batch_processing_log
- **Purpose**: Batch job performance and metrics
- **Partitioning**: Recommended by batch_timestamp
- **Usage**: Performance monitoring, SLA tracking
- **Retention**: Operational data retention policy

### Used By
- **FileValidator**: Single file validation logging
- **BatchFileProcessor**: Batch validation and processing metrics
- **FileRouter**: Integration for complete audit trail
- **Compliance Reports**: Historical analysis and trend monitoring

## Error Handling and Logging

### BigQuery API Errors
- **Connection Failures**: Logged with retry recommendations
- **Schema Mismatches**: Detailed error logging with field information
- **Quota Exceeded**: Graceful degradation with backoff strategies
- **Permission Issues**: Clear IAM troubleshooting information

### Structured Error Logging
```json
{
  "event_type": "bigquery_insert_failure",
  "validation_id": "validation_a3f9c2d1",
  "table_ref": "my-project.governance.validation_log",
  "errors": ["Row insert failed: Invalid timestamp format"],
  "error_message": "BigQuery API error details"
}
```

## Performance Optimization

### Batch Operations
- **Batch Size**: Optimized for BigQuery insert limits
- **Streaming vs Batch**: Uses batch insert for cost optimization
- **Memory Management**: Efficient record creation without accumulation
- **Connection Pooling**: Reuses BigQuery client connections

### Query Performance
- **Partitioning**: Timestamp-based partitioning for query optimization
- **Clustering**: Recommended clustering on entity_type and validation_status
- **Indexing**: Automatic BigQuery optimization for common query patterns

## Security and Compliance

### Data Privacy
- **No PII Storage**: Avoids storing sensitive personal information
- **Metadata Only**: Stores file processing metadata, not content
- **Audit Trail**: Complete processing history for compliance

### Access Control
- **IAM Integration**: Uses BigQuery IAM for access control
- **Service Account**: Dedicated service account for BigQuery operations
- **Least Privilege**: Minimal permissions for insert operations only

### Data Retention
- **Compliance Driven**: Retention based on regulatory requirements
- **Automatic Cleanup**: Configurable data lifecycle policies
- **Backup Strategy**: Integration with BigQuery backup and archival

## Monitoring and Alerting

### Key Metrics
- BigQuery insert success rates
- Validation result distribution (PASS/FAIL ratios)
- Batch processing performance trends
- Error rate monitoring by entity type

### Query Examples

#### Validation Success Rate by Entity
```sql
SELECT 
  entity_type,
  COUNT(*) as total_validations,
  COUNTIF(validation_status = 'PASS') as successful_validations,
  SAFE_DIVIDE(COUNTIF(validation_status = 'PASS'), COUNT(*)) * 100 as success_rate_percent
FROM `project.governance.validation_log`
WHERE validation_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY entity_type
ORDER BY success_rate_percent DESC
```

#### Batch Performance Trends
```sql
SELECT 
  DATE(batch_timestamp) as processing_date,
  AVG(throughput_files_per_second) as avg_throughput,
  AVG(success_rate_percent) as avg_success_rate,
  SUM(total_files) as total_files_processed
FROM `project.governance.batch_processing_log`
WHERE batch_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY processing_date
ORDER BY processing_date DESC
```

## Troubleshooting

### Common Issues
- **Schema Evolution**: Handle BigQuery schema changes gracefully
- **Quota Limits**: Monitor and alert on BigQuery quota usage
- **Performance Degradation**: Optimize query patterns and partitioning
- **Cost Management**: Monitor BigQuery usage and optimize for cost

### Debugging Tools
- **Structured Logging**: Comprehensive error context in Cloud Logging
- **BigQuery Job Console**: Monitor insert job success/failure rates
- **Performance Metrics**: Track insert latency and throughput