"""
File Router Package

Cloud Run batch job package for the simplified file processing architecture.
This package implements the combined validation and routing logic that processes
files from inbox/ directly to validated/ or quarantine/ destinations.

Architecture Overview:
- Queue Drainer (Cloud Function) batches Pub/Sub messages → Cloud Tasks
- Batch Job Manager receives Cloud Tasks → coordinates processing
- Batch File Processor handles concurrent file processing
- Validator performs combined routing + validation logic
- Files go directly from inbox/ → validated/ (PASS) or quarantine/ (FAIL)

Key Components:
- FileMetadataExtractor: Parse filename patterns
- HivePartitionBuilder: Generate partitioned paths for validated/ layer
- CloudStorageManager: Async file operations
- ProcessingLogger: Governance and audit logging
- Validator: Combined routing + validation logic
- BatchFileProcessor: Concurrent processing coordination
- BatchJobManager: Job lifecycle management

Author: Manish Arora
Version: 1.0
"""

# Package exports will be defined here once modules are implemented