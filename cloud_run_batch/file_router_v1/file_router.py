"""
File Router Module

Main file routing orchestrator for the data pipeline.
This module coordinates all file processing operations including metadata
extraction, file copying, archiving, and result logging.

Author: Generated with Claude Code
Version: 1.0
"""

import logging
from .file_metadata_extractor import FileMetadataExtractor
from .hive_partition_builder import HivePartitionBuilder
from .cloud_storage_manager import CloudStorageFileManager
from .processing_logger import ProcessingLogger

# Configure logging
logger = logging.getLogger(__name__)


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
            >>> success = await router.process_file(
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