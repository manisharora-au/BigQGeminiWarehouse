# FileMetadataExtractor Module Documentation

## Overview

The FileMetadataExtractor module handles extraction of metadata from various filename patterns for the data pipeline. This module provides methods to parse different file naming conventions and extract relevant metadata for downstream processing, supporting both full and delta load patterns with comprehensive validation.

## Purpose

- **Filename Pattern Recognition**: Parse structured filenames to extract business metadata
- **Entity Type Identification**: Determine data entity types (customers, orders, etc.)
- **Load Type Classification**: Distinguish between full and delta load patterns
- **Date Extraction**: Extract dates from filenames or generate current dates for delta files
- **Batch ID Management**: Generate and format batch identifiers for delta processing
- **Validation Support**: Ensure extracted metadata meets system requirements

## Supported Filename Patterns

### Pattern 1: Full Load Files
- **Format**: `{entity}_{YYYYMMDD}.csv`
- **Examples**:
  - `customers_20260101.csv`
  - `orders_20260201.csv`
  - `order_items_20260301.csv`
  - `products_20260401.csv`
- **Characteristics**:
  - Contains explicit date in filename
  - Date format: YYYYMMDD (8 digits)
  - Load type: `full`
  - No batch ID component

### Pattern 2: Delta Load Files
- **Format**: `batch_{XX}_{entity}_delta.csv`
- **Examples**:
  - `batch_01_customers_delta.csv`
  - `batch_02_orders_delta.csv`
  - `batch_03_order_items_delta.csv`
- **Characteristics**:
  - No explicit date in filename (uses current date)
  - Batch number: numeric (1, 2, 3, etc.)
  - Load type: `delta`
  - Formatted batch ID: `batch_001`, `batch_002`, etc.

## Key Components

### Class: FileMetadataExtractor

Static utility class providing methods for filename parsing and metadata extraction.

### Supported Entities

Based on `settings.SUPPORTED_ENTITIES`:
- `customers`
- `orders`
- `order_items`
- `products`

## Methods

### Core Extraction Methods

#### `extract_file_metadata(filename) -> Dict[str, Optional[str]]`
- **Purpose**: Main method to extract metadata from filename patterns
- **Parameters**:
  - `filename` (str): Source filename to parse (with or without .csv extension)
- **Returns**: Dictionary containing extracted metadata with standardized keys
- **Process Flow**:
  1. Remove .csv extension and normalize to lowercase
  2. Apply regex patterns for full and delta load recognition
  3. Validate entity type against supported entities
  4. Extract or generate date information
  5. Format batch IDs with zero-padding
  6. Return structured metadata dictionary

#### Output Structure
```python
{
    'entity_type': str,           # customers, orders, order_items, products
    'load_type': str,             # full, delta
    'batch_id': Optional[str],    # batch_001, batch_002 (delta only)
    'file_date': str,             # YYYYMMDD format
    'original_filename': str      # Original filename for audit trail
}
```

### Validation Methods

#### `validate_entity_type(entity_type) -> bool`
- **Purpose**: Validate if extracted entity type is supported
- **Parameters**:
  - `entity_type` (str): Entity type to validate
- **Returns**: `True` if supported, `False` otherwise
- **Use Case**: Additional validation after metadata extraction

#### `get_supported_entities() -> set`
- **Purpose**: Get set of supported entity types
- **Returns**: Copy of supported entities set
- **Use Case**: Dynamic validation and system configuration queries

## Pattern Matching Logic

### Regular Expression Patterns

#### Full Load Pattern
```python
full_pattern = r'^([a-z_]+)_(\d{8})$'
```
- **Group 1**: Entity type (letters and underscores)
- **Group 2**: Date (exactly 8 digits)
- **Examples**: `customers_20260101`, `order_items_20260201`

#### Delta Load Pattern
```python
delta_pattern = r'^batch_(\d+)_([a-z_]+)_delta$'
```
- **Group 1**: Batch number (numeric)
- **Group 2**: Entity type (letters and underscores)
- **Examples**: `batch_01_customers_delta`, `batch_123_orders_delta`

### Pattern Matching Process
1. **Case Normalization**: Convert filename to lowercase for consistent matching
2. **Extension Removal**: Strip .csv extension before pattern matching
3. **Sequential Matching**: Try full load pattern first, then delta pattern
4. **Entity Validation**: Verify extracted entity against supported entities list
5. **Metadata Population**: Build complete metadata structure

## Date Handling Strategy

### Full Load Files
- **Source**: Date extracted directly from filename
- **Format**: YYYYMMDD (8 digits)
- **Validation**: Regex ensures exactly 8 numeric characters
- **Usage**: Used for Hive partitioning in processed/ directory

### Delta Load Files
- **Source**: Current UTC date (no date in filename)
- **Generation**: `datetime.now(timezone.utc).strftime('%Y%m%d')`
- **Rationale**: Delta files represent incremental changes for current processing date
- **Usage**: Used for Hive partitioning based on processing date

