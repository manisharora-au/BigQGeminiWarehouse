# FileValidator Module Documentation

## Overview

The FileValidator module performs comprehensive schema and format validation on CSV files. This module focuses purely on validation logic without routing decisions, providing detailed validation results for file processing decisions. It implements 8 different validation checks to ensure data quality and format compliance before processing.

## Purpose

- **Schema Validation**: Verify CSV structure matches expected schema definitions
- **Format Compliance**: Ensure files meet processing requirements (encoding, size, structure)
- **Data Quality Checks**: Validate data format, column counts, and content integrity
- **Error Isolation**: Provide detailed error reporting for debugging and remediation
- **Performance Optimization**: Use file sampling to minimize resource usage for large files

## Key Components

### Class: FileValidator

Main validation class that orchestrates comprehensive CSV file validation with configurable schema checks.

### Data Class: ValidationResult

Immutable data structure representing complete validation results.

**Attributes:**
- `filename` (str): Name of the validated file
- `validation_id` (str): Unique validation identifier for correlation
- `passed` (bool): Overall validation success status
- `failed_checks` (List[str]): List of failed validation check names
- `error_details` (Dict[str, str]): Detailed error information per failed check
- `metadata` (Dict[str, Optional[str]]): Extracted file metadata
- `file_size_bytes` (Optional[int]): File size in bytes

## Validation Checks (8 Total)

### 1. File Size Validation
- **Method**: `_check_file_size(file_size, min_size=1, max_size=500MB)`
- **Purpose**: Ensure file size is within acceptable processing limits
- **Checks**: Minimum 1 byte, maximum 500MB
- **Failures**: `file_size_min`, `file_size_max`

### 2. UTF-8 Encoding Validation
- **Method**: `_check_utf8_encoding(file_content_sample)`
- **Purpose**: Verify file is properly UTF-8 encoded
- **Optimization**: Uses 10KB sample for performance
- **Failures**: `utf8_encoding`

### 3. Non-Empty File Validation
- **Method**: `_check_non_empty_file(file_header_sample)`
- **Purpose**: Ensure file has header + at least one data row
- **Optimization**: Uses 2KB header sample
- **Failures**: `empty_file`, `insufficient_data`

### 4. CSV Structure Validation
- **Method**: `_check_csv_structure(file_content, entity_type, load_type)`
- **Purpose**: Validate CSV parsing, column structure, and schema compliance
- **Sub-checks**:
  - Column count validation
  - Column names and order verification
  - CSV parsing integrity
- **Failures**: `csv_parse_empty`, `column_count`, `column_schema`, `csv_format`

### 5. Sample Data Validation
- **Method**: `_validate_sample_data(data_rows, columns)`
- **Purpose**: Validate data row format consistency
- **Checks**:
  - Consistent column count across rows
  - Detection of completely empty rows
- **Optimization**: Validates all sample rows without artificial limits
- **Failures**: `data_format`

### 6. Schema Loading and Entity Validation
- **Method**: `load_schema(schema_path)`, `load_schema_by_entity(schema_path, entity)`
- **Purpose**: Load and validate against entity-specific schemas
- **Support**: Full and delta load schemas
- **Failures**: `unknown_entity_type`, `metadata_extraction`

### 7. File Existence Validation
- **Purpose**: Verify file exists in GCS bucket
- **Failures**: `file_existence`

### 8. File Access Validation
- **Purpose**: Handle file access errors and permissions
- **Failures**: `file_access`

## Methods

### Core Validation Methods

#### `__init__()`
- **Purpose**: Initialize FileValidator with schema and GCS client
- **Configuration**: Uses settings module for project ID and schema path
- **Dependencies**: Storage client, FileMetadataExtractor, schema loading

#### `validate_file(bucket_name, file_path, filename) -> ValidationResult`
- **Purpose**: Main validation orchestration method
- **Process Flow**:
  1. Generate validation ID
  2. Extract metadata from filename
  3. Verify entity type support
  4. Download file sample (5KB for headers + sample rows)
  5. Execute all validation checks
  6. Log results to Cloud Logging
  7. Return comprehensive ValidationResult
- **Performance**: Optimized with file sampling strategy
- **Error Handling**: Graceful degradation with detailed error reporting

#### `validate_batch(bucket_name, file_list) -> List[ValidationResult]`
- **Purpose**: Validate multiple files concurrently
- **Concurrency**: Uses asyncio.gather for parallel validation
- **Error Isolation**: Individual file failures don't stop batch processing
- **Exception Handling**: Converts exceptions to validation results

### Schema Management Methods

#### `load_schema(schema_path) -> Dict[str, List[str]]`
- **Purpose**: Load complete schema configuration from JSON file
- **Returns**: Mapping of entity keys to column lists
- **Schema Keys**: 
  - `entity_type` (full load columns)
  - `entity_type_delta` (full + delta columns)
