"""
Hive Partition Builder Module

Builds hive-style partition paths for data organization in the validated/ layer only.
This module handles the creation of partitioned directory structures following
hive conventions for efficient BigQuery querying in the simplified architecture.

Key Responsibilities:
- Generate hive-partitioned paths for validated/ layer only
- Convert YYYYMMDD format to ISO date format (YYYY-MM-DD) for BigQuery compatibility
- Build quarantine paths with flat structure for manual review
- Generate standardized filenames for validated files
- Validate date components and handle formatting errors
- Extract partition information for debugging and governance

Partitioning Strategy:
- inbox/: Flat structure (no partitioning)
- validated/: Full hive partitioning applied by Validator
  - Pattern: validated/load_type={full|delta}/entity_type={entity}/date={YYYY-MM-DD}/
  - Examples: 
    - validated/load_type=full/entity_type=customers/date=2026-01-01/
    - validated/load_type=delta/entity_type=orders/date=2026-01-15/
- quarantine/: Flat structure for failed files (no partitioning)

Filename Conventions:
- Full files: {entity}_full_{YYYY-MM-DD}.csv
- Delta files: {entity}_delta_{batch_id}_{YYYY-MM-DD}.csv
- Preserves original filename in quarantine for audit trail

Author: Manish Arora
Version: 1.0
"""

import logging
from typing import Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

