# File Router Modules Documentation

## Overview

This directory contains comprehensive documentation for all modules in the `cloud_run_batch/file_router` system. The file router system implements a scalable, cloud-native data pipeline for processing and validating CSV files with comprehensive error handling, governance logging, and performance optimization.

## Architecture Overview

The file router system follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   main.py       │    │ batch_job_mgr.py │    │ batch_processor │
│  (Entry Point)  │───▶│  (Job Lifecycle) │───▶│  (Orchestrator) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       ▼                                 ▼                                 ▼
            ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
            │ file_validator  │              │  file_router    │              │ storage_manager │
            │   (Validation)  │              │   (Routing)     │              │ (GCS Operations)│
            └─────────────────┘              └─────────────────┘              └─────────────────┘
                       │                             │                                 │
                       └─────────────────────────────┼─────────────────────────────────┘
                                                     ▼
                       ┌─────────────────────────────────────────────────────────────────────┐
                       │                    Supporting Modules                                 │
                       ├─────────────────┬─────────────────┬─────────────────┬─────────────────┤
                       │  cloud_logging  │bigquery_logging │file_metadata_   │    settings     │
                       │   (Real-time)   │  (Governance)   │   extractor     │ (Configuration) │
                       └─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

## Module Documentation

### Core Processing Modules

#### [Settings](settings.md) 📚
**Purpose**: Centralized configuration management  
**Key Features**: Environment-based configuration, schema path management, validation  
**Status**: ✅ Implemented and Documented

#### [FileValidator](file_validator.md) 🔍
**Purpose**: Comprehensive CSV file validation with 8 different checks  
**Key Features**: Schema validation, format checking, performance optimization  
**Status**: ✅ Implemented and Documented

#### [FileRouter](file_router.md) 🚛
**Purpose**: Route validated files based on business rules  
**Key Features**: Hive partitioning, concurrent routing, error isolation  
**Status**: ✅ Implemented and Documented

#### [CloudStorageManager](cloud_storage_manager.md) ☁️
**Purpose**: Centralized GCS operations with retry logic  
**Key Features**: Singleton pattern, async operations, concurrency control  
**Status**: ✅ Implemented and Documented

#### [FileMetadataExtractor](file_metadata_extractor.md) 🏷️
**Purpose**: Extract metadata from filename patterns  
**Key Features**: Pattern recognition, entity validation, date handling  
**Status**: ✅ Implemented and Documented

### Logging and Monitoring Modules

#### [CloudLogging](cloud_logging.md) 📊
**Purpose**: Real-time operational monitoring via Google Cloud Logging  
**Key Features**: Structured logging, correlation tracking, alerting support  
**Status**: ✅ Implemented and Documented

#### [BigQueryLogging](bigquery_logging.md) 📈
**Purpose**: Long-term governance data persistence to BigQuery  
**Key Features**: Batch operations, audit trails, compliance tracking  
**Status**: ✅ Implemented and Documented

### Orchestration Modules (Pending Implementation)

#### BatchFileProcessor 🔄
**Purpose**: Concurrent processing coordination  
**Key Features**: Batch validation, routing coordination, metrics collection  
**Status**: ⚠️ Pending Implementation

#### BatchJobManager 🎯
**Purpose**: Job lifecycle management  
**Key Features**: Job scheduling, health monitoring, resource allocation  
**Status**: ⚠️ Pending Implementation

#### Main Entry Point 🚀
**Purpose**: Orchestrator entry point for Cloud Run  
**Key Features**: HTTP request handling, job initiation, error responses  
**Status**: ⚠️ Pending Implementation

## Data Flow Architecture

### File Processing Pipeline

```
📁 GCS Inbox/
    │
    ▼ (1) File Discovery
📋 FileMetadataExtractor
    │ ┌─ Entity Type
    │ ├─ Load Type (Full/Delta)
    │ ├─ Batch ID
    │ └─ File Date
    ▼
🔍 FileValidator (8 Validation Checks)
    │ ┌─ File Size       ├─ UTF-8 Encoding
    │ ├─ Non-Empty       ├─ CSV Structure
    │ ├─ Column Count    ├─ Column Names
    │ ├─ Column Order    └─ Data Format
    ▼
🚛 FileRouter (Business Rules)
    ├─ PASS ──▶ 📂 processed/{entity}/year={Y}/month={M}/day={D}/
    └─ FAIL ──▶ 📂 failed/
```

### Logging Architecture

