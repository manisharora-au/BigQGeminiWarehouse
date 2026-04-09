"""
Processing Logger Module

Handles structured logging for file processing results, governance tracking, and audit trails.
This module provides comprehensive logging capabilities for all validation and processing
operations in the simplified architecture.

Key Responsibilities:
- Log validation results (PASS/FAIL) to governance.validation_log
- Record processing statistics and timing metrics
- Generate structured logs for Cloud Logging integration
- Support audit trail requirements for governance
- Track file processing lifecycle from inbox to validated/quarantine

Author: Manish Arora
Version: 1.0
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
import uuid
from google.cloud import bigquery

# Configure logging
logger = logging.getLogger(__name__)

class ProcessingLogger:
    """
    Handles logging of file processing results for governance and monitoring, and persistence long term in BigQuery.
    """

    @staticmethod
    def log_validation_result_to_cloud_logging(
        bucket_name: str, 
        filename: str, 
        metadata: Dict[str, Optional[str]], 
        success: bool, 
        failed_check: Optional[str] = None,
        error_message: Optional[str] = None,
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None
    ) -> str:
        """
        Log validation result for governance tracking.
        
        Creates structured log entries for all file validation attempts, that land in the /inbox folder of the bucket.
        successful or failed, to support monitoring and debugging.
        
        Args:
            bucket_name (str): Name of the GCS bucket. Mandatory.
            filename (str): Original filename being processed. Mandatory.
            metadata (Dict[str, Optional[str]]): Extracted file metadata. Mandatory.
            success (bool): Whether validation was successful. Mandatory.
            failed_check (Optional[str]): Name of the specific check that failed. Optional.
            error_message (Optional[str]): Detailed error description. Optional.
            expected_value (Optional[str]): What was expected (for failures). Optional.
            actual_value (Optional[str]): What was found (for failures). Optional.
            
        Returns:
            str: Validation ID for tracking and correlation
            
        Example:
            >>> ProcessingLogger.log_validation_result_to_cloud_logging(
            ...     "my-bucket",
            ...     "customers_20260101.csv", 
            ...     {"entity_type": "customers", "load_type": "full"},
            ...     True
            ... )
            'validation_a3f9c2d1-...'
        """
        #  Generate a new Validation ID
        validation_id = f"validation_{str(uuid.uuid4())[:8]}"
        
        # Build a comprehensive log entry dictionary object for governance.validation_log
        log_entry = {
            'validation_id': validation_id,
            'file_path': f"gs://{bucket_name}/inbox/{filename}",
            'bucket_name': bucket_name,
            'filename': filename,
            'entity_type': metadata.get('entity_type'),
            'load_type': metadata.get('load_type'),
            'batch_id': metadata.get('batch_id'),
            'file_date': metadata.get('file_date'),
            'validation_status': 'PASS' if success else 'FAIL',
            'failed_check': failed_check if not success else None,
            'expected_value': expected_value if not success else None,
            'actual_value': actual_value if not success else None,
            'error_message': error_message if not success else None,
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'processor': 'cloud-run-validator',
            'processor_version': '1.0'
        }
        
        # Log to Cloud Logging with appropriate severity
        # The below code snippet logs (system.out.println) in Java to Cloud Logging.
        # The logger.info() method signature is: logger.info(msg, *args, **kwargs)
        if success:
            logger.info(
                f"Validation SUCCESS: {filename}",
                # The extra parameter is a special keyword argument that the Python logging system recognizes. 
                # The extra= is essential for Cloud Logging integration to properly structure the log data.
                # When you pass extra={'key': 'value'}, the logging framework:
                # 1. Extracts those key-value pairs
                # 2. Adds them as attributes to the LogRecord object
                # 3. Makes them available to formatters and handlers (like Cloud Logging)
                extra={
                    'validation_id': validation_id,
                    'entity_type': metadata.get('entity_type'),
                    'load_type': metadata.get('load_type'),
                    'structured_data': log_entry
                }
            )
        else:
            logger.error(
                f"Validation FAILED: {filename} - {failed_check}: {error_message}",
                extra={
                    'validation_id': validation_id,
                    'failed_check': failed_check,
                    'error_message': error_message,
                    'structured_data': log_entry
                }
            )
        
        return validation_id

    @staticmethod
    def log_batch_processing_start_to_cloud_logging(
        batch_id: str,
        file_count: int,
        processing_mode: str,
        max_workers: int
    ) -> None:
        """
        Log the start of batch processing operation.
        
        Args:
            batch_id (str): Unique identifier for this batch
            file_count (int): Number of files in the batch
            processing_mode (str): Processing mode (standard, backfill, manual)
            max_workers (int): Number of concurrent workers
        """
        #  Logger.info and/or logger.error is used to log messages to Cloud Logging. Extra is eesential for structured logging.
        logger.info(
            f"Batch processing started: {file_count} files",
            extra={
                'batch_id': batch_id,
                'file_count': file_count,
                'processing_mode': processing_mode,
                'max_workers': max_workers,
                'event_type': 'batch_start'
            }
        )

    @staticmethod
    def log_batch_processing_complete_to_cloud_logging(
        batch_id: str,
        stats: Dict[str, int],
        duration_seconds: float,
        processing_mode: str
    ) -> None:
        """
        Log the completion of batch processing operation.
        
        Args:
            batch_id (str): Unique identifier for this batch
            stats (Dict[str, int]): Processing statistics (total, success, failed)
            duration_seconds (float): Total processing time
            processing_mode (str): Processing mode used
        """
        logger.info(
            f"Batch processing completed: {stats}",
            extra={
                'batch_id': batch_id,
                'processing_stats': stats,
                'duration_seconds': duration_seconds,
                'processing_mode': processing_mode,
                'files_per_second': stats['total'] / duration_seconds if duration_seconds > 0 else 0,
                'event_type': 'batch_complete'
            }
        )

    @staticmethod
    def log_file_processing_metrics_to_cloud_logging(
        filename: str,
        validation_id: str,
        processing_time_ms: int,
        file_size_bytes: int,
        destination_path: Optional[str] = None
    ) -> None:
        """
        Log individual file processing metrics.
        
        Args:
            filename (str): Name of the processed file
            validation_id (str): Validation ID for correlation
            processing_time_ms (int): Time taken to process the file
            file_size_bytes (int): Size of the file in bytes
            destination_path (Optional[str]): Where the file was routed (if successful)
        """
        logger.info(
            f"File processed: {filename} in {processing_time_ms}ms",
            extra={
                'filename': filename,
                'validation_id': validation_id,
                'processing_time_ms': processing_time_ms,
                'file_size_bytes': file_size_bytes,
                'destination_path': destination_path,
                'throughput_bytes_per_second': (file_size_bytes * 1000) // processing_time_ms if processing_time_ms > 0 else 0,
                'event_type': 'file_metrics'
            }
        )

    @staticmethod
    def log_cloud_storage_operation_to_cloud_logging(
        operation: str,
        source_path: str,
        destination_path: str,
        success: bool,
        duration_ms: int,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log Cloud Storage file operations for debugging and monitoring.
        
        Args:
            operation (str): Type of operation (copy, move, delete)
            source_path (str): Source file path
            destination_path (str): Destination file path  
            success (bool): Whether operation succeeded
            duration_ms (int): Operation duration in milliseconds
            error_message (Optional[str]): Error details if operation failed
        """
        severity = 'info' if success else 'error'
        message = f"Storage {operation}: {source_path} → {destination_path}"
        
        #  Prepare the log_data dictionary object for logging.
        log_data = {
            'operation': operation,
            'source_path': source_path,
            'destination_path': destination_path,
            'success': success,
            'duration_ms': duration_ms,
            'event_type': 'storage_operation'
        }
        
        if not success and error_message:
            #  Add the error_message to the log_data dictionary object for logging.
            log_data['error_message'] = error_message
            message += f" - ERROR: {error_message}"
        
        #  logger.info method signature is logger.info(msg, *args, **kwargs)
        if success:
            logger.info(message, extra=log_data)
        else:
            logger.error(message, extra=log_data)

    @staticmethod
    def log_governance_event_to_cloud_logging(
        event_type: str,
        entity_type: str,
        #  The details parameter is a dictionary that can contain any additional information about the event.
        #  The Any Keyword is used to indicate that the dictionary can contain any type of value.
        details: Dict[str, Any],
        severity: str = 'info' # if severity is not provided, it will default to info
    ) -> None:
        """
        Log governance-related events for audit and compliance.
        
        Args:
            event_type (str): Type of governance event
            entity_type (str): Entity being processed
            details (Dict[str, Any]): Additional event details
            severity (str): Log severity level
        """

        #  Prepare the log_data dictionary object for logging.
        log_data = {
            'event_type': f'governance_{event_type}',
            'entity_type': entity_type,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Always use a try-except block when unpacking the details dictionary. 
        # This is because the details dictionary can contain any type of value.
        try:
            if details:
                log_data.update(**details)
        except TypeError as e:
            logger.error(f"Error unpacking details: {e}")
        
        message = f"Governance event: {event_type} for {entity_type}"
        
        #  Remember to add the extra=log_data parameter to the logger.info method call.
        if severity == 'error':
            logger.error(message, extra=log_data)
        elif severity == 'warning':
            logger.warning(message, extra=log_data)
        else:
            logger.info(message, extra=log_data)

    @staticmethod
    def create_validation_log_record_for_bigquery(
        validation_id: str,
        bucket_name: str,
        filename: str,
        metadata: Dict[str, Optional[str]],
        success: bool,
        failed_check: Optional[str] = None,
        error_message: Optional[str] = None,
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a validation log record for BigQuery governance.validation_log table.
        By that, the method only constructs a dictionary object. It does not log anything to Cloud Logging or any BQ Table.
        
        This method creates the structured data that will be inserted into the
        governance database for audit and monitoring purposes.
        
        Args:
            validation_id (str): Unique validation identifier
            bucket_name (str): GCS bucket name
            filename (str): Original filename
            metadata (Dict[str, Optional[str]]): Extracted metadata
            success (bool): Validation result
            failed_check (Optional[str]): Failed check name
            error_message (Optional[str]): Error description
            expected_value (Optional[str]): Expected value for failures
            actual_value (Optional[str]): Actual value found
            
        Returns:
            Dict[str, Any]: Structured record for BigQuery insertion
        """
        return {
            'validation_id': validation_id,
            'file_path': f"gs://{bucket_name}/inbox/{filename}",
            'bucket_name': bucket_name,
            'filename': filename,
            'entity_type': metadata.get('entity_type'),
            'load_type': metadata.get('load_type'),
            'batch_id': metadata.get('batch_id'),
            'file_date': metadata.get('file_date'),
            'validation_timestamp': datetime.now(timezone.utc),
            'validation_status': 'PASS' if success else 'FAIL',
            'failed_check': failed_check,
            'expected_value': expected_value,
            'actual_value': actual_value,
            'error_message': error_message,
            'processor': 'cloud-run-validator',
            'processor_version': '1.0'
        }

    @staticmethod
    def write_validation_result_to_bigquery(
        project_id: str,
        dataset_id: str,
        table_id: str,
        validation_record: Dict[str, Any]
    ) -> bool:
        """
        Write validation result to BigQuery governance.validation_log table.
        
        Args:
            project_id (str): GCP project ID
            dataset_id (str): BigQuery dataset ID (typically 'governance')
            table_id (str): BigQuery table ID (typically 'validation_log')
            validation_record (Dict[str, Any]): Record created by create_validation_log_record_for_bigquery()
            
        Returns:
            bool: True if insert successful, False otherwise
        """
        try:
            #  Get a BQ client handle
            client = bigquery.Client(project=project_id)
            #  Get the table reference
            table_ref = client.dataset(dataset_id).table(table_id)
            
            # Insert the record. The list is used to wrap the dictionary object because the insert_rows_json method expects
            # a list of dictionaries.
            # The dictionary objects auto unpacks the key-value pairs into columns and values.
            errors = client.insert_rows_json(table_ref, [validation_record])

            # The object errors is of type list. If the list is empty, it means the insert was successful.
            if errors:
                logger.error(
                    f"BigQuery insert failed: {errors}",
                    extra={
                        'validation_id': validation_record.get('validation_id'),
                        'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                        'errors': errors,
                        'event_type': 'bigquery_insert_failure'
                    }
                )
                return False
            else:
                logger.info(
                    f"BigQuery insert successful for validation_id: {validation_record.get('validation_id')}",
                    extra={
                        'validation_id': validation_record.get('validation_id'),
                        'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                        'event_type': 'bigquery_insert_success'
                    }
                )
                return True
        except Exception as e:
            logger.error(
                f"BigQuery insert exception: {str(e)}",
                extra={
                    'validation_id': validation_record.get('validation_id'),
                    'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                    'error_message': str(e),
                    'event_type': 'bigquery_insert_exception'
                }
            )
            return False

    @staticmethod
    def write_batch_validation_results_to_bigquery(
        project_id: str,
        dataset_id: str,
        table_id: str,
        validation_records: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Write multiple validation results to BigQuery in batch.
        
        Args:
            project_id (str): GCP project ID
            dataset_id (str): BigQuery dataset ID
            table_id (str): BigQuery table ID
            validation_records (List[Dict[str, Any]]): List of validation records
            
        Returns:
            Dict[str, int]: Statistics - {'successful': count, 'failed': count}
        """
        stats = {'successful': 0, 'failed': 0}
        
        #  check if the validation_records list is empty. If it is, return the stats dictionary.
        if not validation_records:
            return stats
            
        try:
            # Count validation results from the records themselves
            for record in validation_records:
                if record.get('validation_status') == 'PASS':
                    stats['successful'] += 1
                else:
                    stats['failed'] += 1

            logger.info(f'stats is {stats}')
            
            # Get a BQ Client handle
            client = bigquery.Client(project=project_id)
            # Get the table reference
            table_ref = client.dataset(dataset_id).table(table_id)
            
            # Batch insert List of validation records list object
            # The dictionary objects auto unpacks the key-value pairs into columns and values.
            errors = client.insert_rows_json(table_ref, validation_records)
            
            if errors:
                logger.error(
                    f"BigQuery batch insert failed: {len(validation_records)} records",
                    extra={
                        'record_count': len(validation_records),
                        'successful_validations': stats['successful'],
                        'failed_validations': stats['failed'],
                        'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                        'errors': errors,
                        'event_type': 'bigquery_batch_insert_failure'
                    }
                )
            else:
                logger.info(
                    f"BigQuery batch insert successful: {len(validation_records)} records ({stats['successful']} PASS, {stats['failed']} FAIL)",
                    extra={
                        'record_count': len(validation_records),
                        'successful_validations': stats['successful'],
                        'failed_validations': stats['failed'],
                        'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                        'event_type': 'bigquery_batch_insert_success'
                    }
                )
                
        except Exception as e:
            # Keep the validation counts we already calculated, but log the BigQuery exception
            # Don't override the actual validation statistics
            logger.error(
                f"BigQuery batch insert exception: {str(e)}",
                extra={
                    'record_count': len(validation_records),
                    'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                    'error_message': str(e),
                    'event_type': 'bigquery_batch_insert_exception'
                }
            )
            
        return stats