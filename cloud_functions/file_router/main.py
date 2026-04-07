"""
Cloud Run Batch Job: File Router for Data Pipeline

This batch job processes files in the inbox and routes them to appropriate 
folders based on entity type and load type (full/delta). It implements hive 
partitioning structure for downstream processing.

Trigger: Pub/Sub messages from Cloud Storage notifications or manual execution

Author: Generated with Claude Code
Version: 2.0
"""

import re
import json
import logging
import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
from google.cloud import storage
from google.cloud import pubsub_v1
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
SUPPORTED_ENTITIES = {'customers', 'orders', 'order_items', 'products'}
RAW_BUCKET_PREFIX = 'intelia-hackathon-dev-raw-data'
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '50'))
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
SUBSCRIPTION_NAME = os.getenv('PUBSUB_SUBSCRIPTION')
PULL_TIMEOUT = int(os.getenv('PULL_TIMEOUT', '300'))  # 5 minutes


class FileMetadataExtractor:
    """
    Handles extraction of metadata from various filename patterns.
    
    This class provides methods to parse different file naming conventions
    and extract relevant metadata for downstream processing.
    """

    # A Static method decorator is just like a static method in java
    # private static void main() 
    @staticmethod
    def extract_file_metadata(filename: str) -> Dict[str, Optional[str]]:
        """
        Extract metadata from filename patterns.
        
        Supported patterns:
        1. Full snapshot: {entity}_{YYYYMMDD}.csv
        2. Delta files: batch_{XX}_{entity}_delta.csv (no date component)
        
        Args:
            filename (str): The source filename to parse
            
        Returns:
            Dict[str, Optional[str]]: Dictionary containing extracted metadata:
            Optional[str] is used because the output argument may or not be present based on the file name.
                - entity_type: Type of data entity (customers, orders, etc.)
                - load_type: Type of load operation (full or delta)  
                - batch_id: Batch identifier for delta files
                - file_date: Date extracted from filename or current date
                - original_filename: Original filename for reference
                
        Example:
            >>> extract_file_metadata("customers_20260101.csv")
            {'entity_type': 'customers', 'load_type': 'full', 'file_date': '20260101', ...}
            
            >>> extract_file_metadata("batch_01_customers_delta.csv")
            {'entity_type': 'customers', 'load_type': 'delta', 'batch_id': 'batch_001', ...}
        """
        #  Create a dictionary to store the extracted metadata
        metadata = {
            'entity_type': None,
            'load_type': None,
            'batch_id': None,
            'file_date': None,
            'original_filename': filename
        }
        
        # Remove .csv extension for pattern matching
        basename = filename.replace('.csv', '').lower()
        logger.info(f"Basename: {basename}")
        
        # Pattern 1: Full snapshot files (entity_YYYYMMDD)
        full_pattern = r'^([a-z_]+)_(\d{8})$'
        full_match = re.match(full_pattern, basename)
        
        if full_match:
            entity, date_str = full_match.groups() # extract the entity and the date from the full_pattern
            if entity in SUPPORTED_ENTITIES:
                metadata.update({
                    'entity_type': entity,
                    'load_type': 'full',
                    'file_date': date_str
                })
                logger.info(f"Matched full snapshot pattern: entity={entity}, date={date_str}")
                return metadata
        
        # Pattern 2: Delta files (batch_XX_entity_delta) - no date component
        delta_pattern = r'^batch_(\d+)_([a-z_]+)_delta$'
        delta_match = re.match(delta_pattern, basename)
        
        if delta_match:
            batch_num, entity = delta_match.groups()
            # batch_num looks like 01, 02 etc
            if entity in SUPPORTED_ENTITIES:
                # Use current date for delta files since they don't contain date
                current_date = datetime.now(timezone.utc).strftime('%Y%m%d')
                metadata.update({
                    'entity_type': entity,
                    'load_type': 'delta',
                    'batch_id': f'batch_{batch_num.zfill(3)}', # batch_id looks like batch_001, batch_002 etc padded with zeros
                    'file_date': current_date
                })
                logger.info(f"Matched delta pattern: entity={entity}, batch={batch_num}")
                return metadata
        
        logger.warning(f"No matching pattern found for filename: {filename}")
        return metadata


