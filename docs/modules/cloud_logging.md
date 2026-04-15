# Cloud Logging Module Documentation

## Overview

The Cloud Logging module handles structured logging to Google Cloud Logging for operational monitoring, real-time debugging, and alerting. This module focuses purely on Cloud Logging operations without BigQuery persistence, providing comprehensive observability for the file processing pipeline.

## Purpose

- **Operational Monitoring**: Real-time visibility into file processing operations
- **Structured Logging**: Consistent log format with metadata for easy querying
- **Alerting Support**: Enable real-time alerts on validation failures and system issues
- **Performance Tracking**: Log processing metrics and timing information
- **Debugging Support**: Detailed error context for troubleshooting

## Key Components

### Class: CloudLogging

A static utility class that provides structured logging methods for various file processing events and metrics.

### Methods

#### `generate_validation_id() -> str`
- **Purpose**: Generate unique validation identifier for correlation tracking
- **Returns**: Unique validation ID (format: `validation_xxxxxxxx`)
- **Example Output**: `validation_a3f9c2d1`
- **Usage**: Called before file validation to create correlation ID

#### `log_validation_result(...)`
- **Purpose**: Log comprehensive validation results for operational monitoring
- **Parameters**:
  - `validation_id` (str): Unique validation identifier
  - `bucket_name` (str): GCS bucket name
  - `filename` (str): Original filename being processed
  - `metadata` (Dict): Extracted file metadata
  - `success` (bool): Whether validation passed
  - `failed_check` (Optional[str]): Specific check that failed
  - `error_message` (Optional[str]): Detailed error description
  - `expected_value` (Optional[str]): Expected value for failed checks
  - `actual_value` (Optional[str]): Actual value found for failed checks
- **Log Level**: INFO (success) / ERROR (failure)
- **Structured Fields**:
  - `validation_id`, `file_path`, `bucket_name`, `filename`
  - `entity_type`, `load_type`, `batch_id`, `file_date`
  - `validation_status` (PASS/FAIL), `failed_check`, `error_message`
  - `processed_at`, `processor`, `processor_version`, `event_type`

#### `log_batch_processing_start(...)`
- **Purpose**: Log batch processing initiation with configuration details
- **Parameters**:
  - `batch_id` (str): Unique batch identifier
  - `file_count` (int): Number of files in batch
  - `processing_mode` (str): Processing mode ('standard', 'priority')
  - `max_workers` (int): Maximum concurrent workers
- **Log Level**: INFO
- **Use Case**: Track batch job start events and resource allocation

#### `log_batch_processing_complete(...)`
- **Purpose**: Log batch completion with comprehensive metrics
- **Parameters**:
  - `batch_id` (str): Unique batch identifier
  - `total_files` (int): Total files processed
  - `successful_files` (int): Successfully processed files
  - `failed_files` (int): Failed files count
  - `processing_time_ms` (int): Total processing duration
  - `throughput_files_per_second` (float): Processing throughput
- **Calculated Metrics**: Success rate percentage
- **Log Level**: INFO
- **Use Case**: Performance monitoring and success rate tracking

#### `log_file_processing_metrics(...)`
- **Purpose**: Log individual file processing performance metrics
- **Parameters**:
  - `filename` (str): Processed file name
  - `validation_id` (str): Correlation ID
  - `processing_time_ms` (int): File processing duration
  - `file_size_bytes` (int): File size in bytes
  - `validation_status` (str): PASS or FAIL
  - `destination_path` (Optional[str]): Final file destination
- **Calculated Metrics**: Throughput in MB/second
- **Log Level**: INFO
- **Use Case**: Performance analysis and optimization

#### `log_cloud_storage_operation(...)`
- **Purpose**: Log Cloud Storage operations (copy, move, delete)
- **Parameters**:
  - `operation` (str): Operation type ('copy', 'move', 'delete')
  - `source_path` (str): Source GCS path
  - `destination_path` (str): Destination GCS path
  - `success` (bool): Operation success status
  - `duration_ms` (int): Operation duration
  - `error_message` (Optional[str]): Error details if failed
- **Log Level**: INFO (success) / ERROR (failure)
- **Use Case**: GCS operation monitoring and error tracking

#### `log_governance_event(...)`
- **Purpose**: Log governance and compliance events
- **Parameters**:
  - `event_type` (str): Governance event type
  - `entity_type` (str): Entity being processed
  - `file_count` (int): Number of files involved
  - `validation_results` (Dict[str, int]): Validation statistics
  - `additional_context` (Optional[Dict]): Additional context data
- **Log Level**: INFO
- **Use Case**: Compliance tracking and audit trails

## Structured Logging Format

### Common Fields
All log entries include:
- **Timestamp**: ISO format with timezone
- **Event Type**: Categorization for filtering
- **Processor Info**: Version and identification
- **Correlation IDs**: For tracing across operations

### Validation Result Example
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
  "validation_status": "PASS",
  "processed_at": "2026-04-14T16:30:00Z",
  "processor": "cloud-run-validator",
  "processor_version": "1.0",
  "event_type": "file_validation"
}
```

### Batch Processing Example
```json
{
  "batch_id": "batch_abc123_20260414",
  "total_files": 50,
  "successful_files": 48,
  "failed_files": 2,
  "processing_time_ms": 15000,
  "throughput_files_per_second": 3.2,
  "success_rate_percent": 96.0,
  "event_type": "batch_complete"
}
```

## Integration Points

### Used By
- **FileValidator**: Log validation results and metrics
- **FileRouter**: Log routing operations and storage events
- **BatchFileProcessor**: Log batch processing lifecycle
- **CloudStorageManager**: Log GCS operations

### Google Cloud Logging Integration
- **Structured Logging**: Uses `extra={}` parameter for structured data
- **Log Levels**: Appropriate severity levels (INFO/ERROR)
- **Cloud Logging Format**: Compatible with GCP log viewer and alerting
- **Retention**: Follows Cloud Logging retention policies (30 days)

## Monitoring and Alerting

### Key Metrics to Monitor
- Validation failure rates by entity type
- Processing throughput and latency
- GCS operation success rates
- Batch job completion times

### Alerting Scenarios
- High validation failure rates (> 5%)
- Processing timeouts or slow performance
- GCS operation failures
- Batch job failures

### Query Examples

#### Failed Validations
```
resource.type="cloud_run_revision"
jsonPayload.validation_status="FAIL"
jsonPayload.entity_type="customers"
```

#### Batch Performance
```
resource.type="cloud_run_revision"
jsonPayload.event_type="batch_complete"
jsonPayload.success_rate_percent<95
```

## Error Handling

- **No Exceptions**: All logging methods use try-catch internally
- **Graceful Degradation**: Logging failures don't interrupt processing
- **Structured Errors**: Error messages include context and correlation IDs

## Performance Considerations

- **Minimal Overhead**: Structured logging with minimal computation
- **Async Logging**: Uses Python logging framework's async capabilities
- **Efficient Serialization**: JSON serialization for structured data
- **Resource Management**: Automatic cleanup of log resources

## Security and Compliance

- **No Sensitive Data**: Avoids logging PII or credentials
- **Audit Trail**: Provides complete processing audit trail
- **Retention Compliance**: Follows data retention policies
- **Access Control**: Inherits Cloud Logging IAM permissions