```
📝 Real-time Monitoring (Cloud Logging)
    ├─ Validation Results      ├─ Processing Metrics
    ├─ Routing Operations      ├─ Storage Operations
    └─ Batch Processing Stats
    
📊 Governance & Audit (BigQuery)
    ├─ governance.validation_log     (Individual file results)
    └─ governance.batch_processing   (Batch job metrics)
```

## Key Design Patterns

### 1. Singleton Pattern
- **Module**: CloudStorageManager
- **Purpose**: Ensure single instance for resource management
- **Benefits**: Connection pooling, consistent concurrency control

### 2. Factory Pattern
- **Module**: FileValidator, FileRouter
- **Purpose**: Create validation and routing strategies
- **Benefits**: Flexible configuration, extensible design

### 3. Observer Pattern
- **Module**: CloudLogging, BigQueryLogging
- **Purpose**: Decouple logging from core processing
- **Benefits**: Multiple logging destinations, clean separation

### 4. Strategy Pattern
- **Module**: FileMetadataExtractor
- **Purpose**: Different extraction strategies for filename patterns
- **Benefits**: Easy addition of new filename patterns

## Performance Optimizations

### File Processing
- **Sampling Strategy**: 5KB file samples instead of full content download
- **Concurrent Processing**: Async operations with controlled parallelism
- **Resource Management**: Semaphore-controlled concurrency limits

### Storage Operations
- **Connection Reuse**: Persistent GCS client connections
- **Batch Operations**: Grouped operations for efficiency
- **Retry Logic**: Exponential backoff for transient failures

### Logging Performance
- **Structured Logging**: Efficient JSON serialization
- **Batch Inserts**: BigQuery batch operations for governance data
- **Async Operations**: Non-blocking logging operations

## Security and Compliance

### Data Security
- **In-Transit Encryption**: All operations use HTTPS/TLS
- **No Content Storage**: Validation results contain metadata only
- **Access Control**: IAM-based permissions for all operations

### Compliance Features
- **Complete Audit Trail**: Every file operation logged
- **Data Governance**: BigQuery persistence for regulatory compliance
- **Error Tracking**: Comprehensive error context for troubleshooting

### Privacy Protection
- **No PII Storage**: System stores metadata, not content
- **Temporary Processing**: File samples not persisted
- **Secure Configuration**: Environment-based secret management

## Testing Strategy

### Test Coverage by Module
- **Unit Tests**: Individual method testing with mocks
- **Integration Tests**: End-to-end testing with real GCS operations
- **Performance Tests**: Concurrent processing and throughput validation
- **Error Scenario Tests**: Comprehensive failure mode testing

### Real Data Testing
- **Test Data**: Uses actual files from `data/intelia-hackathon-files/`
- **Schema Validation**: Tests against production schema definitions
- **Pattern Testing**: Validates filename pattern recognition

## Monitoring and Alerting

### Key Metrics
- **Validation Success Rate**: Percentage of files passing validation
- **Processing Throughput**: Files processed per second
- **Error Rates**: Categorized by failure type and entity
- **Storage Operation Success**: GCS operation success rates

### Alerting Scenarios
- **High Failure Rates**: > 5% validation or routing failures
- **Performance Degradation**: Processing time exceeding thresholds
- **Storage Issues**: GCS operation failures or quota issues
- **System Health**: Overall pipeline health and availability

## Getting Started

### Prerequisites
- Google Cloud Storage access with appropriate IAM permissions
- BigQuery dataset for governance logging
- Cloud Logging enabled for operational monitoring
- Python 3.12+ with required dependencies

### Configuration
1. Set environment variables: `PROJECT_ID`
2. Configure schema file path (optional): `SCHEMA_FILE_PATH`
3. Ensure GCS bucket structure: `inbox/`, `processed/`, `failed/`
4. Create BigQuery governance tables

### Running Tests
```bash
# Run all tests
python tests/run_tests.py

# Run specific module tests  
python tests/test_basic_validation.py

# Run with verbose output
python tests/run_tests.py --verbose
```

## Future Enhancements

### Planned Features
- Enhanced error recovery mechanisms
- Multi-tenant support for different organizations
- Real-time processing mode for low-latency requirements
- Advanced data quality rules and custom validation

### Scalability Improvements
- Horizontal scaling with multiple Cloud Run instances
- Advanced load balancing and request routing
- Optimized batch size management based on file characteristics
- Enhanced monitoring and auto-scaling capabilities

## Contributing

When contributing to this system:
1. Follow the established patterns and conventions
2. Update documentation for any new features or changes
3. Include comprehensive test coverage
4. Ensure security and compliance requirements are met
5. Update this overview documentation for structural changes