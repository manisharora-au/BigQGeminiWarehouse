"""
Simple test to show validation outputs with real examples

This test uses static methods and simple scenarios to show validation
results including validation_id, error messages, and detailed outputs.
"""

import sys
import asyncio
import json
from unittest.mock import Mock, patch

# Add project to path
sys.path.insert(0, '/Users/manisharora/Projects/BigQGeminiWarehouse')

async def test_validation_methods_directly():
    """Test validation methods directly to see their outputs"""
    
    print("🧪 Testing Validation Methods Directly")
    print("=" * 70)
    
    # Mock dependencies to import FileValidator
    with patch.dict('sys.modules', {'google.cloud.storage': Mock()}):
        with patch.dict('sys.modules', {'google.cloud': Mock()}):
            from cloud_run_batch.file_router.file_validator import FileValidator
            from cloud_run_batch.file_router.cloud_logging import CloudLogging
            
            print("📋 TEST: Validation ID Generation")
            print("-" * 50)
            
            # Generate validation IDs
            validation_ids = []
            for i in range(3):
                vid = CloudLogging.generate_validation_id()
                validation_ids.append(vid)
                print(f"Generated ID {i+1}: {vid}")
            
            print(f"✅ All IDs unique: {len(set(validation_ids)) == 3}")
            print(f"✅ Correct format: {all(v.startswith('validation_') and len(v) == 19 for v in validation_ids)}")
            
            print("\n📋 TEST: File Size Validation")
            print("-" * 50)
            
            # Test file size validation
            test_cases = [
                (1024, "Valid 1KB file"),
                (0, "Empty file"),
                (600 * 1024 * 1024, "600MB file (too large)"),
                (500 * 1024 * 1024, "500MB file (at limit)")
            ]
            
            for size, description in test_cases:
                result = await FileValidator._check_file_size(size)
                check_name, error_msg = result
                
                if check_name is None:
                    print(f"✅ {description}: PASSED")
                else:
                    print(f"❌ {description}: FAILED")
                    print(f"   Check: {check_name}")
                    print(f"   Error: {error_msg}")
            
            print("\n📋 TEST: UTF-8 Encoding Validation")
            print("-" * 50)
            
            utf8_test_cases = [
                ("Hello, World! 123", "Simple ASCII"),
                ("Héllo, Wørld! 你好 🌍", "Unicode characters"),
                ("customer_id,name,email\n123,John,john@test.com", "CSV content"),
            ]
            
            for content, description in utf8_test_cases:
                result = await FileValidator._check_utf8_encoding(content)
                check_name, error_msg = result
                
                if check_name is None:
                    print(f"✅ {description}: PASSED")
                else:
                    print(f"❌ {description}: FAILED - {error_msg}")
            
            print("\n📋 TEST: Non-Empty File Validation")
            print("-" * 50)
            
            content_test_cases = [
                ("customer_id,name,email\n123,John,john@test.com", "Valid CSV with data"),
                ("customer_id,name,email", "Header only"),
                ("", "Empty content"),
                ("   \n  \n  ", "Whitespace only"),
            ]
            
            for content, description in content_test_cases:
                result = await FileValidator._check_non_empty_file(content)
                check_name, error_msg = result
                
                if check_name is None:
                    print(f"✅ {description}: PASSED")
                else:
                    print(f"❌ {description}: FAILED")
                    print(f"   Check: {check_name}")
                    print(f"   Error: {error_msg}")
            
            print("\n📋 TEST: Sample Data Validation")
            print("-" * 50)
            
            # Test sample data validation
            valid_data = [
                ['123', 'John', 'Doe', 'john@test.com', '555-0123'],
                ['456', 'Jane', 'Smith', 'jane@test.com', '555-0456']
            ]
            columns = ['customer_id', 'first_name', 'last_name', 'email', 'phone']
            
            result = await FileValidator._validate_sample_data(valid_data, columns)
            
            print("Valid data rows:")
            for i, row in enumerate(valid_data, 1):
                print(f"  Row {i}: {row}")
            
            if len(result) == 0:
                print("✅ Sample data validation: PASSED")
            else:
                print("❌ Sample data validation: FAILED")
                for check_name, error_msg in result:
                    print(f"   Check: {check_name}")
                    print(f"   Error: {error_msg}")
            
            # Test invalid data
            print("\nTesting invalid data (wrong column count):")
            invalid_data = [
                ['123', 'John', 'Doe'],  # Missing columns
                ['456', 'Jane', 'Smith', 'jane@test.com', '555-0456', 'extra']  # Extra column
            ]
            
            result = await FileValidator._validate_sample_data(invalid_data, columns)
            
            print("Invalid data rows:")
            for i, row in enumerate(invalid_data, 1):
                print(f"  Row {i}: {row} (expected {len(columns)} columns, got {len(row)})")
            
            if len(result) == 0:
                print("✅ Invalid data validation: UNEXPECTEDLY PASSED")
            else:
                print("✅ Invalid data validation: CORRECTLY FAILED")
                for check_name, error_msg in result:
                    print(f"   Check: {check_name}")
                    print(f"   Error: {error_msg}")


