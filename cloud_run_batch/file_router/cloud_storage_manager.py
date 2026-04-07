"""
Cloud Storage Manager Module

Manages Cloud Storage file operations for the simplified data pipeline.
This module handles async file operations between inbox/, validated/, and quarantine/
directories with proper error handling and governance logging.

Key Responsibilities:
- Read files from inbox/ (flat structure)
- Copy validated files to validated/ (with hive partitioning)
- Move failed files to quarantine/ (flat structure)  
- Archive processed files to archive/
- Async operations with semaphore-controlled concurrency
- Comprehensive error handling and retry logic

Author: Manish Arora
Version: 1.0
"""