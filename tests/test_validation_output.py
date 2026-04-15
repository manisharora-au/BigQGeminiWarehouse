"""
Test to show detailed validation outputs including validation_id, error messages, etc.

This test demonstrates the actual validation results with all details
that would be generated during file processing.
"""

import sys
import os
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock

# Add project to path
sys.path.insert(0, '/Users/manisharora/Projects/BigQGeminiWarehouse')

def mock_gcs_dependencies():
    """Mock GCS dependencies to allow testing without actual cloud access"""
    
    # Mock the google.cloud.storage module
    mock_storage = Mock()
    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()
    
    # Configure mock blob
    mock_blob.exists.return_value = True
    mock_blob.size = 2048  # 2KB sample file
    mock_blob.download_as_bytes.return_value = b"""customer_id,first_name,last_name,email,phone
123e4567-e89b-12d3-a456-426614174000,John,Doe,john.doe@example.com,555-0123
987fcdeb-51a2-43d7-b123-987654321abc,Jane,Smith,jane.smith@example.com,555-0456
456789ab-cdef-1234-5678-9abcdef01234,Bob,Johnson,bob.johnson@example.com,555-0789"""
    
    # Configure mock bucket and client
    mock_bucket.get_blob.return_value = mock_blob
    mock_client.bucket.return_value = mock_bucket
    mock_storage.Client.return_value = mock_client
    
    return mock_storage


