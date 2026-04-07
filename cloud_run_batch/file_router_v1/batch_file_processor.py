"""
Batch File Processor Module

Handles batch processing of multiple files with concurrent execution.
This module manages the concurrent processing of multiple files using
asyncio and thread pools for optimal performance.

Author: Generated with Claude Code
Version: 1.0
"""

import asyncio
import logging
import os
from typing import Dict, List, Tuple
from .file_router import FileRouter

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))

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