class HivePartitionBuilder:
    """
    Builds hive-style partition paths for data organization.
    
    This class handles the creation of partitioned directory structures
    following hive conventions for efficient data querying.
    """

    @staticmethod
    def build_destination_path(metadata: Dict[str, Optional[str]]) -> Optional[str]:
        """
        Build hive-partitioned destination path.
        
        Creates directory structure following hive partitioning conventions:
        load_type={load_type}/entity_type={entity}/date={YYYY-MM-DD}/
        
        Args:
            metadata (Dict[str, Optional[str]]): File metadata containing:
                - entity_type: The data entity type
                - load_type: The type of load (full/delta)
                - file_date: Date in YYYYMMDD format
                
        Returns:
            Optional[str]: Hive-partitioned path string or None if metadata incomplete
            
        Example:
            >>> build_destination_path({
            ...     'entity_type': 'customers', 
            ...     'load_type': 'full', 
            ...     'file_date': '20260101'
            ... })
            'load_type=full/entity_type=customers/date=2026-01-01/'
        """
        entity = metadata.get('entity_type')
        load_type = metadata.get('load_type')
        file_date = metadata.get('file_date')
        
        # If arguments are missing then return None
        if not all([entity, load_type, file_date]):
            logger.error(f"Incomplete metadata for path building: {metadata}")
            return None
        
        # Validate date (YYYYMMDD format)
        try:
        #instead of writing our own code we take advantage of the existing functionality
            parsed_datetime = datetime.strptime(file_date, "%Y%m%d")
            year = parsed_datetime.year
            month = parsed_datetime.month
            day = parsed_datetime.day
            
            logger.info(f"Date components are valid: year={year}, month={month}, day={day}")    
                
        except (IndexError, ValueError) as e:
            logger.error(f"Date parsing error: {e}")
            return None
        
        # Build hive partitioned path with ISO date format
        iso_date = f"{year}-{month}-{day}"
        destination = f"load_type={load_type}/entity_type={entity}/date={iso_date}/"
        #  destination would look like load_type=full/entity_type=customers/date=2026-01-01/

        logger.info(f"Built destination path: {destination}")
        return destination

    @staticmethod
    def generate_destination_filename(metadata: Dict[str, Optional[str]]) -> str:
        """
        Generate simplified destination filename.
        
        Creates clean, readable filenames following simple conventions:
        - Full files: {entity}_full_{YYYY-MM-DD}.csv
        - Delta files: {entity}_delta_{batch_id}_{YYYY-MM-DD}.csv
        
        Args:
            metadata (Dict[str, Optional[str]]): File metadata containing:
                - entity_type: The data entity type
                - load_type: The type of load (full/delta)
                - file_date: Date in YYYYMMDD format
                - batch_id: Batch identifier (only for delta files)
                
        Returns:
            str: Clean, standardized filename
            
        Example:
            >>> # Full file
            >>> generate_destination_filename({
            ...     'entity_type': 'customers', 
            ...     'load_type': 'full',
            ...     'file_date': '20260101'
            ... })
            'customers_full_2026-01-01.csv'
            
            >>> # Delta file
            >>> generate_destination_filename({
            ...     'entity_type': 'customers', 
            ...     'load_type': 'delta',
            ...     'batch_id': 'batch_001',
            ...     'file_date': '20260101'
            ... })
            'customers_delta_batch_001_2026-01-01.csv'
        """
        entity = metadata['entity_type']
        load_type = metadata['load_type']
        file_date = metadata['file_date']
        
        # Convert YYYYMMDD to YYYY-MM-DD format
        year = file_date[:4]
        month = file_date[4:6]
        day = file_date[6:8]
        iso_date = f"{year}-{month}-{day}"
        
        if load_type == 'full':
            filename = f"{entity}_full_{iso_date}.csv"
        elif load_type == 'delta':
            batch_id = metadata.get('batch_id', 'batch_000')
            filename = f"{entity}_delta_{batch_id}_{iso_date}.csv"
        else:
            # Fallback for unexpected load types
            filename = f"{entity}_{load_type}_{iso_date}.csv"
        
        logger.info(f"Generated destination filename: {filename}")
        return filename


