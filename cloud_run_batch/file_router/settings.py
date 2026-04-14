"""
Settings and Configuration Module

Centralized configuration management for the file router system.
Currently focuses on schema file path configuration to support
different environments (dev, staging, production).

Author: Manish Arora
Version: 1.0
"""

import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent  # /Users/manisharora/Projects/BigQGeminiWarehouse
SCHEMAS_DIR = PROJECT_ROOT / "schemas"

# Schema configuration
SCHEMA_FILE_PATH = str(SCHEMAS_DIR / "schema.json")
SUPPORTED_ENTITIES = {'customers', 'orders', 'order_items', 'products'}


def get_project_id() -> str:
    """Get GCP project ID from environment variable."""
    project_id = os.getenv("PROJECT_ID")
    if not project_id:
        raise ValueError("PROJECT_ID environment variable is required")
    return project_id

def get_schema_path() -> str:
    """Get schema file path for current environment."""
    # In production, this might come from a different source
    env_schema_path = os.getenv("SCHEMA_FILE_PATH")
    if env_schema_path:
        return env_schema_path
    return SCHEMA_FILE_PATH

# Validation for required settings
def validate_settings():
    """Validate that all required settings are properly configured."""
    schema_path = get_schema_path()
    if not Path(schema_path).exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

# Run validation on import
validate_settings()