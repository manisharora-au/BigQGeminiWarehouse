"""
Cloud Run Batch Job: File Router Main Orchestrator

Main entry point for the simplified Cloud Run batch job architecture.
This module serves as the orchestrator that coordinates all components
and handles different execution modes.

Key Responsibilities:
- Entry point for Cloud Run job execution
- Parse environment variables and configuration
- Initialize BatchJobManager and coordinate execution
- Handle different trigger modes (Cloud Tasks, manual, scheduled)
- Generate final job statistics and exit codes
- Integrate with monitoring and alerting systems

Execution Modes:
1. Cloud Tasks Mode: Process batched file payloads from Queue Drainer
2. Manual Bucket Scan: Process all files in inbox/ for backfill operations  
3. Scheduled Mode: Handle scheduled batch processing requests
4. On-demand Mode: Direct execution for testing and debugging

Environment Variables:
- MAX_WORKERS: Concurrent processing workers (default: 10)
- BATCH_SIZE: Maximum files per batch (default: 50)
- PROCESSOR_VERSION: Version for governance logging
- MANUAL_BUCKET_SCAN: Bucket name for backfill mode (optional)
- GOOGLE_CLOUD_PROJECT: GCP project ID

Exit Codes:
- 0: Success - All files processed successfully
- 1: Partial failure - Some files failed processing
- 2: Critical failure - Job execution failed

Author: Manish Arora
Version: 1.0
"""