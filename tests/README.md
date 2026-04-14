# FileValidator Test Suite

Comprehensive test suite for the FileValidator module and related components.

## Overview

This test suite validates the critical file validation logic using real data files from `data/intelia-hackathon-files/` and comprehensive mock scenarios.

## Test Coverage

### Core Validation Methods
- ✅ `_check_file_size()` - File size validation (min/max limits)
- ✅ `_check_utf8_encoding()` - UTF-8 encoding validation  
- ✅ `_check_non_empty_file()` - Non-empty file validation
- ✅ `_check_csv_structure()` - CSV structure and schema validation
- ✅ `_validate_sample_data()` - Data format validation

### Schema Operations
- ✅ `load_schema()` - Full schema loading
- ✅ `load_schema_by_entity()` - Entity-specific schema loading
- ✅ Real data file structure validation

### Integration Tests  
- ✅ FileMetadataExtractor integration
- ✅ Real data file validation (customers, orders, products)
- ✅ Full vs Delta file format validation

### Error Handling
- ✅ Malformed CSV handling
- ✅ Wrong column count/order detection
- ✅ Empty row detection
- ✅ Schema mismatch detection

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run with Verbose Output
```bash
python tests/run_tests.py --verbose
```

### Run Specific Test
```bash
python tests/run_tests.py --specific test_file_validator.py::TestFileValidator::test_load_schema_file_exists
```

### Run with Pytest Directly
```bash
cd /Users/manisharora/Projects/BigQGeminiWarehouse
python -m pytest tests/test_file_validator.py -v
```

## Test Data

Tests use real data files from:
- `data/intelia-hackathon-files/customers_20260101.csv` (Full load)
- `data/intelia-hackathon-files/batch_01_customers_delta.csv` (Delta load)
- `data/intelia-hackathon-files/orders_20260101.csv` (Orders)
- `data/intelia-hackathon-files/products_20260101.csv` (Products)

## Test Results Interpretation

- ✅ **PASSED**: Validation logic working correctly
- ❌ **FAILED**: Issue found - check error message for details
- 🔶 **SKIPPED**: Test data file missing (non-critical)

## Dependencies

Tests require:
- `pytest` for test framework
- `pytest-asyncio` for async test support
- Real data files in `data/intelia-hackathon-files/`
- Valid `schemas/schema.json` file