"""
File Metadata Extractor Module

Handles extraction of metadata from various filename patterns for the data pipeline.
This module provides methods to parse different file naming conventions and extract
relevant metadata for downstream processing.

Author: Generated with Claude Code
Version: 1.0
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
SUPPORTED_ENTITIES = {'customers', 'orders', 'order_items', 'products'}


class FileMetadataExtractor:
    """
    Handles extraction of metadata from various filename patterns.
    
    This class provides methods to parse different file naming conventions
    and extract relevant metadata for downstream processing.
    """

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