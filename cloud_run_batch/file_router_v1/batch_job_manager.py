"""
Cloud Run Batch Job Manager Module

Manages Cloud Run batch job execution for file processing.
This module handles the main execution loop for the Cloud Run job,
including Pub/Sub message processing and batch file handling.

Author: Manish Arora
Version: 1.0
"""

import asyncio
import json
import logging
import os
from typing import Dict
from google.cloud import storage, pubsub_v1
from .batch_file_processor import BatchFileProcessor
from .pubsub_message_handler import PubSubMessageHandler

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
SUBSCRIPTION_NAME = os.getenv('PUBSUB_SUBSCRIPTION')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '50'))
PULL_TIMEOUT = int(os.getenv('PULL_TIMEOUT', '300'))  # 5 minutes

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

        pubsub_v1.SubscriberClient() is used for pulling messages from Pub/Sub subscription.
        PubSubMessageHandler is a custom class and used for extracting file information from messages.
        BatchFileProcessor is a custom class and used for processing files in batches.
        """
        self.subscriber_client = pubsub_v1.SubscriberClient()
        self.batch_processor = BatchFileProcessor()
        self.message_handler = PubSubMessageHandler()
        
        if PROJECT_ID and SUBSCRIPTION_NAME:
            # subscription path is the path to the subscription in the format projects/{project_id}/subscriptions/{subscription_name}
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