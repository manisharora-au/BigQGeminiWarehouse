"""
Validator Module (Combined Router + Validator)

Main processing component that combines file routing logic with schema validation.
This module handles the complete file processing pipeline from inbox to final destination,
replacing the previous separate File Router and Validator components.

Key Responsibilities:
- Extract metadata from filenames (entity type, load type, date)
- Perform 8 schema validation checks (structure, encoding, format)
- Route PASS files to validated/ with hive partitioning
- Route FAIL files to quarantine/ with detailed error logging
- Generate validation records for governance tracking
- Support both single file and batch processing modes
- Async processing with error isolation per file

Schema Validation Checks:
1. Column names match expected schema
2. Column count validation
3. Column order verification
4. Non-empty file validation
5. UTF-8 encoding verification
6. Comma delimiter validation
7. Date format sampling
8. File size validation

Author: Manish Arora
Version: 1.0
"""