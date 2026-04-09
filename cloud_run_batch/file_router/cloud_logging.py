"""
Cloud Logging Module

Handles structured logging to Google Cloud Logging for operational monitoring,
real-time debugging, and alerting. This module focuses purely on Cloud Logging
operations without BigQuery persistence.

Key Responsibilities:
- Log validation results (PASS/FAIL) to Cloud Logging
- Record processing statistics and timing metrics
- Generate structured logs for operational monitoring
- Support real-time alerting and debugging
- Track file processing lifecycle events

Author: Manish Arora
Version: 1.0
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import uuid

# Configure logging
logger = logging.getLogger(__name__)

class CloudLogging:
    """
    Handles structured logging to Google Cloud Logging for operational visibility.
    
    This class provides methods for logging various file processing events and
    metrics to Cloud Logging with appropriate severity levels and structured data.
    """

    @staticmethod
    def log_validation_result(
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
        Log validation result for operational monitoring.
        
        Creates structured log entries for all file validation attempts
        to support real-time monitoring, alerting, and debugging.
        
        Args:
            bucket_name (str): Name of the GCS bucket
            filename (str): Original filename being processed
            metadata (Dict[str, Optional[str]]): Extracted file metadata
            success (bool): Whether validation was successful
            failed_check (Optional[str]): Name of the specific check that failed
            error_message (Optional[str]): Detailed error description
            expected_value (Optional[str]): What was expected (for failures)
            actual_value (Optional[str]): What was found (for failures)
            
        Returns:
            str: Validation ID for tracking and correlation
            
        Example:
            >>> CloudLogging.log_validation_result(
            ...     "my-bucket",
            ...     "customers_20260101.csv", 
            ...     {"entity_type": "customers", "load_type": "full"},
            ...     True
            ... )
            'validation_a3f9c2d1-...'
        """
        # Generate a new Validation ID
        validation_id = f"validation_{str(uuid.uuid4())[:8]}"
        
        # Build structured log entry
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
            'processor_version': '1.0',
            'event_type': 'file_validation'
        }
        
        # Log to Cloud Logging with appropriate severity
        # The below code snippet logs (system.out.println equivalent) in Java to Cloud Logging.
        # The logger.info() method signature is: logger.info(msg, *args, **kwargs)
        if success:
            logger.info(
                f"Validation SUCCESS: {filename} - {metadata.get('entity_type', 'unknown')}",
                # The extra parameter is a special keyword argument that the Python logging system recognizes. 
                # The extra= is essential for Cloud Logging integration to properly structure the log data.
                # When you pass extra={'key': 'value'}, the logging framework:
                # 1. Extracts those key-value pairs
                # 2. Adds them as attributes to the LogRecord object
                # 3. Makes them available to formatters and handlers (like Cloud Logging)
                extra=log_entry
            )
        else:
            logger.error(
                f"Validation FAILED: {filename} - {failed_check}: {error_message}",
                extra=log_entry
            )
        
        return validation_id

    @staticmethod
    def log_batch_processing_start(
        batch_id: str,
        file_count: int,
        processing_mode: str,
        max_workers: int
    ) -> None:
        """
        Log batch processing start event.
        
        Args:
            batch_id (str): Unique batch identifier
            file_count (int): Number of files in the batch
            processing_mode (str): Processing mode (e.g., 'standard', 'priority')
            max_workers (int): Maximum concurrent workers
        """
        # Logger.info and/or logger.error is used to log messages to Cloud Logging. Extra is essential for structured logging.
        logger.info(
            f"Batch processing STARTED: {batch_id} - {file_count} files with {max_workers} workers",
            extra={
                'batch_id': batch_id,
                'file_count': file_count,
                'processing_mode': processing_mode,
                'max_workers': max_workers,
                'event_type': 'batch_start',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )

    @staticmethod
    def log_batch_processing_complete(
        batch_id: str,
        total_files: int,
        successful_files: int,
        failed_files: int,
        processing_time_ms: int,
        throughput_files_per_second: float
    ) -> None:
        """
        Log batch processing completion with metrics.
        
        Args:
            batch_id (str): Unique batch identifier
            total_files (int): Total files processed
            successful_files (int): Number of successfully processed files
            failed_files (int): Number of failed files
            processing_time_ms (int): Total processing time
            throughput_files_per_second (float): Processing throughput
        """
        success_rate = (successful_files / total_files * 100) if total_files > 0 else 0
        
        logger.info(
            f"Batch processing COMPLETED: {batch_id} - {successful_files}/{total_files} files successful ({success_rate:.1f}%)",
            extra={
                'batch_id': batch_id,
                'total_files': total_files,
                'successful_files': successful_files,
                'failed_files': failed_files,
                'processing_time_ms': processing_time_ms,
                'throughput_files_per_second': throughput_files_per_second,
                'success_rate_percent': success_rate,
                'event_type': 'batch_complete',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )

    @staticmethod
    def log_file_processing_metrics(
        filename: str,
        validation_id: str,
        processing_time_ms: int,
        file_size_bytes: int,
        validation_status: str,
        destination_path: Optional[str] = None
    ) -> None:
        """
        Log individual file processing metrics.
        
        Args:
            filename (str): Name of the processed file
            validation_id (str): Validation ID for correlation
            processing_time_ms (int): File processing time
            file_size_bytes (int): Size of the file
            validation_status (str): PASS or FAIL
            destination_path (Optional[str]): Final destination path
        """
        throughput_mb_per_sec = (file_size_bytes / (1024 * 1024)) / (processing_time_ms / 1000) if processing_time_ms > 0 else 0
        
        logger.info(
            f"File processing metrics: {filename} - {validation_status} in {processing_time_ms}ms",
            extra={
                'filename': filename,
                'validation_id': validation_id,
                'processing_time_ms': processing_time_ms,
                'file_size_bytes': file_size_bytes,
                'validation_status': validation_status,
                'destination_path': destination_path,
                'throughput_mb_per_second': throughput_mb_per_sec,
                'event_type': 'file_metrics',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )

    @staticmethod
    def log_cloud_storage_operation(
        operation: str,
        source_path: str,
        destination_path: str,
        success: bool,
        duration_ms: int,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log Cloud Storage operations (copy, move, delete).
        
        Args:
            operation (str): Type of operation (copy, move, delete)
            source_path (str): Source file path
            destination_path (str): Destination file path
            success (bool): Whether operation succeeded
            duration_ms (int): Operation duration
            error_message (Optional[str]): Error details if failed
        """
        severity = logger.info if success else logger.error
        status = "SUCCESS" if success else "FAILED"
        
        severity(
            f"GCS {operation.upper()} {status}: {source_path} -> {destination_path} ({duration_ms}ms)",
            extra={
                'operation': operation,
                'source_path': source_path,
                'destination_path': destination_path,
                'success': success,
                'duration_ms': duration_ms,
                'error_message': error_message,
                'event_type': 'gcs_operation',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )

    @staticmethod
    def log_governance_event(
        event_type: str,
        entity_type: str,
        file_count: int,
        validation_results: Dict[str, int],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log governance and compliance events.
        
        Args:
            event_type (str): Type of governance event
            entity_type (str): Entity type being processed
            file_count (int): Number of files in the event
            validation_results (Dict[str, int]): Validation statistics
            additional_context (Optional[Dict[str, Any]]): Additional context
        """
        log_data = {
            'event_type': f'governance_{event_type}',
            'entity_type': entity_type,
            'file_count': file_count,
            'validation_results': validation_results,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if additional_context:
            log_data.update(additional_context)
        
        logger.info(
            f"Governance event: {event_type} for {entity_type} - {file_count} files processed",
            extra=log_data
        )