- **Entities Supported**: customers, orders, order_items, products

#### `load_schema_by_entity(schema_path, target_entity) -> Dict[str, List[str]]`
- **Purpose**: Load schema for specific entity (performance optimization)
- **Returns**: Entity-specific schema mapping
- **Use Case**: Single entity validation without loading full schema

### Utility Methods

#### `generate_validation_id() -> str`
- **Purpose**: Generate unique validation identifier
- **Format**: `validation_xxxxxxxx` (8-character suffix)
- **Usage**: Correlation tracking across logging systems

## Performance Optimizations

### File Content Sampling
- **Strategy**: Download only first 5KB for validation checks
- **Benefits**: 
  - Massive memory reduction for large files
  - Improved batch processing performance
  - Maintained validation accuracy
- **Sample Allocation**:
  - UTF-8 validation: First 10KB (reduced to 2KB from sample)
  - Non-empty validation: First 2KB (reduced to 1KB from sample)
  - CSV structure: Full 5KB sample for complete header + data rows

### Static Method Optimization
- **Performance Methods**: File size, UTF-8, and non-empty validations
- **Benefits**: No instance variable access, pure function behavior
- **Memory**: Reduced memory overhead for validation operations

### Concurrent Processing
- **Batch Validation**: Parallel processing using asyncio.gather
- **Error Isolation**: Exception handling prevents cascade failures
- **Resource Management**: Controlled concurrency with proper cleanup

## Integration Points

### Used By
- **BatchFileProcessor**: Batch validation operations
- **FileRouter**: Validation results for routing decisions
- **Cloud Functions**: Single file validation workflows
- **Testing Framework**: Comprehensive validation testing

### Dependencies
- **Settings Module**: Configuration and project settings
- **CloudLogging**: Validation result logging and correlation
- **FileMetadataExtractor**: Filename parsing and metadata extraction
- **Google Cloud Storage**: File access and content retrieval

### Schema Integration
- **Schema File**: `schemas/schema.json`
- **Entity Support**: Configurable via `settings.SUPPORTED_ENTITIES`
- **Schema Evolution**: Support for schema updates and versioning

## Error Handling

### Validation Failure Types
- **Schema Mismatches**: Wrong columns, incorrect order, missing entities
- **Format Issues**: Invalid CSV, encoding problems, empty files
- **Size Constraints**: Files too large or too small for processing
- **Access Issues**: File not found, permission errors, GCS failures

### Error Reporting Structure
```python
ValidationResult(
    filename="customers_20260101.csv",
    validation_id="validation_a3f9c2d1",
    passed=False,
    failed_checks=["column_count", "utf8_encoding"],
    error_details={
        "column_count": "Expected 21 columns, found 19",
        "utf8_encoding": "Invalid UTF-8 sequence at byte 1024"
    },
    metadata={"entity_type": "customers", "load_type": "full"},
    file_size_bytes=1048576
)
```

### Comprehensive Error Context
- **Validation ID**: Unique identifier for error correlation
- **Specific Check Names**: Precise failure identification
- **Detailed Messages**: Actionable error descriptions
- **File Context**: Metadata and size information for debugging

## Configuration

### Environment Variables
- `PROJECT_ID`: GCP project for storage client
- `SCHEMA_FILE_PATH`: Custom schema file location (optional)

### Settings Integration
- **Schema Path**: Configurable schema file location
- **Supported Entities**: Configurable entity validation list
- **Project Configuration**: Environment-based project settings

### Schema Configuration Example
```json
{
  "tables": {
    "customers": {
      "columns": [
        {"name": "customer_id"},
        {"name": "first_name"},
        {"name": "last_name"}
      ],
      "delta_columns": [
        {"name": "_delta_type"},
        {"name": "_batch_id"},
        {"name": "_batch_date"}
      ]
    }
  }
}
```

## Testing and Quality Assurance

### Test Coverage
- **Unit Tests**: Individual validation method testing
- **Integration Tests**: End-to-end validation with real data files
- **Performance Tests**: Large file handling and batch processing
- **Error Scenario Tests**: Comprehensive failure mode testing

### Real Data Validation
- **Test Files**: Uses actual data from `data/intelia-hackathon-files/`
- **Schema Compliance**: Validates real files against production schema
- **Format Verification**: Ensures validation logic works with actual data patterns

## Security Considerations

### Data Privacy
- **Content Sampling**: Only reads file headers and sample data
- **No Content Storage**: Validation results contain metadata only
- **Temporary Data**: File content samples are not persisted

### Access Control
- **GCS Permissions**: Uses service account for secure file access
- **Schema Security**: Schema files stored in secure project locations
- **Audit Trail**: Complete validation history via logging integration