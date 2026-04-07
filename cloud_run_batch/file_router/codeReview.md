  Entry Point to Exit Flow

1. Start: main.py

- Entry point with clean orchestrator pattern
- Environment setup and logging configuration
- Calls CloudRunBatchJobManager and handles exit codes

2. Job Manager: batch_job_manager.py

- CloudRunBatchJobManager - Main execution coordinator
- Determines mode: Pub/Sub vs manual bucket scan
- Handles Pub/Sub message pulling and acknowledgment

3. Message Processing: pubsub_message_handler.py

- PubSubMessageHandler - Extracts file info from Pub/Sub messages
- Filters for inbox files only

4. Batch Coordination: batch_file_processor.py

- BatchFileProcessor - Manages concurrent file processing
- Uses asyncio semaphores for controlled parallelism
- Aggregates processing statistics

5. Single File Processing: file_router.py

- FileRouter - Orchestrates individual file processing pipeline
- Coordinates all file processing steps in sequence

6. Processing Components (called by FileRouter):

- file_metadata_extractor.py - Parse filename patterns
- hive_partition_builder.py - Generate paths and filenames
- cloud_storage_manager.py - Async GCS operations (copy/archive)
- processing_logger.py - Structured logging for governance

7. Package Structure: __init__.py

- Clean exports for all modules

  Review Order Recommendation:

1. main.py - Understand the entry point
2. batch_job_manager.py - See the orchestration logic
3. file_router.py - Core processing pipeline
4. Individual components based on your focus area
5. __init__.py - Package organization

  This gives you the complete data flow from trigger to completion.
