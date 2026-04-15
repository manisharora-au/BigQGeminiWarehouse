# FileRouter Module Documentation

## Overview

The FileRouter module handles routing of validated files to appropriate GCS destinations based on validation results and business rules. This module focuses purely on file routing logic without performing validation or processing, implementing intelligent file placement with Hive partitioning support and comprehensive error tracking.

## Purpose

- **File Routing**: Route files to destinations based on validation outcomes
- **Business Rules Implementation**: Apply organizational file placement policies
- **Hive Partitioning**: Generate partitioned paths for processed files
- **Error Isolation**: Route failed files for manual review and remediation
- **Performance Tracking**: Monitor routing success rates and operation timing

## Key Components

### Data Class: RoutingResult

Immutable data structure representing the complete result of a file routing operation.

**Attributes:**
- `filename` (str): Name of the routed file
- `validation_id` (str): Validation ID for correlation tracking
- `success` (bool): Whether routing operation was successful
- `source_path` (str): Original file path in inbox/
- `destination_path` (Optional[str]): Final destination path
- `routing_type` (str): Type of routing ('passed', 'failed', 'error')
- `error_message` (Optional[str]): Error details if routing failed
- `duration_ms` (int): Routing operation duration in milliseconds

### Class: FileRouter

Main routing class that implements business rules for file placement based on validation results with support for Hive partitioning and async operations.

## Routing Rules

### Validation PASS Files

#### Full Load Files
- **Destination**: `gs://bucket/processed/{entity_type}/load_type=full/filename`
- **Partitioning**: Hive-style partitioning by entity type and load type
- **Example**: `gs://my-bucket/processed/customers/load_type=full/customers_20260101.csv`

#### Delta Load Files  
- **Destination**: `gs://bucket/processed/{entity_type}/load_type=delta/date={YYYY-MM-DD}/filename`
- **Partitioning**: Hive-style partitioning by entity type, load type, and date
- **Date Format**: YYYY-MM-DD (converted from YYYYMMDD internal format)
- **Example**: `gs://my-bucket/processed/customers/load_type=delta/date=2026-01-01/batch_01_customers_delta.csv`

### Validation FAIL Files
- **Destination**: `gs://bucket/failed/filename`
- **Purpose**: Manual review and remediation
- **Retention**: Based on organizational policies
- **Example**: `gs://my-bucket/failed/invalid_customers_20260101.csv`

### File Operations
- **Strategy**: Move operations (not copy) to avoid duplication
- **Source**: All files originate from `inbox/` folder
- **Atomicity**: Single operation per file with proper error handling
- **Verification**: Post-operation verification with eventual consistency handling

## Methods

### Core Routing Methods

#### `__init__()`
- **Purpose**: Initialize FileRouter with storage manager and configuration
- **Dependencies**: CloudStorageManager instance, project settings
- **Configuration**: Uses settings module for project ID

#### `route_validated_files(bucket_name, validation_results) -> List[RoutingResult]`
- **Purpose**: Route multiple validated files concurrently to their destinations
- **Parameters**:
  - `bucket_name` (str): GCS bucket name
  - `validation_results` (List[ValidationResult]): Results from file validation
- **Process Flow**:
  1. Create routing tasks for each validation result
  2. Execute routing operations concurrently using asyncio.gather
  3. Handle exceptions and convert to RoutingResult objects
  4. Log batch routing metrics
- **Returns**: List of RoutingResult objects with operation outcomes
- **Error Handling**: Individual file failures don't stop batch processing

#### `_route_single_file(bucket_name, validation_result) -> RoutingResult`
- **Purpose**: Route individual file based on validation result
- **Parameters**:
  - `bucket_name` (str): GCS bucket name
  - `validation_result` (ValidationResult): Single file validation result
- **Process Flow**:
  1. Determine destination path based on validation outcome
  2. Execute move operation via CloudStorageManager
  3. Log GCS operation details
  4. Return RoutingResult with timing and success metrics
- **Timing**: Tracks operation duration for performance monitoring
- **Logging**: Integrates with CloudLogging for operation visibility

### Path Generation Methods

#### `_generate_processed_path(validation_result) -> str`
- **Purpose**: Generate Hive-partitioned destination path for processed files
- **Input**: ValidationResult containing metadata
- **Path Structure**: `processed/{entity_type}/year={YYYY}/month={MM}/day={DD}/filename`
- **Date Handling**:
  - Primary: Uses `file_date` from metadata (format: YYYYMMDD)
  - Fallback: Current UTC date if file_date invalid or missing
- **Entity Types**: Supports all configured entity types (customers, orders, etc.)

#### `get_expected_destination_path(validation_result) -> str`
- **Purpose**: Get expected destination path without performing routing operation
- **Use Case**: Preview routing destination for validation or testing
- **Logic**: Same as actual routing but without file operations
- **Returns**: Expected destination path string

### Metrics and Monitoring Methods

#### `_log_batch_routing_metrics(bucket_name, routing_results)`
- **Purpose**: Log comprehensive batch routing metrics for operational monitoring
- **Metrics Calculated**:
  - Total files processed
  - Successful vs failed routing operations
  - Files routed to processed/ vs failed/ destinations
  - Average routing duration
  - Success rates and error categorization
- **Integration**: Logs structured data to Cloud Logging for alerting

### Convenience Methods