class CloudStorageFileManager:
    """
    Manages Cloud Storage file operations for the data pipeline.
    
    This class handles file copying, moving, and metadata operations
    within Google Cloud Storage buckets.
    """

    # Initialize the Cloud Storage client. __init__ method is a constructor that is called when an object of the class is created.
    def __init__(self):
        """
        Initialize the Cloud Storage client.
        
        Creates a connection to Google Cloud Storage using application
        default credentials.
        """
        self.client = storage.Client()
        logger.info("Initialized Cloud Storage client")

    async def copy_file_to_raw_folder(self, bucket_name: str, source_path: str, 
                                     dest_path: str, dest_filename: str) -> bool:
        """
        Copy file from inbox to raw folder with hive partitioning.
        
        Performs the core file routing operation by copying files from the
        inbox to the appropriate raw data location with proper partitioning.
        
        Args:
            bucket_name (str): Name of the GCS bucket
            source_path (str): Source file path in inbox/ folder
            dest_path (str): Destination folder path with hive partitions
            dest_filename (str): Standardized destination filename
            
        Returns:
            bool: True if copy operation successful, False otherwise
            
        Raises:
            Exception: For any Cloud Storage operation failures
            
        Example:
            >>> manager = CloudStorageFileManager()
            >>> success = manager.copy_file_to_raw_folder(
            ...     "my-bucket", 
            ...     "inbox/customers_20260101.csv",
            ...     "load_type=full/entity_type=customers/date=2026-01-01/",
            ...     "customers_full_2026-01-01.csv"
            ... )
        """
        try:
            # Obtain a reference to the bucket object
            bucket = self.client.bucket(bucket_name)
            
            # Get source blob - a reference to a file in a bucket
            source_blob = bucket.blob(source_path)
            
            # Check if source exists asynchronously
            exists_check = await asyncio.get_event_loop().run_in_executor(
                None, source_blob.exists
            )
            if not exists_check:
                logger.error(f"Source file does not exist: {source_path}")
                return False
            
            # Build full destination path
            full_dest_path = f"raw/{dest_path}{dest_filename}"
            dest_blob = bucket.blob(full_dest_path)
            logger.info(f"Destination path: {full_dest_path}")

            # Download and upload operations asynchronously
            source_content = await asyncio.get_event_loop().run_in_executor(
                None, source_blob.download_as_bytes
            )
            logger.info(f"Downloaded source content for: {source_path}")
            
            await asyncio.get_event_loop().run_in_executor(
                None, dest_blob.upload_from_string, source_content
            )
            logger.info(f"File content copied successfully: {source_path} -> {full_dest_path}")
            
            # Add processing metadata
            dest_blob.metadata = {
                'original_filename': source_path,
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'processor': 'file-router-cloud-function',
                'processor_version': '1.0'
            }
            
            # Patch metadata asynchronously
            await asyncio.get_event_loop().run_in_executor(
                None, dest_blob.patch
            )

            # Verify destination exists asynchronously
            dest_exists = await asyncio.get_event_loop().run_in_executor(
                None, dest_blob.exists
            )
            if dest_exists:
                logger.info(f"File copied successfully: {source_path} -> {full_dest_path}")
                return True
            else:
                logger.error(f"Destination file does not exist: {dest_path}")
                return False
            
        except Exception as e:
            logger.error(f"Error copying file {source_path}: {str(e)}")
            return False

    async def move_file_to_archive(self, bucket_name: str, source_path: str) -> bool:
        """
        Move processed file from inbox to archive folder.
        
        Archives the original file after successful processing to maintain
        a record of all processed files while keeping inbox clean.
        
        Args:
            bucket_name (str): Name of the GCS bucket
            source_path (str): Source file path in inbox/ folder
            
        Returns:
            bool: True if archive operation successful, False otherwise
            
        Example:
            >>> manager = CloudStorageFileManager()
            >>> success = manager.move_file_to_archive(
            ...     "my-bucket", 
            ...     "inbox/customers_20260101.csv"
            ... )
        """
        try:
            bucket = self.client.bucket(bucket_name)
            
            source_blob = bucket.blob(source_path)
            
            # Check if source exists asynchronously
            exists_check = await asyncio.get_event_loop().run_in_executor(
                None, source_blob.exists
            )
            if not exists_check:
                logger.warning(f"Source file for archive does not exist: {source_path}")
                return False
            
            # Extract filename from inbox path
            filename = source_path.replace('inbox/', '')
            archive_path = f"archive/{filename}"
            
            # Copy to archive asynchronously
            archive_blob = await asyncio.get_event_loop().run_in_executor(
                None, bucket.copy_blob, source_blob, bucket, archive_path
            )
            
            # Add archive metadata
            archive_blob.metadata = {
                'archived_at': datetime.now(timezone.utc).isoformat(),
                'original_location': source_path,
                'archived_by': 'file-router-function'
            }
            
            await asyncio.get_event_loop().run_in_executor(
                None, archive_blob.patch
            )
            
            # Delete original from inbox asynchronously
            await asyncio.get_event_loop().run_in_executor(
                None, source_blob.delete
            )
            
            logger.info(f"File archived: {source_path} -> {archive_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error archiving file {source_path}: {str(e)}")
            return False


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