class HivePartitionBuilder:
    """
    Builds hive-style partition paths for the validated/ layer.
    
    This class handles the creation of partitioned directory structures
    following hive conventions for efficient data querying. Partitioning
    is only applied when files are moved to the validated/ layer.
    """

    # The difference between a static method and a normal method is that a static method is not bound to a class or an instance of a class.
    
    @staticmethod
    def build_validated_destination_path(metadata: Dict[str, Optional[str]]) -> Optional[str]:
        """
        Build hive-partitioned destination path for the validated/ layer.
        
        Creates directory structure following hive partitioning conventions:
        validated/load_type={load_type}/entity_type={entity}/date={YYYY-MM-DD}/
        
        Args:
            metadata (Dict[str, Optional[str]]): File metadata containing:
                - entity_type: The data entity type
                - load_type: The type of load (full/delta)
                - file_date: Date in YYYYMMDD format
                
        Returns:
            Optional[str]: Hive-partitioned path string or None if metadata incomplete
            
        Example: Full Refresh File
            >>> build_validated_destination_path({
            ...     'entity_type': 'customers', 
            ...     'load_type': 'full', 
            ...     'file_date': '20260101'
            ... })
            'validated/load_type=full/entity_type=customers/date=2026-01-01/'

        Example: Delta Refresh File
            >>> build_validated_destination_path({
            ...     'entity_type': 'orders', 
            ...     'load_type': 'delta', 
            ...     'batch_id': 'batch_001',
            ...     'file_date': '20260101'
            ... })
            'validated/load_type=delta/entity_type=orders/date=2026-01-01/'
        """
        entity = metadata.get('entity_type')
        load_type = metadata.get('load_type')
        if load_type == 'delta' and metadata.get('batch_id') is not None: 
            batch_id = metadata.get('batch_id')
        file_date = metadata.get('file_date')
        
        # Validate required metadata is present
        if load_type == 'delta':
            #  check if all required metadata is present for delta files
            if not all([entity, load_type, file_date, batch_id]):
                #  check which of the metadata is missing
                missing_metadata = [key for key, value in metadata.items() if value is None]
                logger.error(f"Incomplete metadata for path building: {missing_metadata}")
                return None
        else:
            #  check if all required metadata is present for full files
            if not all([entity, load_type, file_date]):
                missing_metadata = [key for key, value in metadata.items() if value is None]
                logger.error(f"Incomplete metadata for path building: {missing_metadata}")
                return None
        
        # Validate and convert date (YYYYMMDD format to YYYY-MM-DD)
        try:
            if len(file_date) != 8 or not file_date.isdigit():
                raise ValueError(f"Invalid date format: {file_date}")

            logger.debug(f"Date format is valid: {file_date}")    
            
            # Parse date components for validation
            year = file_date[:4]
            month = file_date[4:6]
            day = file_date[6:8]
            
            # Validate date components
            if not (1 <= int(month) <= 12 and 1 <= int(day) <= 31 and 1 <= int(year) <= 9999):
                raise ValueError(f"Invalid month/day values: month={month}, day={day}, year={year}")
            
            logger.debug(f"Date components are valid: year={year}, month={month}, day={day}")    
                
        except (IndexError, ValueError) as e:
            logger.error(f"Date parsing error: {e}")
            return None
        
        # Build hive partitioned path with ISO date format for validated/ layer
        iso_date = f"{year}-{month}-{day}"
        destination = f"validated/load_type={load_type}/entity_type={entity}/date={iso_date}/"
        
        logger.info(f"Built validated destination path: {destination}")
        return destination

    @staticmethod
    def build_quarantine_destination_path(filename: str) -> str:
        """
        Build destination path for quarantined files (flat structure).
        
        Quarantined files are stored in a flat structure without partitioning
        to simplify manual review and reprocessing.
        
        Args:
            filename (str): Original filename
            
        Returns:
            str: Quarantine destination path
            
        Example:
            >>> build_quarantine_destination_path("customers_20260101.csv")
            'quarantine/customers_20260101.csv'
        """
        quarantine_path = f"quarantine/{filename}"
        logger.info(f"Built quarantine destination path: {quarantine_path}")
        return quarantine_path

    @staticmethod
    def generate_validated_filename(metadata: Dict[str, Optional[str]]) -> str:
        """
        Generate clean destination filename for validated files.
        
        Creates standardized filenames following simple conventions:
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
            >>> generate_validated_filename({
            ...     'entity_type': 'customers', 
            ...     'load_type': 'full',
            ...     'file_date': '20260101'
            ... })
            'customers_full_2026-01-01.csv'
            
            >>> # Delta file
            >>> generate_validated_filename({
            ...     'entity_type': 'customers', 
            ...     'load_type': 'delta',
            ...     'batch_id': 'batch_001',
            ...     'file_date': '20260101'
            ... })
            'customers_delta_batch_001_2026-01-01.csv'
        """
        entity = metadata.get('entity_type')
        load_type = metadata.get('load_type')
        file_date = metadata.get('file_date')
        
        # Convert YYYYMMDD to YYYY-MM-DD format
        year = file_date[:4]
        month = file_date[4:6]
        day = file_date[6:8]
        # since build_validated_destination_path will have been executed earlier, there is no need to perform any further date, year, 
        # and month validation
        iso_date = f"{year}-{month}-{day}"
        
        if load_type == 'full':
            filename = f"{entity}_full_{iso_date}.csv"
        elif load_type == 'delta':
            #  get batch_id from metadata
            batch_id = metadata.get('batch_id', 'batch_000')
            filename = f"{entity}_delta_{batch_id}_{iso_date}.csv"
        else:
            # Fallback for unexpected load types
            filename = f"{entity}_{load_type}_{iso_date}.csv"
        
        logger.info(f"Generated validated filename: {filename}")
        return filename

    @staticmethod
    #  The prupose of this method is to extract partition information from a validated path.
    #  This method is not used in the current pipeline.
    def extract_partition_info(validated_path: str) -> Optional[Dict[str, str]]:
        """
        Extract partition information from a validated path.
        
        Useful for debugging and governance logging to understand
        what partitions were created.
        
        Args:
            validated_path (str): Path in validated/ with hive partitions
            
        Returns:
            Optional[Dict[str, str]]: Partition key-value pairs or None if invalid
            
        Example:
            >>> extract_partition_info("validated/load_type=full/entity_type=customers/date=2026-01-01/")
            {'load_type': 'full', 'entity_type': 'customers', 'date': '2026-01-01'}
        """
        import re
        
        # Extract partition key-value pairs using regex
        partition_pattern = r'(\w+)=([^/]+)'
        matches = re.findall(partition_pattern, validated_path)
        
        if not matches:
            logger.warning(f"No partition information found in path: {validated_path}")
            return None
            
        partition_info = dict(matches)
        logger.debug(f"Extracted partition info: {partition_info}")
        return partition_info