#### `route_single_validated_file(bucket_name, validation_result) -> RoutingResult`
- **Purpose**: Route single file (convenience wrapper for single file operations)
- **Use Case**: Individual file processing workflows
- **Implementation**: Wrapper around `_route_single_file` with direct return

## Business Logic Implementation

### Routing Decision Matrix

| Validation Status | Load Type | Destination | Partitioning | Purpose |
|------------------|-----------|-------------|--------------|---------|
| PASS | Full | `processed/{entity_type}/load_type=full/` | Load type partitioning | Ready for processing |
| PASS | Delta | `processed/{entity_type}/load_type=delta/date={YYYY-MM-DD}/` | Load type + date partitioning | Ready for processing |
| FAIL | Any | `failed/` | Flat structure | Manual review |
| ERROR | Any | `failed/` | Flat structure | Technical remediation |

### Path Generation Examples

#### Successful Full Load Customer File
```
Input: customers_20260101.csv (PASS, load_type=full)
Output: processed/customers/load_type=full/customers_20260101.csv
```

#### Successful Delta Customer File
```
Input: batch_01_customers_delta.csv (PASS, load_type=delta, file_date=20260414)
Output: processed/customers/load_type=delta/date=2026-04-14/batch_01_customers_delta.csv
```

#### Failed Order File
```
Input: orders_20260201.csv (FAIL)
Output: failed/orders_20260201.csv
```

## Performance Characteristics

### Concurrent Operations
- **Parallelism**: Multiple files routed simultaneously using asyncio
- **Error Isolation**: Individual routing failures don't affect batch processing
- **Resource Management**: Controlled concurrency via CloudStorageManager

### Timing and Metrics
- **Operation Timing**: Millisecond precision for performance analysis
- **Throughput Tracking**: Files per second routing throughput
- **Success Rate Monitoring**: Percentage of successful routing operations

### Error Handling
- **Graceful Degradation**: Routing failures are logged but don't halt processing
- **Detailed Error Context**: Comprehensive error messages for troubleshooting
- **Retry Logic**: Inherits retry capabilities from CloudStorageManager

## Integration Points

### Dependencies
- **CloudStorageManager**: File move operations with retry logic
- **FileValidator**: ValidationResult input for routing decisions
- **CloudLogging**: Operation logging and metrics tracking
- **Settings**: Project configuration and environment settings

### Used By
- **BatchFileProcessor**: Batch file routing after validation
- **File Processing Pipelines**: End-to-end file processing workflows
- **Testing Framework**: Routing logic validation and testing

### Cloud Storage Integration
- **GCS Operations**: Move operations with atomic guarantees
- **Path Management**: Proper GCS path formatting and validation
- **Bucket Management**: Multi-bucket support with configuration

## Monitoring and Observability

### Key Metrics
- **Routing Success Rate**: Percentage of successful file routing operations
- **Average Routing Duration**: Mean time for file routing operations
- **Throughput**: Files routed per second during batch operations
- **Destination Distribution**: Ratio of processed vs failed file routing

### Logging Integration
- **Structured Logs**: JSON-formatted logs with correlation IDs
- **Error Classification**: Categorized error types for targeted alerting
- **Performance Metrics**: Operation timing and throughput data

### Alerting Scenarios
- **High Routing Failure Rate**: > 5% of routing operations failing
- **Slow Routing Performance**: Average duration exceeding thresholds
- **Storage Operation Failures**: GCS move operation errors
- **Path Generation Issues**: Invalid destination path generation

## Error Scenarios and Recovery

### Common Error Types
- **GCS Operation Failures**: Network issues, permissions, quota limits
- **Path Generation Errors**: Invalid metadata, missing date information
- **Concurrent Access Issues**: Multiple processors accessing same files
- **Storage Quota Exceeded**: Bucket storage limit reached

### Error Recovery Strategies
- **Automatic Retry**: CloudStorageManager handles transient failures
- **Error Logging**: Comprehensive error context for manual remediation
- **Graceful Degradation**: Failed routing doesn't stop batch processing
- **Manual Recovery**: Failed files can be manually moved or reprocessed

## Security and Compliance

### Access Control
- **IAM Integration**: Uses service account permissions for GCS access
- **Least Privilege**: Minimal permissions for file move operations only
- **Audit Trail**: Complete routing history via logging integration

### Data Governance
- **File Isolation**: Clear separation between processed and failed files
- **Retention Policies**: Different retention for processed vs failed files
- **Compliance Tracking**: Complete audit trail for regulatory requirements

## Configuration and Customization

### Environment Configuration
- **Project ID**: GCP project for storage operations
- **Bucket Strategy**: Configurable bucket naming and structure
- **Path Templates**: Customizable path generation patterns

### Business Rule Customization
- **Routing Logic**: Configurable routing decision matrix
- **Partitioning Strategy**: Customizable Hive partitioning schemes
- **Destination Policies**: Flexible destination path generation

## Testing and Quality Assurance

### Test Coverage
- **Unit Tests**: Individual routing method testing
- **Integration Tests**: End-to-end routing with actual GCS operations
- **Performance Tests**: Batch routing throughput and timing
- **Error Scenario Tests**: Comprehensive failure mode testing

### Validation Testing
- **Path Generation**: Verify correct Hive partitioning paths
- **Business Rules**: Validate routing decisions match expected outcomes
- **Error Handling**: Test graceful degradation and error reporting