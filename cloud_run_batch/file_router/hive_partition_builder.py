"""
Hive Partition Builder Module

Builds hive-style partition paths for data organization in the data pipeline.
This module handles the creation of partitioned directory structures following
hive conventions for efficient data querying.

Author: Generated with Claude Code
Version: 1.0
"""

import logging
from typing import Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)


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
            if len(file_date) != 8 or not file_date.isdigit():
                raise ValueError(f"Invalid date format: {file_date}")

            logger.info(f"Date format is valid: {file_date}")    
            
            # Parse date components for validation
            year = file_date[:4]
            month = file_date[4:6]
            day = file_date[6:8]
            
            # Validate date components: Date should be between 1 and 31 and month between 1 and 12
            if not (1 <= int(month) <= 12 and 1 <= int(day) <= 31):
                raise ValueError(f"Invalid month/day values: month={month}, day={day}")
            
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