async def test_detailed_validation_output():
    """Test detailed validation output showing all validation details"""
    
    print("🧪 Testing Detailed Validation Output")
    print("=" * 70)
    
    # Mock GCS dependencies
    with patch.dict('sys.modules', {'google.cloud.storage': mock_gcs_dependencies()}):
        with patch.dict('sys.modules', {'google.cloud': Mock()}):
            
            # Import after mocking
            from cloud_run_batch.file_router.file_validator import FileValidator, ValidationResult
            from cloud_run_batch.file_router.cloud_logging import CloudLogging
            
            # Mock CloudLogging to capture log calls
            with patch.object(CloudLogging, 'log_validation_result') as mock_log:
                
                # Create validator
                validator = FileValidator()
                
                # Test Case 1: Valid File
                print("\n📋 TEST CASE 1: Valid CSV File")
                print("-" * 50)
                
                result1 = await validator.validate_file(
                    bucket_name="test-bucket",
                    file_path="inbox/customers_20260101.csv", 
                    filename="customers_20260101.csv"
                )
                
                print(f"✅ Validation ID: {result1.validation_id}")
                print(f"✅ Filename: {result1.filename}")
                print(f"✅ Passed: {result1.passed}")
                print(f"✅ Failed Checks: {result1.failed_checks}")
                print(f"✅ Error Details: {result1.error_details}")
                print(f"✅ Metadata: {result1.metadata}")
                print(f"✅ File Size: {result1.file_size_bytes} bytes")
                
                # Show log call details
                if mock_log.called:
                    log_call = mock_log.call_args
                    print("\n📝 Log Call Details:")
                    print(f"   - validation_id: {log_call.kwargs.get('validation_id')}")
                    print(f"   - bucket_name: {log_call.kwargs.get('bucket_name')}")
                    print(f"   - filename: {log_call.kwargs.get('filename')}")
                    print(f"   - success: {log_call.kwargs.get('success')}")
                    print(f"   - error_message: {log_call.kwargs.get('error_message')}")
                
                mock_log.reset_mock()
                
                # Test Case 2: Invalid File (Wrong Schema)
                print("\n\n📋 TEST CASE 2: Invalid CSV File (Wrong Schema)")
                print("-" * 50)
                
                # Mock a file with wrong schema
                validator.storage_client.bucket.return_value.get_blob.return_value.download_as_bytes.return_value = b"""wrong_col1,wrong_col2,wrong_col3
data1,data2,data3
more1,more2,more3"""
                
                result2 = await validator.validate_file(
                    bucket_name="test-bucket",
                    file_path="inbox/invalid_customers_20260101.csv",
                    filename="invalid_customers_20260101.csv"
                )
                
                print(f"❌ Validation ID: {result2.validation_id}")
                print(f"❌ Filename: {result2.filename}")
                print(f"❌ Passed: {result2.passed}")
                print(f"❌ Failed Checks: {result2.failed_checks}")
                print(f"❌ Error Details:")
                for check, error in result2.error_details.items():
                    print(f"     • {check}: {error}")
                print(f"❌ Metadata: {result2.metadata}")
                print(f"❌ File Size: {result2.file_size_bytes} bytes")
                
                # Show log call details for failed validation
                if mock_log.called:
                    log_call = mock_log.call_args
                    print("\n📝 Log Call Details (Failed Validation):")
                    print(f"   - validation_id: {log_call.kwargs.get('validation_id')}")
                    print(f"   - success: {log_call.kwargs.get('success')}")
                    print(f"   - failed_check: {log_call.kwargs.get('failed_check')}")
                    print(f"   - error_message: {log_call.kwargs.get('error_message')}")
                
                mock_log.reset_mock()
                
                # Test Case 3: Delta File
                print("\n\n📋 TEST CASE 3: Delta CSV File")
                print("-" * 50)
                
                # Mock a delta file
                validator.storage_client.bucket.return_value.get_blob.return_value.download_as_bytes.return_value = b"""customer_id,first_name,last_name,email,phone,date_of_birth,gender,registration_date,country,city,acquisition_channel,customer_tier,is_email_subscribed,is_sms_subscribed,preferred_device,preferred_category,loyalty_points,account_status,last_login_date,referral_source_id,marketing_segment,_delta_type,_batch_id,_batch_date
123e4567-e89b-12d3-a456-426614174000,John,Doe,john.doe@example.com,555-0123,1990-01-01,Male,2023-01-01,US,New York,direct,gold,true,false,mobile,Electronics,1000,active,2024-01-01,,loyal,INSERT,batch_001,2024-01-01T00:00:00Z"""
                
                result3 = await validator.validate_file(
                    bucket_name="test-bucket",
                    file_path="inbox/batch_01_customers_delta.csv",
                    filename="batch_01_customers_delta.csv"
                )
                
                print(f"🔄 Validation ID: {result3.validation_id}")
                print(f"🔄 Filename: {result3.filename}")
                print(f"🔄 Passed: {result3.passed}")
                print(f"🔄 Failed Checks: {result3.failed_checks}")
                print(f"🔄 Error Details: {result3.error_details}")
                print(f"🔄 Metadata: {result3.metadata}")
                print(f"🔄 Load Type: {result3.metadata.get('load_type', 'unknown')}")
                
                # Show log call details for delta file
                if mock_log.called:
                    log_call = mock_log.call_args
                    print("\n📝 Log Call Details (Delta File):")
                    print(f"   - validation_id: {log_call.kwargs.get('validation_id')}")
                    print(f"   - metadata: {log_call.kwargs.get('metadata')}")
                    print(f"   - success: {log_call.kwargs.get('success')}")
                
                # Test Case 4: File Size Error
                print("\n\n📋 TEST CASE 4: File Too Large")
                print("-" * 50)
                
                # Mock a very large file
                validator.storage_client.bucket.return_value.get_blob.return_value.size = 600 * 1024 * 1024  # 600MB
                
                result4 = await validator.validate_file(
                    bucket_name="test-bucket",
                    file_path="inbox/huge_file.csv",
                    filename="huge_file.csv"
                )
                
                print(f"🚫 Validation ID: {result4.validation_id}")
                print(f"🚫 Filename: {result4.filename}")
                print(f"🚫 Passed: {result4.passed}")
                print(f"🚫 Failed Checks: {result4.failed_checks}")
                print(f"🚫 Error Details:")
                for check, error in result4.error_details.items():
                    print(f"     • {check}: {error}")
                
                print(f"🚫 File Size: {result4.file_size_bytes} bytes ({result4.file_size_bytes / (1024*1024):.1f} MB)")
                
                # Test Case 5: Multiple Validation Errors
                print("\n\n📋 TEST CASE 5: Multiple Validation Errors")
                print("-" * 50)
                
                # Mock an empty file with wrong name
                validator.storage_client.bucket.return_value.get_blob.return_value.size = 0
                validator.storage_client.bucket.return_value.get_blob.return_value.download_as_bytes.return_value = b""
                
                result5 = await validator.validate_file(
                    bucket_name="test-bucket",
                    file_path="inbox/unknown_entity_20260101.csv",
                    filename="unknown_entity_20260101.csv"
                )
                
                print(f"💥 Validation ID: {result5.validation_id}")
                print(f"💥 Filename: {result5.filename}")
                print(f"💥 Passed: {result5.passed}")
                print(f"💥 Failed Checks ({len(result5.failed_checks)} total):")
                for i, check in enumerate(result5.failed_checks, 1):
                    print(f"     {i}. {check}")
                print(f"💥 Error Details:")
                for check, error in result5.error_details.items():
                    print(f"     • {check}: {error}")
                
                if mock_log.called:
                    log_call = mock_log.call_args
                    print("\n📝 Comprehensive Error Message:")
                    print(f"   {log_call.kwargs.get('error_message')}")
                
                print("\n" + "=" * 70)
                print("🎉 Detailed validation output testing completed!")
                print(f"📊 Generated {5} different validation scenarios with unique IDs")


def test_validation_id_generation():
    """Test validation ID generation patterns"""
    
    print("\n🔢 Testing Validation ID Generation")
    print("=" * 50)
    
    # Mock GCS to avoid cloud dependencies
    with patch.dict('sys.modules', {'google.cloud.storage': Mock()}):
        with patch.dict('sys.modules', {'google.cloud': Mock()}):
            from cloud_run_batch.file_router.cloud_logging import CloudLogging
            
            # Generate multiple validation IDs
            ids = [CloudLogging.generate_validation_id() for _ in range(5)]
            
            print("Generated Validation IDs:")
            for i, validation_id in enumerate(ids, 1):
                print(f"  {i}. {validation_id}")
            
            # Verify uniqueness
            assert len(set(ids)) == len(ids), "All validation IDs should be unique"
            print(f"\n✅ All {len(ids)} validation IDs are unique")
            
            # Verify format
            for validation_id in ids:
                assert validation_id.startswith('validation_'), f"ID should start with 'validation_': {validation_id}"
                assert len(validation_id) == 19, f"ID should be 19 chars long: {validation_id} (length: {len(validation_id)})"
            
            print("✅ All validation IDs follow expected format: validation_xxxxxxxx")


async def main():
    """Run all detailed validation tests"""
    await test_detailed_validation_output()
    test_validation_id_generation()


if __name__ == '__main__':
    asyncio.run(main())