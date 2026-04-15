# CloudStorageManager Module Documentation

## Overview

The CloudStorageManager module manages Cloud Storage file operations for the data pipeline using a singleton pattern. This module handles async file operations between different GCS directories (inbox/, processed/, failed/) with comprehensive error handling, retry logic, and performance monitoring. It implements controlled concurrency to prevent overwhelming the GCS API.

## Purpose

- **Centralized Storage Operations**: Single point for all GCS file operations
- **Async File Management**: Efficient concurrent file operations with controlled parallelism
- **Error Handling**: Robust retry logic with exponential backoff for transient failures
- **Performance Optimization**: Semaphore-controlled concurrency to prevent API rate limiting
- **Operation Logging**: Comprehensive logging of all storage operations for monitoring

## Key Components

### Class: CloudStorageManager

Singleton class that provides async methods for moving files between GCS locations with proper error handling and performance monitoring.

### Design Patterns

#### Singleton Pattern Implementation
- **Purpose**: Ensure only one storage manager instance per application
- **Benefits**: Shared connection pooling, consistent concurrency control, resource efficiency
- **Implementation**: Uses `__new__` method to control instance creation
- **Thread Safety**: Singleton pattern prevents multiple concurrent storage managers

#### Async Operations
- **Concurrency Control**: Semaphore-based limiting of concurrent operations
- **Non-blocking**: Async/await pattern for efficient I/O operations
- **Error Isolation**: Individual operation failures don't affect other operations
- **Resource Management**: Proper cleanup and connection management

## Methods

### Singleton Management

#### `__new__(cls, project_id, max_concurrent_operations=10)`
- **Purpose**: Singleton pattern implementation to ensure single instance
- **Parameters**:
  - `project_id` (str): GCP project ID for storage operations
  - `max_concurrent_operations` (int): Maximum concurrent storage operations (default: 10)
- **Returns**: The singleton CloudStorageManager instance
- **Behavior**: Creates new instance only if none exists, otherwise returns existing instance

#### `__init__(self, project_id, max_concurrent_operations=10)`
- **Purpose**: Initialize the storage manager (singleton-aware)
- **Initialization**: Only runs once due to singleton pattern using `_initialized` flag
- **Components**:
  - GCS client creation with project configuration
  - Semaphore setup for concurrency control
  - Retry configuration for error handling
- **Thread Safety**: Protected initialization to prevent duplicate setup

### Core File Operations

#### `copy_file_to_destination(bucket_name, source_path, destination_path)`
- **Purpose**: Copy file from source to destination within same bucket
- **Parameters**:
  - `bucket_name` (str): GCS bucket name
  - `source_path` (str): Source file path in bucket
  - `destination_path` (str): Destination file path in bucket
- **Operation**: Creates copy without removing original file
- **Use Cases**: Backup operations, file duplication for multiple processing paths
- **Error Handling**: Comprehensive retry logic with exponential backoff

#### `move_file_from_inbox_to_destination(bucket_name, source_filename, destination_path)`
- **Purpose**: Move file from inbox/ directory to specified destination
- **Parameters**:
  - `bucket_name` (str): GCS bucket name
  - `source_filename` (str): Filename in inbox/ directory
  - `destination_path` (str): Complete destination path including filename
- **Operation Flow**:
  1. Copy file from `inbox/{source_filename}` to `destination_path`
  2. Verify copy operation succeeded
  3. Delete original file from inbox/
  4. Handle eventual consistency with polling verification
- **Atomicity**: Two-phase operation with verification and cleanup
- **Primary Use Case**: Main routing operation for validated files

#### `delete_file_from_bucket(bucket_name, file_path)`
- **Purpose**: Delete specified file from bucket
- **Parameters**:
  - `bucket_name` (str): GCS bucket name
  - `file_path` (str): Complete file path to delete
- **Safety**: Permanent deletion operation - use with caution
- **Use Cases**: Cleanup operations, removing temporary files
- **Verification**: Confirms deletion success before returning

### Advanced Operations

#### `batch_copy_validated_files(bucket_name, file_operations)`
- **Purpose**: Execute multiple copy operations concurrently
- **Parameters**:
  - `bucket_name` (str): GCS bucket name
  - `file_operations` (List[Tuple]): List of (source_path, destination_path) tuples
- **Concurrency**: Uses asyncio.gather for parallel execution
- **Error Isolation**: Individual operation failures don't stop batch processing
- **Performance**: Significantly faster than sequential operations for large batches

### Utility and Verification Methods

#### `_verify_file_exists(bucket, file_path, max_retries=3)`
- **Purpose**: Verify file exists with eventual consistency handling
- **Parameters**:
  - `bucket`: GCS bucket object
  - `file_path` (str): File path to verify
  - `max_retries` (int): Maximum verification attempts
- **Eventual Consistency**: Handles GCS eventual consistency with polling
- **Backoff Strategy**: Progressive delays between verification attempts
- **Use Case**: Verify operations completed successfully before proceeding

#### `_get_retry_config()`
- **Purpose**: Configure exponential backoff retry strategy
- **Retry Conditions**: Handles transient GCS errors (500, 503, timeout)
- **Backoff Strategy**: Exponential backoff with jitter
- **Max Attempts**: Configurable retry attempts based on error type
- **Error Classification**: Different retry strategies for different error types

