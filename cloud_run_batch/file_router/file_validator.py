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
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from google.cloud import storage
from .file_metadata_extractor import FileMetadataExtractor
from .cloud_logging import CloudLogging
from . import settings # validate_settings() will trigger on import

# Configure logging
logger = logging.getLogger(__name__)
# Configuration constants
SUPPORTED_ENTITIES = settings.SUPPORTED_ENTITIES

#  A data Class is a class that is primarily used to store data. Just like a collection of variables.
#  The benefit of using a data class over any other collection is that you could apply methods on data defined within the body of the class.
#  Adding a (frozen=True) makes the class immutable. 
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
    #  The failed_checks attribute would look like ['column_names', 'column_count', 'column_order', 'non_empty_file', 'utf8_encoding', 'comma_delimiter', 'date_format', 'file_size']
    error_details: Dict[str, str]
    # If populated, the error_details attribute would look like {'column_names': 'Column names do not match expected schema'
    #                                                           'column_count': 'Column count does not match expected schema'
    #                                                           'column_order': 'Column order does not match expected schema'
    #                                                           'non_empty_file': 'File is empty'
    #                                                           'utf8_encoding': 'File is not UTF-8 encoded'
    #                                                           'comma_delimiter': 'File is not comma delimited'
    #                                                           'date_format': 'Date format is not valid'
    #                                                           'file_size': 'File size is too large'}
    metadata: Dict[str, Optional[str]]
    # If populated, the metadata attribute would look like {'entity_type': 'customers', 'date': '20260101', 'file_type': 'csv', 'source': 'gcs'}
    file_size_bytes: Optional[int]
    # The file_size_bytes attribute would look like 123456789