class PubSubMessageHandler:
    """
    Handles Pub/Sub message processing for batch file operations.
    
    This class manages the extraction of file information from Pub/Sub
    messages triggered by Cloud Storage events.
    """

    @staticmethod
    def extract_file_info_from_message(message_data: Dict) -> Optional[Tuple[str, str]]:
        """
        Extract bucket name and file path from Pub/Sub message.
        
        Parses Cloud Storage event notifications received via Pub/Sub
        to extract the relevant file information for processing.
        
        Args:
            message_data (Dict): Pub/Sub message data containing Cloud Storage event
            
        Returns:
            Optional[Tuple[str, str]]: (bucket_name, file_path) or None if invalid
            
        Example:
            >>> extract_file_info_from_message({
            ...     'bucketId': 'my-bucket',
            ...     'objectId': 'inbox/customers_20260101.csv',
            ...     'eventType': 'OBJECT_FINALIZE'
            ... })
            ('my-bucket', 'inbox/customers_20260101.csv')
        """
        try:
            bucket_name = message_data.get('bucketId') or message_data.get('bucket')
            file_path = message_data.get('objectId') or message_data.get('name')
            
            if not bucket_name or not file_path:
                logger.warning(f"Invalid message data: {message_data}")
                return None
                
            # Only process files in inbox/
            if not file_path.startswith('inbox/'):
                logger.debug(f"Skipping file not in inbox: {file_path}")
                return None
                
            return bucket_name, file_path
            
        except Exception as e:
            logger.error(f"Error parsing message data: {e}")
            return None


