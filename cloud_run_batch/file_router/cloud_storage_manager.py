"""
Cloud Storage Manager Module

Manages Cloud Storage file operations for the data pipeline.
This module handles file copying, moving, and metadata operations
within Google Cloud Storage buckets with asynchronous support.

Author: Generated with Claude Code
Version: 1.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from google.cloud import storage

# Configure logging
logger = logging.getLogger(__name__)


class CloudStorageFileManager:
    """
    Manages Cloud Storage file operations for the data pipeline.
    
    This class handles file copying, moving, and metadata operations
    within Google Cloud Storage buckets.
    """

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
            >>> success = await manager.copy_file_to_raw_folder(
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
            >>> success = await manager.move_file_to_archive(
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