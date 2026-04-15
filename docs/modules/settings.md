# Settings Module Documentation

## Overview

The Settings module provides centralized configuration management for the file router system. It manages environment-specific settings, path configurations, and validation requirements. This module ensures consistent access to critical configuration values across the entire application.

## Purpose

- **Environment Management**: Support different environments (dev, staging, production)
- **Configuration Centralization**: Single source of truth for system settings  
- **Path Management**: Handle file system paths for schemas and resources
- **Validation**: Ensure required configurations are present and valid

## Key Components

### Constants

#### `PROJECT_ROOT`
- **Type**: `Path`
- **Description**: Base project directory path
- **Value**: `/Users/manisharora/Projects/BigQGeminiWarehouse`

#### `SCHEMAS_DIR`
- **Type**: `Path` 
- **Description**: Directory containing schema definition files
- **Value**: `{PROJECT_ROOT}/schemas`

#### `SCHEMA_FILE_PATH`
- **Type**: `str`
- **Description**: Full path to the main schema.json file
- **Value**: `{SCHEMAS_DIR}/schema.json`

#### `SUPPORTED_ENTITIES`
- **Type**: `set`
- **Description**: Set of supported entity types for validation
- **Value**: `{'customers', 'orders', 'order_items', 'products'}`

### Functions

#### `get_project_id() -> str`
- **Purpose**: Retrieve GCP project ID from environment variables
- **Returns**: Project ID string for GCP operations
- **Environment Variable**: `PROJECT_ID`
- **Error Handling**: Raises `ValueError` if `PROJECT_ID` not set
- **Usage**: Used by GCS client initialization and BigQuery operations

#### `get_schema_path() -> str`
- **Purpose**: Get schema file path for current environment
- **Returns**: Absolute path to schema.json file
- **Environment Override**: Uses `SCHEMA_FILE_PATH` env var if set
- **Fallback**: Uses default `SCHEMA_FILE_PATH` constant
- **Usage**: Schema loading in FileValidator and validation operations

#### `validate_settings()`
- **Purpose**: Validate all required settings are properly configured
- **Validation Checks**:
  - Schema file exists at specified path
  - Required environment variables are accessible
- **Error Handling**: Raises `FileNotFoundError` for missing schema file
- **Execution**: Automatically runs on module import

## Integration Points

### Used By
- **FileValidator**: Schema path configuration
- **CloudStorageManager**: Project ID for GCS client
- **BigQueryLogging**: Project ID for BigQuery operations
- **All Modules**: Entity validation against supported entities list

### Environment Variables

#### Required
- `PROJECT_ID`: GCP project identifier

#### Optional
- `SCHEMA_FILE_PATH`: Custom schema file path override

## Configuration Examples

### Development Environment
```bash
export PROJECT_ID="dev-project"
# Uses default schema path: ./schemas/schema.json
```

### Production Environment
```bash
export PROJECT_ID="prod-project"
export SCHEMA_FILE_PATH="/opt/config/schemas/production-schema.json"
```

## Error Scenarios

### Missing Project ID
```python
ValueError: PROJECT_ID environment variable is required
```

### Missing Schema File
```python
FileNotFoundError: Schema file not found: /path/to/schema.json
```

## Design Patterns

- **Singleton Configuration**: Single source of truth for settings
- **Environment-based Configuration**: Support for different deployment environments
- **Validation on Import**: Early detection of configuration issues
- **Fallback Mechanisms**: Default values with environment overrides

## Security Considerations

- Environment variables used for sensitive configuration
- No hardcoded credentials or secrets
- Path validation to prevent directory traversal

## Future Enhancements

- Support for multiple schema files
- Configuration validation for additional environments
- Runtime configuration reloading
- Configuration encryption for sensitive values