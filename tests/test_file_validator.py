"""
Test suite for FileValidator module

Tests the FileValidator class and its validation methods using real data files
from the data/intelia-hackathon-files directory. Covers schema validation,
CSV structure checks, and error handling scenarios.

Test Categories:
1. Schema loading and validation
2. File size validation 
3. UTF-8 encoding validation
4. CSV structure validation (columns, headers, data format)
5. Integration tests with real data files
6. Error handling and edge cases

Author: Test Suite for FileValidator
Version: 1.0
"""

import pytest
import asyncio
import io
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List

# Import the modules we're testing
import sys
sys.path.append('/Users/manisharora/Projects/BigQGeminiWarehouse')

from cloud_run_batch.file_router.file_validator import FileValidator, ValidationResult
from cloud_run_batch.file_router.file_metadata_extractor import FileMetadataExtractor


class TestFileValidator:
    """Test class for FileValidator functionality"""
    
    @pytest.fixture
    def file_validator(self):
        """Create a FileValidator instance for testing"""
        return FileValidator()
    
    @pytest.fixture
    def schema_path(self):
        """Path to the schema.json file"""
        return '/Users/manisharora/Projects/BigQGeminiWarehouse/schemas/schema.json'
    
    @pytest.fixture
    def data_directory(self):
        """Path to test data directory"""
        return '/Users/manisharora/Projects/BigQGeminiWarehouse/data/intelia-hackathon-files'
    
    @pytest.fixture
    def sample_csv_content(self):
        """Sample valid CSV content for testing"""
        return """customer_id,first_name,last_name,email,phone
123,John,Doe,john@example.com,555-1234
456,Jane,Smith,jane@example.com,555-5678
789,Bob,Johnson,bob@example.com,555-9012"""
    
    @pytest.fixture
    def sample_delta_csv_content(self):
        """Sample valid delta CSV content for testing"""
        return """customer_id,first_name,last_name,email,phone,_delta_type,_batch_id,_batch_date
123,John,Doe,john@example.com,555-1234,INSERT,batch_001,2026-03-20T03:49:28Z
456,Jane,Smith,jane@example.com,555-5678,UPDATE,batch_001,2026-03-20T03:49:28Z"""
    
    # Test Schema Loading
    def test_load_schema_file_exists(self, schema_path):
        """Test loading schema from existing schema.json file"""
        schemas = FileValidator.load_schema(schema_path)
        
        # Verify schema is loaded and contains expected entities
        assert isinstance(schemas, dict)
        assert len(schemas) > 0
        
        # Check for expected entity types (both full and delta)
        expected_entities = ['customers', 'orders', 'order_items', 'products']
        for entity in expected_entities:
            assert entity in schemas, f"Entity {entity} should be in schema"
            assert f"{entity}_delta" in schemas, f"Delta entity {entity}_delta should be in schema"
    
    def test_load_schema_by_entity(self, schema_path):
        """Test loading schema for specific entity"""
        schemas = FileValidator.load_schema_by_entity(schema_path, 'customers')
        
        assert isinstance(schemas, dict)
        assert 'customers' in schemas
        assert 'customers_delta' in schemas
        
        # Verify delta schema has more columns than base schema
        base_cols = schemas['customers']
        delta_cols = schemas['customers_delta']
        assert len(delta_cols) > len(base_cols), "Delta schema should have more columns"
    
    def test_load_schema_nonexistent_file(self):
        """Test loading schema from non-existent file"""
        with pytest.raises(FileNotFoundError):
            FileValidator.load_schema('/nonexistent/schema.json')
    
    # Test File Size Validation
    @pytest.mark.asyncio
    async def test_check_file_size_valid(self):
        """Test file size validation with valid size"""
        result = await FileValidator._check_file_size(1024)  # 1KB
        assert result == (None, None), "Valid file size should pass validation"
    
    @pytest.mark.asyncio
    async def test_check_file_size_too_small(self):
        """Test file size validation with file too small"""
        check_name, error_msg = await FileValidator._check_file_size(0)
        assert check_name == 'file_size_min'
        assert 'too small' in error_msg.lower()
    
    @pytest.mark.asyncio
    async def test_check_file_size_too_large(self):
        """Test file size validation with file too large"""
        large_size = 600 * 1024 * 1024  # 600MB
        check_name, error_msg = await FileValidator._check_file_size(large_size)
        assert check_name == 'file_size_max'
        assert 'too large' in error_msg.lower()
    
    # Test UTF-8 Encoding Validation
    @pytest.mark.asyncio
    async def test_check_utf8_encoding_valid(self):
        """Test UTF-8 encoding validation with valid content"""
        valid_content = "Hello, World! 123 @#$%"
        result = await FileValidator._check_utf8_encoding(valid_content)
        assert result == (None, None), "Valid UTF-8 content should pass validation"
    
    @pytest.mark.asyncio
    async def test_check_utf8_encoding_unicode(self):
        """Test UTF-8 encoding validation with Unicode characters"""
        unicode_content = "Héllo, Wørld! 你好 🌍"
        result = await FileValidator._check_utf8_encoding(unicode_content)
        assert result == (None, None), "Unicode content should pass UTF-8 validation"
    
    # Test Non-Empty File Validation
    @pytest.mark.asyncio
    async def test_check_non_empty_file_valid(self, sample_csv_content):
        """Test non-empty file validation with valid content"""
        result = await FileValidator._check_non_empty_file(sample_csv_content)
        assert result == (None, None), "Valid CSV content should pass non-empty validation"
    
    @pytest.mark.asyncio
    async def test_check_non_empty_file_empty(self):
        """Test non-empty file validation with empty content"""
        check_name, error_msg = await FileValidator._check_non_empty_file("")
        assert check_name == 'empty_file'
        assert 'empty' in error_msg.lower()
    
    @pytest.mark.asyncio
    async def test_check_non_empty_file_only_header(self):
        """Test non-empty file validation with only header"""
        header_only = "customer_id,first_name,last_name"
        check_name, error_msg = await FileValidator._check_non_empty_file(header_only)
        assert check_name == 'insufficient_data'
        assert 'need at least 2' in error_msg
    
    # Test CSV Structure Validation
    @pytest.mark.asyncio
    async def test_check_csv_structure_valid(self, file_validator, sample_csv_content):
        """Test CSV structure validation with valid content"""
        # Mock the schema to match our sample content
        with patch.object(FileValidator, 'load_schema_by_entity') as mock_load:
            mock_load.return_value = {
                'customers': ['customer_id', 'first_name', 'last_name', 'email', 'phone']
            }
            
            errors = await file_validator._check_csv_structure(
                schema_config_path='/fake/path',
                file_content=sample_csv_content,
                entity_type='customers',
                load_type='full'
            )
            
            assert len(errors) == 0, "Valid CSV should have no structure errors"
    
    @pytest.mark.asyncio
    async def test_check_csv_structure_wrong_columns(self, file_validator, sample_csv_content):
        """Test CSV structure validation with incorrect columns"""
        with patch.object(FileValidator, 'load_schema_by_entity') as mock_load:
            # Schema expects different columns
            mock_load.return_value = {
                'customers': ['id', 'name', 'email']  # Different from sample content
            }
            
            errors = await file_validator._check_csv_structure(
                schema_config_path='/fake/path',
                file_content=sample_csv_content,
                entity_type='customers',
                load_type='full'
            )
            
            assert len(errors) > 0, "Wrong columns should generate errors"
            
            # Check for specific error types
            error_types = [error[0] for error in errors]
            assert 'column_count' in error_types or 'column_schema' in error_types
    
    @pytest.mark.asyncio
    async def test_validate_sample_data_valid(self):
        """Test sample data validation with valid rows"""
        data_rows = [
            ['123', 'John', 'Doe', 'john@example.com', '555-1234'],
            ['456', 'Jane', 'Smith', 'jane@example.com', '555-5678']
        ]
        columns = ['customer_id', 'first_name', 'last_name', 'email', 'phone']
        
        errors = await FileValidator._validate_sample_data(data_rows, columns)
        assert len(errors) == 0, "Valid data rows should have no errors"
    
    @pytest.mark.asyncio
    async def test_validate_sample_data_wrong_column_count(self):
        """Test sample data validation with wrong column count"""
        data_rows = [
            ['123', 'John', 'Doe'],  # Missing columns
            ['456', 'Jane', 'Smith', 'jane@example.com', '555-5678', 'extra']  # Extra column
        ]
        columns = ['customer_id', 'first_name', 'last_name', 'email', 'phone']
        
        errors = await FileValidator._validate_sample_data(data_rows, columns)
        assert len(errors) > 0, "Wrong column count should generate errors"
        
        # Check error message contains row information
        error_message = errors[0][1]
        assert 'Row 1' in error_message or 'Row 2' in error_message
    
    @pytest.mark.asyncio
    async def test_validate_sample_data_empty_rows(self):
        """Test sample data validation with empty rows"""
        data_rows = [
            ['123', 'John', 'Doe', 'john@example.com', '555-1234'],
            ['', '', '', '', ''],  # Empty row
        ]
        columns = ['customer_id', 'first_name', 'last_name', 'email', 'phone']
        
        errors = await FileValidator._validate_sample_data(data_rows, columns)
        assert len(errors) > 0, "Empty rows should generate errors"
        
        error_message = errors[0][1]
        assert 'empty' in error_message.lower()
    
    # Integration Tests with Real Data Files
    def test_real_data_file_structure_customers_full(self, data_directory, schema_path):
        """Test real customers file structure matches schema"""
        file_path = os.path.join(data_directory, 'customers_20260101.csv')
        if not os.path.exists(file_path):
            pytest.skip(f"Test data file not found: {file_path}")
        
        # Load schema
        schemas = FileValidator.load_schema(schema_path)
        expected_columns = schemas.get('customers', [])
        
        # Read first few lines of actual file
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            actual_columns = [col.strip() for col in first_line.split(',')]
        
        assert actual_columns == expected_columns, \
            f"Real data columns {actual_columns} don't match schema {expected_columns}"
    
    def test_real_data_file_structure_customers_delta(self, data_directory, schema_path):
        """Test real customers delta file structure matches schema"""
        file_path = os.path.join(data_directory, 'batch_01_customers_delta.csv')
        if not os.path.exists(file_path):
            pytest.skip(f"Test data file not found: {file_path}")
        
        # Load schema
        schemas = FileValidator.load_schema(schema_path)
        expected_columns = schemas.get('customers_delta', [])
        
        # Read first few lines of actual file
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            actual_columns = [col.strip() for col in first_line.split(',')]
        
        assert actual_columns == expected_columns, \
            f"Real delta data columns {actual_columns} don't match schema {expected_columns}"
    
    # Test Error Handling and Edge Cases
    @pytest.mark.asyncio
    async def test_csv_parsing_error_handling(self, file_validator):
        """Test CSV parsing with malformed content"""
        malformed_csv = 'customer_id,name\n"unclosed quote,value'
        
        with patch.object(FileValidator, 'load_schema_by_entity') as mock_load:
            mock_load.return_value = {'customers': ['customer_id', 'name']}
            
            errors = await file_validator._check_csv_structure(
                schema_config_path='/fake/path',
                file_content=malformed_csv,
                entity_type='customers',
                load_type='full'
            )
            
            # Should handle CSV parsing errors gracefully
            error_types = [error[0] for error in errors]
            assert any('csv' in error_type.lower() for error_type in error_types)
    
    def test_metadata_extraction_integration(self):
        """Test integration with FileMetadataExtractor"""
        extractor = FileMetadataExtractor()
        
        # Test various filename formats
        test_cases = [
            ('customers_20260101.csv', 'customers', 'full'),
            ('batch_01_customers_delta.csv', 'customers', 'delta'),
            ('orders_20260201.csv', 'orders', 'full'),
            ('batch_02_products_delta.csv', 'products', 'delta')
        ]
        
        for filename, expected_entity, expected_load_type in test_cases:
            metadata = extractor.extract_file_metadata(filename)
            assert metadata['entity_type'] == expected_entity, \
                f"Wrong entity type for {filename}: expected {expected_entity}, got {metadata['entity_type']}"
            assert metadata['load_type'] == expected_load_type, \
                f"Wrong load type for {filename}: expected {expected_load_type}, got {metadata['load_type']}"


# Test Configuration and Fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])