## Concurrency Control

### Semaphore Management
- **Purpose**: Prevent overwhelming GCS API with too many concurrent requests
- **Default Limit**: 10 concurrent operations
- **Benefits**: Prevents rate limiting, ensures stable performance
- **Flexibility**: Configurable limit based on application requirements

### Async Operations Flow
```python
async with self.semaphore:  # Acquire semaphore slot
    # Perform GCS operation with retry logic
    # Release semaphore automatically on completion/exception
```

## Error Handling Strategy

### Retry Logic
- **Transient Errors**: Automatic retry with exponential backoff
- **Permanent Errors**: Immediate failure with detailed error reporting
- **Error Classification**:
  - Network timeouts: Retry with increasing delays
  - Rate limiting (429): Retry with exponential backoff
  - Server errors (5xx): Retry with limited attempts
  - Client errors (4xx): No retry, immediate failure

### Error Types and Responses

| Error Type | HTTP Code | Retry Strategy | Max Attempts |
|------------|-----------|----------------|--------------|
| Network Timeout | Timeout | Exponential backoff | 5 |
| Rate Limited | 429 | Exponential backoff | 3 |
| Server Error | 5xx | Exponential backoff | 3 |
| Not Found | 404 | No retry | 1 |
| Permission | 403 | No retry | 1 |
| Bad Request | 400 | No retry | 1 |

### Comprehensive Error Logging
- **Structured Logs**: JSON-formatted error details
- **Context Information**: Operation details, file paths, timing
- **Error Classification**: Clear categorization for alerting and monitoring
- **Recovery Guidance**: Actionable information for troubleshooting

## Performance Characteristics

### Operation Timing
- **Latency Tracking**: Millisecond precision timing for all operations
- **Throughput Metrics**: Operations per second for batch processing
- **Performance Logging**: Detailed timing logs for optimization

### Concurrency Benefits
- **Parallel Execution**: Multiple files processed simultaneously
- **Resource Efficiency**: Optimal utilization of network and CPU resources
- **Scalability**: Handles large batches efficiently with controlled parallelism

### GCS API Optimization
- **Connection Reuse**: Persistent client connections for efficiency
- **Batch Operations**: Grouped operations where possible
- **Rate Limit Compliance**: Respects GCS API rate limits and quotas

## Integration Points

### Dependencies
- **Google Cloud Storage**: Primary dependency for all file operations
- **CloudLogging**: Integration for operation logging and monitoring
- **Settings Module**: Configuration for project ID and environment settings

### Used By
- **FileRouter**: File movement operations for routing validated files
- **BatchFileProcessor**: Bulk file operations for batch processing
- **Archive Manager**: File archival and cleanup operations
- **Testing Framework**: Storage operations testing and verification

### Cloud Storage Integration
- **Bucket Management**: Multi-bucket support with consistent operations
- **Path Handling**: Proper GCS path formatting and validation
- **Permissions**: Service account-based authentication and authorization

## Monitoring and Observability

### Operation Metrics
- **Success Rates**: Percentage of successful storage operations
- **Average Latency**: Mean time for different operation types
- **Throughput**: Operations per second for batch processing
- **Error Rates**: Categorized error rates by type and cause

### Logging Integration
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Operation Context**: Complete context for debugging and analysis
- **Performance Data**: Timing and throughput metrics
- **Error Details**: Comprehensive error information for troubleshooting

### Alerting Scenarios
- **High Error Rates**: > 5% of operations failing
- **Slow Operations**: Average latency exceeding thresholds
- **Quota Issues**: Approaching GCS quota limits
- **Connection Problems**: Client connectivity issues

## Security and Access Control

### Authentication
- **Service Account**: Uses configured service account for GCS access
- **IAM Integration**: Leverages Google Cloud IAM for authorization
- **Least Privilege**: Minimal permissions required for file operations

### Data Security
- **In-Transit Encryption**: All operations use HTTPS/TLS
- **Access Logging**: Complete audit trail of all storage operations
- **Permission Validation**: Proper error handling for authorization failures

## Configuration Options

### Concurrency Settings
- **Max Concurrent Operations**: Configurable limit for parallel operations
- **Semaphore Management**: Dynamic adjustment based on performance requirements
- **Timeout Configuration**: Customizable timeouts for different operation types

### Retry Configuration
- **Retry Attempts**: Configurable maximum retry attempts
- **Backoff Strategy**: Customizable exponential backoff parameters
- **Error Classification**: Configurable retry policies by error type

### Environment Settings
- **Project ID**: GCP project configuration
- **Default Timeouts**: Environment-specific timeout values
- **Performance Tuning**: Environment-based performance optimization

## Testing and Validation

### Test Coverage
- **Unit Tests**: Individual method testing with mocked GCS operations
- **Integration Tests**: End-to-end testing with actual GCS operations
- **Performance Tests**: Concurrency and throughput testing
- **Error Scenario Tests**: Comprehensive failure mode testing

### Singleton Testing
- **Instance Verification**: Validate singleton pattern implementation
- **Concurrent Access**: Test thread safety and concurrent initialization
- **State Management**: Verify proper state management across operations