## Batch ID Management

### Format Standardization
- **Input**: Raw batch number from filename (e.g., "1", "23", "456")
- **Processing**: Zero-padding using `batch_num.zfill(3)`
- **Output**: Standardized format (e.g., "batch_001", "batch_023", "batch_456")
- **Benefits**: Consistent sorting and identification across systems

### Examples
| Filename | Extracted Batch | Formatted Batch ID |
|----------|----------------|-------------------|
| `batch_1_customers_delta.csv` | "1" | "batch_001" |
| `batch_23_orders_delta.csv` | "23" | "batch_023" |
| `batch_456_products_delta.csv` | "456" | "batch_456" |

## Metadata Examples

### Full Load Example
```python
# Input: "customers_20260101.csv"
{
    'entity_type': 'customers',
    'load_type': 'full',
    'batch_id': None,
    'file_date': '20260101',
    'original_filename': 'customers_20260101.csv'
}
```

### Delta Load Example
```python
# Input: "batch_01_customers_delta.csv" (processed on 2026-04-14)
{
    'entity_type': 'customers',
    'load_type': 'delta',
    'batch_id': 'batch_001',
    'file_date': '20260414',
    'original_filename': 'batch_01_customers_delta.csv'
}
```

### Unrecognized Pattern Example
```python
# Input: "invalid_filename.csv"
{
    'entity_type': None,
    'load_type': None,
    'batch_id': None,
    'file_date': None,
    'original_filename': 'invalid_filename.csv'
}
```

## Error Handling and Edge Cases

### Unsupported Patterns
- **Behavior**: Returns metadata structure with null values
- **Logging**: Warning message for unrecognized patterns
- **Downstream**: FileValidator catches and handles invalid metadata

### Entity Type Validation
- **Unsupported Entities**: Rejected even if pattern matches
- **Case Sensitivity**: Handled through lowercase normalization
- **Underscore Support**: Entity types with underscores (order_items) supported

### Date Format Validation
- **Full Loads**: Regex ensures exactly 8 digits (YYYYMMDD)
- **Invalid Dates**: Pattern matching prevents invalid date formats
- **Delta Loads**: Generated dates always valid (current UTC)

## Integration Points

### Used By
- **FileValidator**: Metadata validation during file processing
- **FileRouter**: Entity-based routing and Hive partitioning
- **BatchFileProcessor**: Batch processing coordination
- **Testing Framework**: Filename pattern validation testing

### Dependencies
- **Settings Module**: Configuration for supported entities
- **Python Standard Library**: Regex, datetime functionality
- **Logging Framework**: Structured logging for debugging and monitoring

### Configuration Integration
- **Supported Entities**: Dynamically loaded from settings module
- **Environment Flexibility**: Entity support configurable per environment
- **Extension Support**: Easy addition of new entity types

## Logging and Monitoring

### Information Logging
- **Pattern Matching**: Successful pattern recognition events
- **Entity Extraction**: Detailed entity and date extraction logging
- **Validation Results**: Entity type validation outcomes

### Warning Logging
- **Unrecognized Patterns**: Files that don't match any supported pattern
- **Unsupported Entities**: Valid patterns with unsupported entity types
- **Processing Issues**: Any metadata extraction problems

### Debug Information
- **Regex Details**: Detailed pattern matching information
- **Metadata Assembly**: Step-by-step metadata construction
- **Edge Case Handling**: Special case processing details

## Performance Considerations

### Regex Optimization
- **Compiled Patterns**: Patterns compiled once for reuse
- **Efficient Matching**: Sequential pattern matching stops on first match
- **Minimal Backtracking**: Simple, direct patterns without complex alternation

### Memory Management
- **Static Methods**: No instance state, minimal memory overhead
- **Immediate Return**: Early return on successful pattern match
- **String Operations**: Efficient string processing with minimal copying

## Testing and Validation

### Test Coverage Areas
- **Pattern Recognition**: All supported filename patterns
- **Edge Cases**: Invalid patterns, unsupported entities, malformed filenames
- **Date Handling**: Date extraction and current date generation
- **Batch ID Formatting**: Zero-padding and format consistency

### Validation Testing
- **Real Filenames**: Testing with actual production filename patterns
- **Error Scenarios**: Comprehensive testing of failure modes
- **Entity Support**: Validation of all supported entity types

## Future Enhancements

### Pattern Extension
- **New Patterns**: Support for additional filename conventions
- **Flexible Dating**: Support for different date formats
- **Versioning Support**: Filename versioning for reprocessing scenarios

### Metadata Enrichment
- **Additional Fields**: More metadata extraction from filenames
- **Validation Rules**: Enhanced validation for specific entity types
- **Custom Extractors**: Entity-specific metadata extraction logic