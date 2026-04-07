"""
Pub/Sub Message Handler Module

Handles Pub/Sub message processing for batch file operations.
This module manages the extraction of file information from Pub/Sub
messages triggered by Cloud Storage events.

Author: Manish Arora
Version: 1.0
"""

import logging
from typing import Dict, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)


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