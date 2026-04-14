"""
Pytest configuration and shared fixtures for test suite

Provides common test fixtures, configuration, and utilities
for testing FileValidator and related modules.
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, patch


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_gcs_blob():
    """Mock GCS blob for testing file operations"""
    blob = Mock()
    blob.exists.return_value = True
    blob.size = 1024
    blob.download_as_bytes.return_value = b"sample,csv,content\nrow1,data,here\nrow2,more,data"
    return blob


@pytest.fixture
def mock_storage_client():
    """Mock GCS storage client for testing"""
    client = Mock()
    bucket = Mock()
    client.bucket.return_value = bucket
    return client, bucket


@pytest.fixture
def temp_csv_file():
    """Create temporary CSV file for testing"""
    content = """customer_id,first_name,last_name,email
123,John,Doe,john@example.com
456,Jane,Smith,jane@example.com"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def project_paths():
    """Provide common project paths"""
    base_path = '/Users/manisharora/Projects/BigQGeminiWarehouse'
    return {
        'base': base_path,
        'schema': os.path.join(base_path, 'schemas', 'schema.json'),
        'data': os.path.join(base_path, 'data', 'intelia-hackathon-files'),
        'tests': os.path.join(base_path, 'tests')
    }