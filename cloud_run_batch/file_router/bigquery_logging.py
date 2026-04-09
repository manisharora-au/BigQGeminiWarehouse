"""
BigQuery Logging Module

Handles long-term persistence of governance and audit data to BigQuery.
This module focuses purely on BigQuery operations for compliance and
historical analysis requirements.

Key Responsibilities:
- Write validation results to governance.validation_log table
- Persist audit trails for compliance requirements
- Support long-term data retention and analysis
- Batch insert operations for performance
- Handle BigQuery schema and table management

Author: Manish Arora
Version: 1.0
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from google.cloud import bigquery

# Configure logging
logger = logging.getLogger(__name__)


class BigQueryLogging:
    """
    Handles persistence of governance and audit data to BigQuery.
    
    This class provides methods for writing validation results and audit
    information to BigQuery for long-term compliance and analysis.
    """

    @staticmethod
    def create_validation_log_record(
        validation_id: str,
        bucket_name: str,
        filename: str,
        metadata: Dict[str, Optional[str]],
        success: bool,
        failed_check: Optional[str] = None,
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a validation log record for BigQuery insertion.
        
        Args:
            validation_id (str): Unique validation identifier
            bucket_name (str): GCS bucket name
            filename (str): Original filename
            metadata (Dict[str, Optional[str]]): Extracted file metadata
            success (bool): Whether validation was successful
            failed_check (Optional[str]): Name of failed validation check
            expected_value (Optional[str]): Expected value for failed check
            actual_value (Optional[str]): Actual value found
            error_message (Optional[str]): Detailed error message
            
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
            validation_record (Dict[str, Any]): Record created by create_validation_log_record()
            
        Returns:
            bool: True if insert successful, False otherwise
        """
        try:
            # Get a BQ Client handle
            client = bigquery.Client(project=project_id)
            # Get the table reference
            table_ref = client.dataset(dataset_id).table(table_id)
            
            # Insert the record
            # The API / method needs a list of dictionaries as input to insert data
            errors = client.insert_rows_json(table_ref, [validation_record])
            
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
        
        # Check if the validation_records list is empty. If it is, return the stats dictionary.
        if not validation_records:
            return stats
            
        try:
            # Count validation results from the records themselves
            for record in validation_records:
                if record.get('validation_status') == 'PASS':
                    stats['successful'] += 1
                else:
                    stats['failed'] += 1
            
            client = bigquery.Client(project=project_id)
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
            logger.error(
                f"BigQuery batch insert exception: {str(e)}",
                extra={
                    'record_count': len(validation_records),
                    'successful_validations': stats['successful'],
                    'failed_validations': stats['failed'],
                    'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                    'error_message': str(e),
                    'event_type': 'bigquery_batch_insert_exception'
                }
            )
            
        return stats

    @staticmethod
    def create_batch_processing_record(
        batch_id: str,
        total_files: int,
        successful_files: int,
        failed_files: int,
        processing_time_ms: int,
        throughput_files_per_second: float,
        entity_types_processed: List[str]
    ) -> Dict[str, Any]:
        """
        Create a batch processing record for BigQuery governance tracking.
        
        Args:
            batch_id (str): Unique batch identifier
            total_files (int): Total files processed
            successful_files (int): Successfully processed files
            failed_files (int): Failed files
            processing_time_ms (int): Total processing time
            throughput_files_per_second (float): Processing throughput
            entity_types_processed (List[str]): List of entity types in batch
            
        Returns:
            Dict[str, Any]: Structured record for BigQuery insertion
        """
        return {
            'batch_id': batch_id,
            'batch_timestamp': datetime.now(timezone.utc),
            'total_files': total_files,
            'successful_files': successful_files,
            'failed_files': failed_files,
            'processing_time_ms': processing_time_ms,
            'throughput_files_per_second': throughput_files_per_second,
            'success_rate_percent': (successful_files / total_files * 100) if total_files > 0 else 0,
            'entity_types_processed': entity_types_processed,
            'processor': 'cloud-run-validator',
            'processor_version': '1.0'
        }

    @staticmethod
    def write_batch_processing_record(
        project_id: str,
        dataset_id: str,
        table_id: str,
        batch_record: Dict[str, Any]
    ) -> bool:
        """
        Write batch processing record to BigQuery for governance tracking.
        
        Args:
            project_id (str): GCP project ID
            dataset_id (str): BigQuery dataset ID
            table_id (str): BigQuery table ID (e.g., 'batch_processing_log')
            batch_record (Dict[str, Any]): Batch processing record
            
        Returns:
            bool: True if insert successful, False otherwise
        """
        try:
            # Get a BQ Client handle
            client = bigquery.Client(project=project_id)
            # Get the table reference
            table_ref = client.dataset(dataset_id).table(table_id)
            
            errors = client.insert_rows_json(table_ref, [batch_record])
            
            if errors:
                logger.error(
                    f"BigQuery batch record insert failed: {errors}",
                    extra={
                        'batch_id': batch_record.get('batch_id'),
                        'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                        'errors': errors,
                        'event_type': 'bigquery_batch_record_failure'
                    }
                )
                return False
            else:
                logger.info(
                    f"BigQuery batch record inserted: {batch_record.get('batch_id')}",
                    extra={
                        'batch_id': batch_record.get('batch_id'),
                        'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                        'event_type': 'bigquery_batch_record_success'
                    }
                )
                return True
                
        except Exception as e:
            logger.error(
                f"BigQuery batch record exception: {str(e)}",
                extra={
                    'batch_id': batch_record.get('batch_id'),
                    'table_ref': f"{project_id}.{dataset_id}.{table_id}",
                    'error_message': str(e),
                    'event_type': 'bigquery_batch_record_exception'
                }
            )
            return False