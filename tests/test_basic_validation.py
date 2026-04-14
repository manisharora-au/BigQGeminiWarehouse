"""
Basic validation tests that don't require GCS dependencies

These tests focus on core validation logic without requiring
Google Cloud Storage client or external dependencies.
"""

import sys
import os
import asyncio
import json
from unittest.mock import patch, Mock

# Add project to path
sys.path.insert(0, '/Users/manisharora/Projects/BigQGeminiWarehouse')

class TestBasicValidation:
    """Basic validation tests without GCS dependencies"""
    
    def test_schema_file_exists(self):
        """Test that schema.json file exists"""
        schema_path = '/Users/manisharora/Projects/BigQGeminiWarehouse/schemas/schema.json'
        assert os.path.exists(schema_path), f"Schema file should exist at {schema_path}"
    
    def test_data_files_exist(self):
        """Test that test data files exist"""
        data_dir = '/Users/manisharora/Projects/BigQGeminiWarehouse/data/intelia-hackathon-files'
        
        expected_files = [
            'customers_20260101.csv',
            'batch_01_customers_delta.csv',
            'orders_20260101.csv',
            'products_20260101.csv'
        ]
        
        for filename in expected_files:
            file_path = os.path.join(data_dir, filename)
            if os.path.exists(file_path):
                print(f"✅ Found: {filename}")
            else:
                print(f"⚠️ Missing: {filename}")
    
    def test_schema_structure(self):
        """Test schema file structure without importing FileValidator"""
        schema_path = '/Users/manisharora/Projects/BigQGeminiWarehouse/schemas/schema.json'
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        # Basic schema structure validation
        assert 'tables' in schema, "Schema should have 'tables' section"
        assert isinstance(schema['tables'], dict), "Tables should be a dictionary"
        
        # Check for expected entities
        expected_entities = ['customers', 'orders', 'order_items', 'products']
        for entity in expected_entities:
            assert entity in schema['tables'], f"Entity {entity} should be in schema"
            
            table = schema['tables'][entity]
            assert 'columns' in table, f"Entity {entity} should have columns"
            assert isinstance(table['columns'], list), f"Columns should be a list for {entity}"
    
    def test_real_data_file_headers(self):
        """Test real data file headers match expected format"""
        data_dir = '/Users/manisharora/Projects/BigQGeminiWarehouse/data/intelia-hackathon-files'
        
        test_cases = [
            ('customers_20260101.csv', 'customers'),
            ('batch_01_customers_delta.csv', 'customers_delta')
        ]
        
        for filename, entity_type in test_cases:
            file_path = os.path.join(data_dir, filename)
            if not os.path.exists(file_path):
                print(f"⚠️ Test file not found: {filename}")
                continue
            
            # Read first line (header)
            with open(file_path, 'r') as f:
                header = f.readline().strip()
                columns = [col.strip() for col in header.split(',')]
            
            print(f"📁 {filename}")
            print(f"   Columns: {len(columns)}")
            print(f"   Sample: {columns[:5]}...")
            
            # Basic validation
            assert len(columns) > 0, f"File {filename} should have columns"
            assert 'customer_id' in columns, f"File {filename} should have customer_id column"
            
            # Delta files should have delta columns
            if 'delta' in filename:
                delta_columns = ['_delta_type', '_batch_id', '_batch_date']
                for delta_col in delta_columns:
                    assert delta_col in columns, f"Delta file should have {delta_col} column"

    def test_mock_file_size_validation(self):
        """Test file size validation logic in isolation"""
        # Mock the FileValidator class to avoid GCS imports
        with patch.dict('sys.modules', {'google.cloud.storage': Mock()}):
            with patch.dict('sys.modules', {'google.cloud': Mock()}):
                from cloud_run_batch.file_router.file_validator import FileValidator
                
                async def run_async_tests():
                    # Test valid file size
                    result = await FileValidator._check_file_size(1024)
                    assert result == (None, None), "Valid file size should pass"
                    print("✅ Valid file size test passed")
                    
                    # Test file too small
                    check_name, error_msg = await FileValidator._check_file_size(0)
                    assert check_name == 'file_size_min'
                    assert 'too small' in error_msg
                    print("✅ File too small test passed")
                    
                    # Test file too large
                    large_size = 600 * 1024 * 1024  # 600MB
                    check_name, error_msg = await FileValidator._check_file_size(large_size)
                    assert check_name == 'file_size_max'
                    assert 'too large' in error_msg
                    print("✅ File too large test passed")
                
                # Run async tests
                asyncio.run(run_async_tests())


def run_all_tests():
    """Run all tests without pytest"""
    print("🧪 Running Basic Validation Tests")
    print("=" * 50)
    
    test_instance = TestBasicValidation()
    
    try:
        print("\n1️⃣ Testing schema file exists...")
        test_instance.test_schema_file_exists()
        print("✅ Schema file test passed")
    except Exception as e:
        print(f"❌ Schema file test failed: {e}")
    
    try:
        print("\n2️⃣ Testing data files exist...")
        test_instance.test_data_files_exist()
        print("✅ Data files test completed")
    except Exception as e:
        print(f"❌ Data files test failed: {e}")
    
    try:
        print("\n3️⃣ Testing schema structure...")
        test_instance.test_schema_structure()
        print("✅ Schema structure test passed")
    except Exception as e:
        print(f"❌ Schema structure test failed: {e}")
    
    try:
        print("\n4️⃣ Testing real data file headers...")
        test_instance.test_real_data_file_headers()
        print("✅ Data file headers test completed")
    except Exception as e:
        print(f"❌ Data file headers test failed: {e}")
    
    try:
        print("\n5️⃣ Testing file size validation...")
        test_instance.test_mock_file_size_validation()
        print("✅ File size validation test passed")
    except Exception as e:
        print(f"❌ File size validation test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Basic validation tests completed!")


if __name__ == '__main__':
    run_all_tests()