"""
File Metadata Extractor Module

Handles extraction of metadata from various filename patterns for the simplified data pipeline.
This module provides methods to parse different file naming conventions and extract
relevant metadata for downstream processing.

Key Responsibilities:
- Parse filename patterns to identify entity type (customers, orders, order_items, products)
- Determine load type (full or delta) from filename structure
- Extract date information from full load filenames
- Generate batch identifiers for delta files using current date
- Validate entity types against supported schema definitions
- Provide utilities for filename pattern validation and debugging

Supported Filename Patterns:
1. Full Load: {entity}_{YYYYMMDD}.csv
   - Example: customers_20260101.csv
   - Contains explicit date in filename
   
2. Delta Load: batch_{XX}_{entity}_delta.csv  
   - Example: batch_01_customers_delta.csv
   - Uses current date for partitioning (no date in filename)

Metadata Structure:
- entity_type: customers | orders | order_items | products
- load_type: full | delta
- batch_id: batch_XXX (delta files only, zero-padded)
- file_date: YYYYMMDD format
- original_filename: preserved for audit trail

Author: Manish Arora
Version: 1.0
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from . import settings

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
SUPPORTED_ENTITIES = settings.SUPPORTED_ENTITIES

class FileMetadataExtractor:
    """
    Handles extraction of metadata from various filename patterns.
    
    This class provides methods to parse different file naming conventions
    and extract relevant metadata for downstream processing.
    """

    @staticmethod
    def extract_file_metadata(filename: str) -> Dict[str, Optional[str]]:
        """
        Extract metadata from filename patterns for the simplified architecture.
        
        Supported patterns:
        1. Full snapshot: {entity}_{YYYYMMDD}.csv
        2. Delta files: batch_{XX}_{entity}_delta.csv (no date component)
        
        Args:
            filename (str): The source filename to parse
            
        Returns:
            Dict[str, Optional[str]]: Dictionary containing extracted metadata:
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
        # Create a dictionary to store the extracted metadata
        metadata = {
            'entity_type': None,
            'load_type': None,
            'batch_id': None,
            'file_date': None,
            'original_filename': filename
        }
        
        # Remove .csv extension for pattern matching
        basename = filename.replace('.csv', '').lower()
        logger.info(f"Extracting metadata from filename: {basename}")
        
        # Pattern 1: Full snapshot files (entity_YYYYMMDD)
        full_pattern = r'^([a-z_]+)_(\d{8})$'
        #  the below matches the pattern for full snapshot files. The actual File name is not being matched, but only the pattern.
        full_match = re.match(full_pattern, basename)
        
        if full_match:
            #  the below line extracts the entity and date from the filename
            entity, date_str = full_match.groups()
            logger.info(f"Extracted entity: {entity}, date: {date_str}")
            #  the below line checks if the entity is supported
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
            if entity in SUPPORTED_ENTITIES:
                # Use current date for delta files since they don't contain date
                current_date = datetime.now(timezone.utc).strftime('%Y%m%d')
                metadata.update({
                    'entity_type': entity,
                    'load_type': 'delta',
                    'batch_id': f'batch_{batch_num.zfill(3)}',  # batch_001, batch_002 etc
                    'file_date': current_date
                })
                logger.info(f"Matched delta pattern: entity={entity}, batch={batch_num}")
                return metadata
        
        logger.warning(f"No matching pattern found for filename: {filename}")
        return metadata

    @staticmethod
    def validate_entity_type(entity_type: str) -> bool:
        """
        Validate if the extracted entity type is supported.
        
        Args:
            entity_type (str): The entity type to validate
            
        Returns:
            bool: True if entity type is supported, False otherwise
        """
        return entity_type in SUPPORTED_ENTITIES

    @staticmethod 
    def get_supported_entities() -> set:
        """
        Get the set of supported entity types.
        
        Returns:
            set: Set of supported entity type strings
        """
        #  the copy() method is used to return a copy of the set, so that the original set is not modified.
        return SUPPORTED_ENTITIES.copy()