"""
Cloud Run Batch Job: File Router for Data Pipeline

Main orchestrator for the Cloud Run batch job that processes files in the inbox
and routes them to appropriate folders based on entity type and load type.

This module serves as the entry point and orchestrates all components following
separation of concerns principles.

Author: Manish Arora
Version: 1.0
"""

import asyncio
import logging
import os
import sys
from file_router import CloudRunBatchJobManager
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# this creates an asynchronous main function that will be called by the Cloud Run job
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
        
    Exit Codes:
        0: Success - All files processed successfully
        1: Partial failure - Some files failed processing
        2: Critical failure - Job execution failed
    """
    try:
        logger.info("Starting Cloud Run file router batch job")
        
        # Initialize and run batch job manager
        # The Cloud Run Batch Manager is the main orchestrator for the batch job
        job_manager = CloudRunBatchJobManager()
        # final_stats is a dictionary object with keys: total, success, failed
        final_stats = await job_manager.run_batch_job()
        logger.info(f"Batch job execution completed: {final_stats}")
        
        # Exit with appropriate code based on results
        if final_stats['total'] == 0:
            logger.info("No files to process")
            sys.exit(0)  # Success - nothing to do
        elif final_stats['failed'] > 0:
            logger.warning(f"Some files failed processing: {final_stats['failed']} out of {final_stats['total']}")
            sys.exit(1)  # Partial failure
        else:
            logger.info(f"All {final_stats['success']} files processed successfully")
            sys.exit(0)  # Success
            
    except Exception as e:
        logger.error(f"Critical error in batch job execution: {str(e)}", exc_info=True)
        sys.exit(2)  # Critical failure


# Key entry point for local testing and development and also when deployed to Cloud Run Batch
if __name__ == "__main__":
    logger.info("Starting local Cloud Run batch job test...")
    
    # Set test environment variables if not already set
    if not os.getenv('GOOGLE_CLOUD_PROJECT'):
        os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
        logger.info("Set GOOGLE_CLOUD_PROJECT to test-project for local testing")
        
    if not os.getenv('MANUAL_BUCKET_SCAN'):
        os.environ['MANUAL_BUCKET_SCAN'] = 'test-bucket'
        logger.info("Set MANUAL_BUCKET_SCAN to test-bucket for local testing")
    
    # Run the main async function in a new event loop
    asyncio.run(main())