class FileValidator:
    """
    Handles comprehensive CSV file validation with configurable schema checks.
    
    This class performs 8 different validation checks on CSV files to ensure
    they meet quality and format requirements before processing.
    """

    def __init__(self):
        """
        Initialize the File Validator with schema configuration.
        
        Configuration is loaded from environment variables and settings.
        """
        # Use settings for configuration
        self.project_id = settings.get_project_id()
        self.schema_config_path = settings.get_schema_path()
        
        # Use the existing load_schema static method.
        # self.expected_schemas = FileValidator.load_schema(self.schema_config_path)

        # Storage Client is a GCP Cloud Storage Handle
        self.storage_client = storage.Client(project=self.project_id)
        # Get ahandle to the FileMetadataExtractor class
        self.metadata_extractor = FileMetadataExtractor()
        self.max_sample_rows = 100  # Rows to sample for validation


    @staticmethod
    def load_schema(schema_path: str) -> Dict[str, List[str]]:
        """
        Load expected column lists from a schema.json file.

        Reads the schema definition and builds two entries per table:
        - entity_type       -> base column names only (used for full loads)
        - entity_type_delta -> base + delta column names (used for delta loads)

        Args:
            schema_path (str): Absolute path to the schema.json file

        Returns:
            Dict[str, List[str]]: Mapping of entity key to ordered column name list.
                Keys follow the pattern:
                    'customers'       -> full-load columns
                    'customers_delta' -> delta-load columns (base + _delta_type, _batch_id, _batch_date)
        """
        #  Open the file and load the schema
        with open(schema_path) as f:
            schema = json.load(f)

        result = {} 
        # Traverse through the json structure and extract base and delta columns
        # The result object would look like :
        # {'customers': ['customer_id', 'first_name', 'last_name', 'email', ....], 
        # 'customers_delta': ['customer_id', 'first_name', 'last_name', 'email', ....], 
        # 'orders_delta': ['order_id', 'customer_id', 'order_date', 'total_amount', ....], 
        # 'order_items': ['order_item_id', 'order_id', 'product_id', 'quantity', 'price', ....], 
        # 'order_items_delta': ['order_item_id', 'order_id', 'product_id', 'quantity', 'price', ....], 
        # 'products': ['product_id', 'product_name', 'category', 'price', 'stock_quantity', ....], 
        # 'products_delta': ['product_id', 'product_name', 'category', 'price', 'stock_quantity', ....]}

        for entity, table in schema["tables"].items():
            base_cols = [col["name"] for col in table["columns"]]        # KeyError if missing. Put all columns into a List object 
            delta_cols = [col["name"] for col in table.get("delta_columns", [])]  # Safe: defaults to []. Put all columns into a List object
            #  Ensure only supported entities are in scope
            if entity in SUPPORTED_ENTITIES:
                result[entity] = base_cols
                result[f"{entity}_delta"] = base_cols + delta_cols
        return result

    @staticmethod
    def load_schema_by_entity(schema_path: str, target_entity: str) -> Dict[str, List[str]]:
        """
        Load expected column lists from a schema.json file for a specific entity.

        Args:
            schema_path (str): Absolute path to the schema.json file
            target_entity (str): The specific entity to load the schema for

        Returns:
            Dict[str, List[str]]: Mapping of entity key to ordered column name list.
        """
        #  Open the file and load the schema
        with open(schema_path) as f:
            schema = json.load(f)

        result = {} 
        # Check if the target entity exists in the schema and is supported
        if target_entity in schema.get("tables", {}) and target_entity in SUPPORTED_ENTITIES:
            table = schema["tables"][target_entity]
            base_cols = [col["name"] for col in table.get("columns", [])]
            delta_cols = [col["name"] for col in table.get("delta_columns", [])]
            
            result[target_entity] = base_cols
            result[f"{target_entity}_delta"] = base_cols + delta_cols
            
        return result

    """
    Validate a single CSV file against schema and format requirements.
    
    Args:
        bucket_name (str): GCS bucket name
        file_path (str): Full path to file in bucket (e.g., "inbox/customers_20260101.csv")
        filename (str): Just the filename (e.g., "customers_20260101.csv")
        
    Returns:
        ValidationResult: Complete validation results
    """
    async def validate_file(
        self,
        bucket_name: str,
        file_path: str,
        filename: str
    ) -> ValidationResult:

        # Generate validation ID without logging
        validation_id = CloudLogging.generate_validation_id()
        
        # Extract metadata from filename
        metadata = self.metadata_extractor.extract_file_metadata(filename)
        #  Sample metadata is {'entity_type': 'customers', 'load_type': 'full', 'batch_id': '20260101', 'file_date': '20260101'}

        if not metadata['entity_type'] or metadata['entity_type'] not in SUPPORTED_ENTITIES:
            return ValidationResult(
                filename=filename,
                validation_id=validation_id,
                passed=False,
                failed_checks=['metadata_extraction'],
                error_details={'metadata_extraction': 'Could not extract entity type from filename, or entity type is not supported'},
                metadata=metadata,
                file_size_bytes=None
            )
        
        # Initialize validation tracking
        failed_checks = []
        error_details = {}
        file_size_bytes = None
        
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.get_blob(file_path)
            
            if blob is None:
                return ValidationResult(
                    filename=filename,
                    validation_id=validation_id,
                    passed=False,
                    failed_checks=['file_existence'],
                    error_details={'file_existence': 'File does not exist in bucket'},
                    metadata=metadata,
                    file_size_bytes=None
                )
            
            file_size_bytes = blob.size
            
            # Download a generous byte ceiling, then trim to exact line count in memory.
            # This avoids hardcoding a byte size that may under/over-capture depending on row width.
            MAX_SAMPLE_BYTES = 50 * 1024  # 50KB ceiling — generous enough for wide rows
            TARGET_LINES = 7              # header + 5 data rows + 1 buffer

            actual_sample_size = min(MAX_SAMPLE_BYTES, file_size_bytes)
            file_content_bytes = blob.download_as_bytes(start=0, end=actual_sample_size - 1)
            #  Decode the bytes to string and split into lines, then take the first TARGET_LINES
            #  The .join is an iterator that joins the lines with a newline character. 
            #  The file content will be a string with the first TARGET_LINES lines of the file.
            file_content = '\n'.join(
                file_content_bytes.decode('utf-8', errors='replace').splitlines()[:TARGET_LINES]
            )

            # Create smaller content samples for specific validation checks
            # utf8_sample_size = min(2 * 1024, len(file_content))
            # file_content_sample = file_content[:utf8_sample_size]
            
            # header_sample_size = min(1 * 1024, len(file_content))
            # file_header_sample = file_content[:header_sample_size]
            
            # Perform validation checks
            check_name, error_msg = await FileValidator._check_file_size(file_size_bytes)
            if check_name:
                failed_checks.append(check_name)
                error_details[check_name] = error_msg
                
            check_name, error_msg = await FileValidator._check_utf8_encoding(file_content)
            if check_name:
                failed_checks.append(check_name)
                error_details[check_name] = error_msg
                
            check_name, error_msg = await FileValidator._check_non_empty_file(file_content)
            if check_name:
                failed_checks.append(check_name)
                error_details[check_name] = error_msg
                
            # CSV structure check can return multiple errors
            csv_errors = await self._check_csv_structure(self.schema_config_path, file_content, metadata['entity_type'], metadata['load_type'])
            for check_name, error_msg in csv_errors:
                failed_checks.append(check_name)
                error_details[check_name] = error_msg
            
        except UnicodeDecodeError as e:
            failed_checks.append('utf8_encoding')
            error_details['utf8_encoding'] = f"File encoding error: {str(e)}"
            
        except Exception as e:
            failed_checks.append('file_access')
            error_details['file_access'] = f"Error accessing file: {str(e)}"
        
        # Create final result
        #  validation passed is a boolean value. if length of failed_checks is 0, then validation passed
        validation_passed = len(failed_checks) == 0
        
        # Log final validation result
        CloudLogging.log_validation_result(
            validation_id=validation_id,
            bucket_name=bucket_name,
            filename=filename,
            metadata=metadata,
            success=validation_passed,
            failed_check=None,  # Use error_message for comprehensive failure details
            expected_value=None,
            actual_value=None,
            # .values on a dict object only gives you all the values disregarding the keys. The join() is an 
            # iterable method that joins the elements of an iterable with a specified separator. In this case a semi 
            # colon is used as a separator.
            error_message='; '.join(error_details.values()) if error_details else None
            #  The contruct would look like ["Expected ['order_id'] but got ['orderid']; Expected UTF-8 but detected Latin-1"]
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

    """
    Check if file size is within acceptable limits.
    Args:
        file_size (int): File size in bytes
        min_size (int): Minimum allowed file size
        max_size (int): Maximum allowed file size
    Returns:
        Tuple[Optional[str], Optional[str]]: (failed_check_name, error_message) or (None, None)
    """
    @staticmethod
    async def _check_file_size(
        file_size: int,
        min_size: int = 1,
        max_size: int = 500 * 1024 * 1024  # 500MB
    ) -> Tuple[Optional[str], Optional[str]]:  # Immutable
     
        if file_size < min_size:
            return 'file_size_min', f"File too small: {file_size} bytes < {min_size} bytes"
        elif file_size > max_size:
            return 'file_size_max', f"File too large: {file_size} bytes > {max_size} bytes"
        return None, None

    """
    Verify file is valid UTF-8 (already done by successful download_as_text).
    Args:
        file_content (str): File content as string
    Returns:
        Tuple[Optional[str], Optional[str]]: (failed_check_name, error_message) or (None, None)
    """
    @staticmethod
    async def _check_utf8_encoding(
        file_content: str
    ) -> Tuple[Optional[str], Optional[str]]:
        try:
            # If we got here, UTF-8 decoding was successful during download
            # Additional check for any problematic characters in the sample
            file_content.encode('utf-8')
            return None, None
        except UnicodeEncodeError as e:
            return 'utf8_encoding', f"UTF-8 encoding validation failed: {str(e)}"

    """
    Check if file has content beyond just headers.
    Args:
        file_content (str): File content as string
    Returns:
        Tuple[Optional[str], Optional[str]]: (failed_check_name, error_message) or (None, None)
    """
    @staticmethod
    async def _check_non_empty_file(
        file_content: str
    ) -> Tuple[Optional[str], Optional[str]]:
        if not file_content or file_content.strip() == "":
            return 'empty_file', "File is empty or contains only whitespace"
            
        # The strip() method removes any leading or trailing whitespace from the string.
        # The split('\n') method splits the string into a list of strings, where each string is a line in the file.
        # The lines variable is of type list, and therefore a function can be called on it.
        lines = file_content.strip().split('\n')
        if len(lines) < 2:  # Need at least header + 1 data row
            return 'insufficient_data', f"File has only {len(lines)} line(s), need at least 2 (header + data)"
            
        return None, None

    """
    Validate CSV structure including columns, delimiter, and data format.
    For delta files (load_type='delta') the schema key is suffixed with '_delta'
    so that the additional _delta_type, _batch_id, and _batch_date columns are
    included in the expected column list.
    Args:
        file_content (str): File content as string
        entity_type (str): Expected entity type for schema lookup (e.g. 'customers')
        load_type (str): Load type from filename metadata ('full' or 'delta')
    Returns:
        List[Tuple[str, str]]: List of (failed_check_name, error_message) tuples
    """
    
    async def _check_csv_structure(
        self,
        schema_config_path: str,
        file_content: str,
        entity_type: str,
        load_type: str
    ) -> List[Tuple[str, str]]:

        validation_errors = []
        
        try:
            # Delta files carry 3 extra columns; use a separate schema key for them
            schema_key = f"{entity_type}_delta" if load_type == "delta" else entity_type

            expected_schemas = FileValidator.load_schema_by_entity(schema_config_path, entity_type)
            expected_columns = expected_schemas.get(schema_key)
            
            if not expected_columns:
                validation_errors.append(('unknown_entity_type', f"No schema defined for entity type: {schema_key}"))
                return validation_errors
            
            # Parse CSV
            csv_reader = csv.reader(io.StringIO(file_content))
            rows = list(csv_reader)
            
            if not rows:
                validation_errors.append(('csv_parse_empty', "No rows found after CSV parsing"))
                return validation_errors
            
            # Check header row which should be Row 1 (index 0)
            actual_columns = [col.strip() for col in rows[0]]
            
            # Column count validation
            if len(actual_columns) != len(expected_columns):
                validation_errors.append(('column_count', f"Expected {len(expected_columns)} columns, found {len(actual_columns)}"))
            
            # Column names validation (order-sensitive)
            if actual_columns != expected_columns:
                validation_errors.append(('column_schema', f"Expected columns {expected_columns}, found {actual_columns}"))
            
            # Sample data rows for format validation
            if len(rows) > 1:
                # data_errors is of type List[Tuple[str, str]]. Only supply the rows except the header to validate
                data_errors = await FileValidator._validate_sample_data(rows[1:], actual_columns)
                #  The extend method is used to add all the elements of an iterable to the end of the list.
                validation_errors.extend(data_errors)
            
        except csv.Error as e:
            validation_errors.append(('csv_format', f"CSV parsing error: {str(e)}"))
        except Exception as e:
            validation_errors.append(('csv_structure', f"CSV structure validation error: {str(e)}"))
            
        return validation_errors

    @staticmethod
    async def _validate_sample_data(
        data_rows: List[List[str]],
        columns: List[str]
    ) -> List[Tuple[str, str]]:
        """
        Validate sample data rows for common format issues.
        
        Args:
            data_rows (List[List[str]]): Sample data rows to validate
            columns (List[str]): Column names
            
        Returns:
            List[Tuple[str, str]]: List of (failed_check_name, error_message) tuples
        """
        validation_errors = []
        issues = []
        
        #  i is the 0-indexed row number of the data rows, whereas row is the actual row data
        for i, row in enumerate(data_rows):
            row_num = i + 1  # +1 because we're 0-indexed for data rows
            
            # Check for consistent column count
            if len(row) != len(columns):
                issues.append(f"Row {row_num}: Expected {len(columns)} values, found {len(row)}")
            
            # Check for completely empty rows, iterating through each column
            if all(cell.strip() == "" for cell in row):
                issues.append(f"Row {row_num}: All columns empty")
        
        if issues:
            validation_errors.append(('data_format', f"Data format issues: {'; '.join(issues)}"))
            
        return validation_errors

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