def test_schema_loading():
    """Test schema loading and show the results"""
    
    print("\n📋 TEST: Schema Loading")
    print("-" * 50)
    
    # Mock dependencies for FileValidator import
    with patch.dict('sys.modules', {'google.cloud.storage': Mock()}):
        with patch.dict('sys.modules', {'google.cloud': Mock()}):
            from cloud_run_batch.file_router.file_validator import FileValidator
            
            schema_path = '/Users/manisharora/Projects/BigQGeminiWarehouse/schemas/schema.json'
            
            try:
                # Test full schema loading
                print("Loading full schema...")
                schemas = FileValidator.load_schema(schema_path)
                
                print(f"✅ Schema loaded successfully: {len(schemas)} entity schemas")
                
                for entity_key, columns in schemas.items():
                    entity_type = "DELTA" if entity_key.endswith('_delta') else "FULL"
                    base_entity = entity_key.replace('_delta', '')
                    print(f"   {base_entity} ({entity_type}): {len(columns)} columns")
                
                # Test entity-specific schema loading
                print("\nLoading entity-specific schema for 'customers'...")
                customer_schemas = FileValidator.load_schema_by_entity(schema_path, 'customers')
                
                print(f"✅ Customer schemas loaded: {len(customer_schemas)} variants")
                
                if 'customers' in customer_schemas:
                    print(f"   Full customers schema: {len(customer_schemas['customers'])} columns")
                    print(f"   Sample columns: {customer_schemas['customers'][:5]}...")
                
                if 'customers_delta' in customer_schemas:
                    print(f"   Delta customers schema: {len(customer_schemas['customers_delta'])} columns")
                    delta_only_cols = [col for col in customer_schemas['customers_delta'] 
                                     if col not in customer_schemas['customers']]
                    print(f"   Delta-only columns: {delta_only_cols}")
                
            except Exception as e:
                print(f"❌ Schema loading failed: {e}")


def test_metadata_extraction():
    """Test metadata extraction from filenames"""
    
    print("\n📋 TEST: Metadata Extraction")
    print("-" * 50)
    
    try:
        from cloud_run_batch.file_router.file_metadata_extractor import FileMetadataExtractor
        
        extractor = FileMetadataExtractor()
        
        test_filenames = [
            "customers_20260101.csv",
            "batch_01_customers_delta.csv",
            "orders_20260201.csv",
            "batch_02_products_delta.csv",
            "invalid_filename.csv",
            "order_items_20260301.csv"
        ]
        
        print("Testing filename metadata extraction:")
        
        for filename in test_filenames:
            try:
                metadata = extractor.extract_file_metadata(filename)
                print(f"\n📄 {filename}:")
                print(f"   Entity: {metadata.get('entity_type', 'UNKNOWN')}")
                print(f"   Load Type: {metadata.get('load_type', 'UNKNOWN')}")
                print(f"   Batch ID: {metadata.get('batch_id', 'N/A')}")
                print(f"   File Date: {metadata.get('file_date', 'N/A')}")
                
                if metadata.get('entity_type'):
                    print(f"   ✅ Successfully extracted metadata")
                else:
                    print(f"   ⚠️  Could not extract entity type")
                    
            except Exception as e:
                print(f"   ❌ Extraction failed: {e}")
                
    except ImportError as e:
        print(f"❌ Could not import FileMetadataExtractor: {e}")


async def main():
    """Run all validation tests"""
    await test_validation_methods_directly()
    test_schema_loading()
    test_metadata_extraction()
    
    print("\n" + "=" * 70)
    print("🎉 Validation output testing completed!")
    print("📊 This shows the actual validation results, IDs, and error messages")
    print("    that would be generated during file processing.")


if __name__ == '__main__':
    asyncio.run(main())