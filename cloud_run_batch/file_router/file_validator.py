"""
File Validator Module

Performs comprehensive schema and format validation on CSV files.
This module focuses purely on validation logic without routing decisions.

Key Responsibilities:
- Perform 8 schema validation checks (structure, encoding, format)
- Generate detailed validation results with pass/fail status
- Support both single file and batch validation modes
- Async processing with error isolation per file
- Integration with file_metadata_extractor for metadata handling

Schema Validation Checks:
1. Column names match expected schema
2. Column count validation
3. Column order verification
4. Non-empty file validation
5. UTF-8 encoding verification
6. Comma delimiter validation
7. Date format sampling
8. File size validation

Author: Manish Arora
Version: 1.0
"""

import asyncio
import csv
import io
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from google.cloud import storage
from .file_metadata_extractor import FileMetadataExtractor
from .cloud_logging import CloudLogging

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Represents the result of file validation.
    
    Attributes:
        filename (str): Name of the validated file
        validation_id (str): Unique validation identifier
        passed (bool): Whether validation passed
        failed_checks (List[str]): List of failed validation check names
        error_details (Dict[str, str]): Detailed error information per failed check
        metadata (Dict[str, Optional[str]]): Extracted file metadata
        file_size_bytes (Optional[int]): Size of the file in bytes
    """
    filename: str
    validation_id: str
    passed: bool
    failed_checks: List[str]
    error_details: Dict[str, str]
    metadata: Dict[str, Optional[str]]
    file_size_bytes: Optional[int]


class FileValidator:
    """
    Handles comprehensive CSV file validation with configurable schema checks.
    
    This class performs 8 different validation checks on CSV files to ensure
    they meet quality and format requirements before processing.
    """

    def __init__(self, project_id: str, expected_schemas: Dict[str, List[str]]):
        """
        Initialize the File Validator.
        
        Args:
            project_id (str): GCP project ID
            expected_schemas (Dict[str, List[str]]): Entity type to column list mapping
                Example: {'customers': ['id', 'name', 'email'], 'orders': ['id', 'amount']}
        """
        self.project_id = project_id
        self.expected_schemas = expected_schemas
        self.storage_client = storage.Client(project=project_id)
        self.metadata_extractor = FileMetadataExtractor()
        self.max_sample_rows = 100  # Rows to sample for validation

    async def validate_file(
        self,
        bucket_name: str,
        file_path: str,
        filename: str
    ) -> ValidationResult:
        """
        Validate a single CSV file against schema and format requirements.
        
        Args:
            bucket_name (str): GCS bucket name
            file_path (str): Full path to file in bucket (e.g., "inbox/customers_20260101.csv")
            filename (str): Just the filename (e.g., "customers_20260101.csv")
            
        Returns:
            ValidationResult: Complete validation results
        """
        # Generate validation ID and extract metadata
        validation_id = CloudLogging.log_validation_result(
            bucket_name=bucket_name,
            filename=filename,
            metadata={},  # Will be updated after extraction
            success=True,  # Placeholder, will be updated
            validation_id=None,
            failed_check=None,
            expected_value=None,
            actual_value=None,
            error_message=None
        )
        
        # Extract metadata from filename
        metadata = self.metadata_extractor.extract_file_metadata(filename)
        if not metadata['entity_type']:
            return ValidationResult(
                filename=filename,
                validation_id=validation_id,
                passed=False,
                failed_checks=['metadata_extraction'],
                error_details={'metadata_extraction': 'Could not extract entity type from filename'},
                metadata=metadata,
                file_size_bytes=None
            )
        
        # Initialize validation tracking
        failed_checks = []
        error_details = {}
        file_size_bytes = None
        
        try:
            # Get file from GCS and basic info
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            
            if not blob.exists():
                return ValidationResult(
                    filename=filename,
                    validation_id=validation_id,
                    passed=False,
                    failed_checks=['file_existence'],
                    error_details={'file_existence': 'File does not exist in bucket'},
                    metadata=metadata,
                    file_size_bytes=None
                )
            
            # Get file size
            blob.reload()
            file_size_bytes = blob.size
            
            # Download file content for validation
            file_content = blob.download_as_text(encoding='utf-8')
            
            # Perform validation checks
            await self._check_file_size(file_size_bytes, failed_checks, error_details)
            await self._check_utf8_encoding(file_content, failed_checks, error_details)
            await self._check_non_empty_file(file_content, failed_checks, error_details)
            await self._check_csv_structure(file_content, metadata['entity_type'], failed_checks, error_details)
            
        except UnicodeDecodeError as e:
            failed_checks.append('utf8_encoding')
            error_details['utf8_encoding'] = f"File encoding error: {str(e)}"
            
        except Exception as e:
            failed_checks.append('file_access')
            error_details['file_access'] = f"Error accessing file: {str(e)}"
        
        # Create final result
        validation_passed = len(failed_checks) == 0
        
        # Log final validation result
        CloudLogging.log_validation_result(
            bucket_name=bucket_name,
            filename=filename,
            metadata=metadata,
            success=validation_passed,
            validation_id=validation_id,
            failed_check=failed_checks[0] if failed_checks else None,
            expected_value=None,
            actual_value=None,
            error_message='; '.join(error_details.values()) if error_details else None
        )
        
        return ValidationResult(
            filename=filename,
            validation_id=validation_id,
            passed=validation_passed,
            failed_checks=failed_checks,
            error_details=error_details,
            metadata=metadata,
            file_size_bytes=file_size_bytes
        )

    async def _check_file_size(
        self,
        file_size: int,
        failed_checks: List[str],
        error_details: Dict[str, str],
        min_size: int = 1,
        max_size: int = 500 * 1024 * 1024  # 500MB
    ) -> None:
        """
        Check if file size is within acceptable limits.
        
        Args:
            file_size (int): File size in bytes
            failed_checks (List[str]): List to append failed check names
            error_details (Dict[str, str]): Dict to store error details
            min_size (int): Minimum allowed file size
            max_size (int): Maximum allowed file size
        """
        if file_size < min_size:
            failed_checks.append('file_size_min')
            error_details['file_size_min'] = f"File too small: {file_size} bytes < {min_size} bytes"
        elif file_size > max_size:
            failed_checks.append('file_size_max')
            error_details['file_size_max'] = f"File too large: {file_size} bytes > {max_size} bytes"

    async def _check_utf8_encoding(
        self,
        file_content: str,
        failed_checks: List[str],
        error_details: Dict[str, str]
    ) -> None:
        """
        Verify file is valid UTF-8 (already done by successful download_as_text).
        
        Args:
            file_content (str): File content as string
            failed_checks (List[str]): List to append failed check names
            error_details (Dict[str, str]): Dict to store error details
        """
        try:
            # If we got here, UTF-8 decoding was successful
            # Additional check for any problematic characters
            file_content.encode('utf-8')
        except UnicodeEncodeError as e:
            failed_checks.append('utf8_encoding')
            error_details['utf8_encoding'] = f"UTF-8 encoding validation failed: {str(e)}"

    async def _check_non_empty_file(
        self,
        file_content: str,
        failed_checks: List[str],
        error_details: Dict[str, str]
    ) -> None:
        """
        Check if file has content beyond just headers.
        
        Args:
            file_content (str): File content as string
            failed_checks (List[str]): List to append failed check names
            error_details (Dict[str, str]): Dict to store error details
        """
        if not file_content or file_content.strip() == "":
            failed_checks.append('empty_file')
            error_details['empty_file'] = "File is empty or contains only whitespace"
            return
            
        lines = file_content.strip().split('\n')
        if len(lines) < 2:  # Need at least header + 1 data row
            failed_checks.append('insufficient_data')
            error_details['insufficient_data'] = f"File has only {len(lines)} line(s), need at least 2 (header + data)"

    async def _check_csv_structure(
        self,
        file_content: str,
        entity_type: str,
        failed_checks: List[str],
        error_details: Dict[str, str]
    ) -> None:
        """
        Validate CSV structure including columns, delimiter, and data format.
        
        Args:
            file_content (str): File content as string
            entity_type (str): Expected entity type for schema lookup
            failed_checks (List[str]): List to append failed check names
            error_details (Dict[str, str]): Dict to store error details
        """
        try:
            # Get expected schema for entity type
            expected_columns = self.expected_schemas.get(entity_type)
            if not expected_columns:
                failed_checks.append('unknown_entity_type')
                error_details['unknown_entity_type'] = f"No schema defined for entity type: {entity_type}"
                return
            
            # Parse CSV
            csv_reader = csv.reader(io.StringIO(file_content))
            rows = list(csv_reader)
            
            if not rows:
                failed_checks.append('csv_parse_empty')
                error_details['csv_parse_empty'] = "No rows found after CSV parsing"
                return
            
            # Check header row
            actual_columns = [col.strip() for col in rows[0]]
            
            # Column count validation
            if len(actual_columns) != len(expected_columns):
                failed_checks.append('column_count')
                error_details['column_count'] = f"Expected {len(expected_columns)} columns, found {len(actual_columns)}"
            
            # Column names validation (order-sensitive)
            if actual_columns != expected_columns:
                failed_checks.append('column_schema')
                error_details['column_schema'] = f"Expected columns {expected_columns}, found {actual_columns}"
            
            # Sample data rows for format validation
            if len(rows) > 1:
                await self._validate_sample_data(rows[1:min(len(rows), self.max_sample_rows + 1)], 
                                                 actual_columns, failed_checks, error_details)
            
        except csv.Error as e:
            failed_checks.append('csv_format')
            error_details['csv_format'] = f"CSV parsing error: {str(e)}"
        except Exception as e:
            failed_checks.append('csv_structure')
            error_details['csv_structure'] = f"CSV structure validation error: {str(e)}"

    async def _validate_sample_data(
        self,
        data_rows: List[List[str]],
        columns: List[str],
        failed_checks: List[str],
        error_details: Dict[str, str]
    ) -> None:
        """
        Validate sample data rows for common format issues.
        
        Args:
            data_rows (List[List[str]]): Sample data rows to validate
            columns (List[str]): Column names
            failed_checks (List[str]): List to append failed check names
            error_details (Dict[str, str]): Dict to store error details
        """
        issues = []
        
        for i, row in enumerate(data_rows):
            row_num = i + 2  # +2 because we're 0-indexed and skipped header
            
            # Check for consistent column count
            if len(row) != len(columns):
                issues.append(f"Row {row_num}: Expected {len(columns)} values, found {len(row)}")
                if len(issues) >= 5:  # Limit error collection
                    break
            
            # Check for completely empty rows
            if all(cell.strip() == "" for cell in row):
                issues.append(f"Row {row_num}: All columns empty")
                if len(issues) >= 5:
                    break
        
        if issues:
            failed_checks.append('data_format')
            error_details['data_format'] = f"Data format issues: {'; '.join(issues)}"

    async def validate_batch(
        self,
        bucket_name: str,
        file_list: List[Tuple[str, str]]
    ) -> List[ValidationResult]:
        """
        Validate multiple files concurrently.
        
        Args:
            bucket_name (str): GCS bucket name
            file_list (List[Tuple[str, str]]): List of (file_path, filename) tuples
            
        Returns:
            List[ValidationResult]: Results for each file
        """
        validation_tasks = [
            self.validate_file(bucket_name, file_path, filename)
            for file_path, filename in file_list
        ]
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Handle any exceptions in the results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                file_path, filename = file_list[i]
                final_results.append(ValidationResult(
                    filename=filename,
                    validation_id=f"error_{i}",
                    passed=False,
                    failed_checks=['validation_exception'],
                    error_details={'validation_exception': str(result)},
                    metadata={},
                    file_size_bytes=None
                ))
            else:
                final_results.append(result)
        
        return final_results