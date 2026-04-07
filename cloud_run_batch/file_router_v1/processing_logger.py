"""
Processing Logger Module

Handles logging of file processing results for governance and monitoring.
This module provides structured logging capabilities for tracking all
file processing operations and their outcomes.

Author: Generated with Claude Code
Version: 1.0
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)


class ProcessingLogger:
    """
    Handles logging of file processing results for governance and monitoring.
    
    This class provides structured logging capabilities for tracking all
    file processing operations and their outcomes.
    """

    @staticmethod
    def log_processing_result(bucket_name: str, filename: str, 
                            metadata: Dict[str, Optional[str]], success: bool, 
                            error_message: Optional[str] = None) -> None:
        """
        Log processing result for governance tracking.
        
        Creates structured log entries for all file processing attempts,
        successful or failed, to support monitoring and debugging.
        
        Note: In production, this would insert records into BigQuery 
        governance.validation_log table. Currently logs to Cloud Logging.
        
        Args:
            bucket_name (str): Name of the GCS bucket
            filename (str): Original filename being processed
            metadata (Dict[str, Optional[str]]): Extracted file metadata
            success (bool): Whether processing was successful
            error_message (Optional[str]): Error details if processing failed
            
        Returns:
            None
            
        Example:
            >>> ProcessingLogger.log_processing_result(
            ...     "my-bucket",
            ...     "customers_20260101.csv", 
            ...     {"entity_type": "customers", "load_type": "full"},
            ...     True
            ... )
        """
        log_entry = {
            'file_path': f"gs://{bucket_name}/inbox/{filename}",
            'entity_type': metadata.get('entity_type'),
            'load_type': metadata.get('load_type'),
            'batch_id': metadata.get('batch_id'),
            'file_date': metadata.get('file_date'),
            'validation_status': 'SUCCESS' if success else 'FAILED',
            'failed_check': None if success else 'FILE_ROUTING',
            'expected_value': 'valid_filename_pattern',
            'actual_value': filename,
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'error_message': error_message,
            'processor': 'file-router-function',
            'processor_version': '1.0'
        }
        
        if success:
            logger.info(f"Processing SUCCESS: {json.dumps(log_entry, indent=2)}")
        else:
            logger.error(f"Processing FAILED: {json.dumps(log_entry, indent=2)}")