class BatchFileProcessor:
    """
    Handles batch processing of multiple files with concurrent execution.
    
    This class manages the concurrent processing of multiple files using
    asyncio and thread pools for optimal performance.
    """

    def __init__(self, max_workers: int = MAX_WORKERS):
        """
        Initialize batch processor with specified worker count.
        
        Args:
            max_workers (int): Maximum number of concurrent workers
        """
        self.max_workers = max_workers
        self.file_router = FileRouter()
        logger.info(f"Batch processor initialized with {max_workers} workers")

    async def process_files_batch(self, file_list: List[Tuple[str, str]]) -> Dict[str, int]:
        """
        Process a batch of files concurrently.
        
        Processes multiple files in parallel using asyncio and returns
        summary statistics of the processing results.
        
        Args:
            file_list (List[Tuple[str, str]]): List of (bucket_name, file_path) tuples
            
        Returns:
            Dict[str, int]: Processing statistics with counts
            
        Example:
            >>> processor = BatchFileProcessor()
            >>> files = [('bucket', 'inbox/file1.csv'), ('bucket', 'inbox/file2.csv')]
            >>> result = await processor.process_files_batch(files)
            {'total': 2, 'success': 2, 'failed': 0}
        """
        if not file_list:
            logger.warning("No files to process in batch")
            return {'total': 0, 'success': 0, 'failed': 0}

        logger.info(f"Processing batch of {len(file_list)} files")
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_single_file(bucket_name: str, file_path: str) -> bool:
            async with semaphore:
                try:
                    return await self.file_router.process_file(bucket_name, file_path)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    return False

        # Process all files concurrently
        tasks = [
            process_single_file(bucket_name, file_path) 
            for bucket_name, file_path in file_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        success_count = sum(1 for r in results if r is True)
        failed_count = len(results) - success_count
        
        stats = {
            'total': len(file_list),
            'success': success_count,
            'failed': failed_count
        }
        
        logger.info(f"Batch processing completed: {stats}")
        return stats


class FileRouter:
    """
    Main file routing orchestrator for the data pipeline.
    
    This class coordinates all file processing operations including metadata
    extraction, file copying, archiving, and result logging.
    """

    def __init__(self):
        """
        Initialize file router with required components.
        
        Sets up the metadata extractor, partition builder, storage manager,
        and logger for coordinated file processing operations.
        """
        self.metadata_extractor = FileMetadataExtractor()
        self.partition_builder = HivePartitionBuilder()
        self.storage_manager = CloudStorageFileManager()
        self.logger = ProcessingLogger()
        logger.info("File router initialized successfully")

    async def process_file(self, bucket_name: str, file_path: str) -> bool:
        """
        Process a single file through the complete routing pipeline.
        
        Orchestrates the entire file processing workflow from metadata
        extraction through final archiving and logging.
        
        Args:
            bucket_name (str): Name of the GCS bucket
            file_path (str): Full path to the file in the bucket
            
        Returns:
            bool: True if processing completed successfully, False otherwise
            
        Processing Steps:
            1. Validate file is in inbox/ and is CSV format
            2. Extract metadata from filename
            3. Build hive-partitioned destination path
            4. Generate standardized destination filename
            5. Copy file to raw folder with partitioning
            6. Archive original file
            7. Log processing result
            
        Example:
            >>> router = FileRouter()
            >>> success = router.process_file(
            ...     "my-bucket", 
            ...     "inbox/customers_20260101.csv"
            ... )
        """
        logger.info(f"Starting file processing: gs://{bucket_name}/{file_path}")
        
        try:
            # Validate file location
            if not file_path.startswith('inbox/'):
                logger.info(f"Skipping file not in inbox/: {file_path}")
                return True  # Not an error, just not our responsibility
            
            # Extract filename
            filename_only = file_path.replace('inbox/', '')
            
            # Skip hidden files and directories
            if filename_only.startswith('.') or '/' in filename_only:
                logger.info(f"Skipping hidden file or directory: {filename_only}")
                return True
            
            # Validate CSV format
            if not filename_only.lower().endswith('.csv'):
                error_msg = "Only CSV files are supported"
                logger.warning(f"Skipping non-CSV file: {filename_only}")
                self.logger.log_processing_result(bucket_name, filename_only, {}, 
                                                False, error_msg)
                return False
            
            # Extract file metadata
            metadata = self.metadata_extractor.extract_file_metadata(filename_only)
            
            if not metadata['entity_type']:
                error_msg = "Filename does not match expected patterns"
                logger.error(f"Unable to parse filename pattern: {filename_only}")
                self.logger.log_processing_result(bucket_name, filename_only, 
                                                metadata, False, error_msg)
                return False
            
            logger.info(f"Extracted metadata: {metadata}")
            
            # Build destination path
            dest_path = self.partition_builder.build_destination_path(metadata)
            if not dest_path:
                error_msg = "Unable to build destination path from metadata"
                logger.error(f"Path building failed for metadata: {metadata}")
                self.logger.log_processing_result(bucket_name, filename_only, 
                                                metadata, False, error_msg)
                return False
            
            # Generate destination filename
            dest_filename = self.partition_builder.generate_destination_filename(metadata)
            
            # Copy file to raw folder
            copy_success = await self.storage_manager.copy_file_to_raw_folder(
                bucket_name, file_path, dest_path, dest_filename
            )
            
            if not copy_success:
                error_msg = "Failed to copy file to raw folder"
                self.logger.log_processing_result(bucket_name, filename_only, 
                                                metadata, False, error_msg)
                return False
            
            # Archive original file
            archive_success = await self.storage_manager.move_file_to_archive(
                bucket_name, file_path
            )
            
            if not archive_success:
                logger.warning(f"File copy succeeded but archiving failed: {filename_only}")
                # Don't fail the entire process for archive failure
            
            # Log success
            self.logger.log_processing_result(bucket_name, filename_only, 
                                            metadata, True)
            
            logger.info(f"File processing completed successfully: {filename_only}")
            return True
            
        except Exception as e:
            error_msg = f"Unexpected processing error: {str(e)}"
            logger.error(error_msg)
            filename = file_path.split('/')[-1] if '/' in file_path else file_path
            self.logger.log_processing_result(bucket_name, filename, {}, 
                                            False, error_msg)
            return False


class CloudRunBatchJobManager:
    """
    Manages Cloud Run batch job execution for file processing.
    
    This class handles the main execution loop for the Cloud Run job,
    including Pub/Sub message processing and batch file handling.
    """

    def __init__(self):
        """
        Initialize the Cloud Run batch job manager.
        
        Sets up Pub/Sub client, batch processor, and message handler
        for processing files in batches.
        """
        self.subscriber_client = pubsub_v1.SubscriberClient()
        self.batch_processor = BatchFileProcessor()
        self.message_handler = PubSubMessageHandler()
        
        if PROJECT_ID and SUBSCRIPTION_NAME:
            self.subscription_path = self.subscriber_client.subscription_path(
                PROJECT_ID, SUBSCRIPTION_NAME
            )
        else:
            self.subscription_path = None
            logger.warning("PROJECT_ID or SUBSCRIPTION_NAME not set - running in manual mode")

    async def process_pubsub_messages(self) -> Dict[str, int]:
        """
        Process pending Pub/Sub messages in batches.
        
        Pulls messages from the subscription, extracts file information,
        and processes files in batches for optimal performance.
        
        Returns:
            Dict[str, int]: Processing statistics
            
        Example:
            >>> manager = CloudRunBatchJobManager()
            >>> stats = await manager.process_pubsub_messages()
            {'total': 15, 'success': 14, 'failed': 1}
        """
        if not self.subscription_path:
            logger.error("Cannot process Pub/Sub messages - subscription not configured")
            return {'total': 0, 'success': 0, 'failed': 0}

        logger.info(f"Pulling messages from subscription: {self.subscription_path}")
        
        file_list = []
        ack_ids = []
        
        try:
            # Pull messages from subscription
            pull_request = pubsub_v1.PullRequest(
                subscription=self.subscription_path,
                max_messages=BATCH_SIZE
            )
            
            response = self.subscriber_client.pull(
                request=pull_request, timeout=PULL_TIMEOUT
            )
            
            logger.info(f"Pulled {len(response.received_messages)} messages")
            
            # Extract file information from messages
            for received_message in response.received_messages:
                try:
                    message_data = json.loads(received_message.message.data.decode('utf-8'))
                    file_info = self.message_handler.extract_file_info_from_message(message_data)
                    
                    if file_info:
                        file_list.append(file_info)
                        ack_ids.append(received_message.ack_id)
                    else:
                        # Acknowledge invalid messages to remove them from queue
                        self.subscriber_client.acknowledge(
                            subscription=self.subscription_path,
                            ack_ids=[received_message.ack_id]
                        )
                        
                except Exception as e:
                    logger.error(f"Error parsing message: {e}")
                    # Acknowledge unparseable messages
                    self.subscriber_client.acknowledge(
                        subscription=self.subscription_path,
                        ack_ids=[received_message.ack_id]
                    )
            
            # Process files in batch
            if file_list:
                stats = await self.batch_processor.process_files_batch(file_list)
                
                # Acknowledge all processed messages
                if ack_ids:
                    self.subscriber_client.acknowledge(
                        subscription=self.subscription_path,
                        ack_ids=ack_ids
                    )
                    logger.info(f"Acknowledged {len(ack_ids)} messages")
                
                return stats
            else:
                logger.info("No valid files to process in this batch")
                return {'total': 0, 'success': 0, 'failed': 0}
                
        except Exception as e:
            logger.error(f"Error processing Pub/Sub messages: {e}")
            return {'total': 0, 'success': 0, 'failed': 0}

    async def process_inbox_scan(self, bucket_name: str) -> Dict[str, int]:
        """
        Scan inbox folder and process all files found.
        
        Alternative processing mode that scans the inbox folder directly
        instead of relying on Pub/Sub messages. Useful for backfill operations.
        
        Args:
            bucket_name (str): Name of the bucket to scan
            
        Returns:
            Dict[str, int]: Processing statistics
            
        Example:
            >>> manager = CloudRunBatchJobManager()
            >>> stats = await manager.process_inbox_scan('my-bucket')
            {'total': 25, 'success': 24, 'failed': 1}
        """
        logger.info(f"Scanning inbox folder in bucket: {bucket_name}")
        
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            
            # List all files in inbox/ prefix
            blobs = bucket.list_blobs(prefix='inbox/')
            file_list = []
            
            for blob in blobs:
                # Skip directories and hidden files
                if blob.name.endswith('/') or '.' in blob.name.split('/')[-1][0]:
                    continue
                    
                if blob.name.lower().endswith('.csv'):
                    file_list.append((bucket_name, blob.name))
            
            logger.info(f"Found {len(file_list)} files in inbox")
            
            if file_list:
                return await self.batch_processor.process_files_batch(file_list)
            else:
                return {'total': 0, 'success': 0, 'failed': 0}
                
        except Exception as e:
            logger.error(f"Error scanning inbox: {e}")
            return {'total': 0, 'success': 0, 'failed': 0}

    async def run_batch_job(self) -> Dict[str, int]:
        """
        Main execution method for the Cloud Run batch job.
        
        Determines execution mode (Pub/Sub vs inbox scan) and processes
        files accordingly. Returns processing statistics.
        
        Returns:
            Dict[str, int]: Combined processing statistics
        """
        logger.info("Starting Cloud Run batch job execution")
        
        total_stats = {'total': 0, 'success': 0, 'failed': 0}
        
        # Check for manual bucket scan mode
        manual_bucket = os.getenv('MANUAL_BUCKET_SCAN')
        if manual_bucket:
            logger.info(f"Running in manual bucket scan mode for: {manual_bucket}")
            stats = await self.process_inbox_scan(manual_bucket)
        else:
            # Process Pub/Sub messages
            stats = await self.process_pubsub_messages()
        
        # Aggregate statistics
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
        
        logger.info(f"Batch job completed. Final stats: {total_stats}")
        return total_stats


async def main():
    """
    Cloud Run batch job entry point.
    
    This is the main entry point for the Cloud Run job that processes
    file routing operations in batches for optimal performance.
    
    Environment Variables:
        - GOOGLE_CLOUD_PROJECT: GCP project ID
        - PUBSUB_SUBSCRIPTION: Pub/Sub subscription name
        - MAX_WORKERS: Maximum concurrent workers (default: 10)
        - BATCH_SIZE: Maximum messages to pull per batch (default: 50)
        - PULL_TIMEOUT: Pub/Sub pull timeout in seconds (default: 300)
        - MANUAL_BUCKET_SCAN: Bucket name for manual scan mode (optional)
        
    Returns:
        None
    """
    try:
        logger.info("Starting Cloud Run file router batch job")
        
        # Initialize and run batch job manager
        job_manager = CloudRunBatchJobManager()
        final_stats = await job_manager.run_batch_job()
        
        logger.info(f"Batch job execution completed successfully: {final_stats}")
        
        # Exit with appropriate code based on results
        if final_stats['failed'] > 0:
            logger.warning(f"Some files failed processing: {final_stats['failed']}")
            sys.exit(1)  # Partial failure
        else:
            sys.exit(0)  # Success
            
    except Exception as e:
        logger.error(f"Critical error in batch job execution: {str(e)}")
        sys.exit(2)  # Critical failure


# For local testing and development
if __name__ == "__main__":
    print("Starting local Cloud Run batch job test...")
    
    # Set test environment variables if not already set
    if not os.getenv('GOOGLE_CLOUD_PROJECT'):
        os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
    if not os.getenv('MANUAL_BUCKET_SCAN'):
        os.environ['MANUAL_BUCKET_SCAN'] = 'test-bucket'
    
    asyncio.run(main())