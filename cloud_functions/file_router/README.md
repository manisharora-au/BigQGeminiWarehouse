# File Router Cloud Function

## Purpose
This Cloud Function processes files uploaded to the `inbox/` folder in Cloud Storage and routes them to the appropriate raw data folders using hive partitioning structure.

## Functionality

### File Pattern Recognition
Supports two filename patterns:

1. **Full snapshot files**: `{entity}_{YYYYMMDD}.csv`
   - Example: `customers_20260101.csv`
   - Routes to: `raw/full/entity_type=customers/year=2026/month=01/day=01/`

2. **Delta files**: `batch_{XX}_{entity}_delta.csv` (no date component)
   - Example: `batch_01_customers_delta.csv`
   - Routes to: `raw/delta/entity_type=customers/year={current}/month={current}/day={current}/`
   - Uses current processing date for partitioning

### Supported Entity Types
- `customers`
- `orders` 
- `order_items`
- `products`

### Processing Flow

1. **File Upload Detection**: Triggered by Cloud Storage bucket notifications
2. **Pattern Matching**: Extract entity type, load type, and date from filename
3. **Hive Partitioning**: Create partitioned folder structure
4. **File Routing**: Copy file from `inbox/` to `raw/{load_type}/entity_type={entity}/year={YYYY}/month={MM}/day={DD}/`
5. **Standardized Naming**: Rename file to `{load_type}_{entity}_{batch_id}_{YYYYMMDD}_{timestamp}.csv`
6. **Archival**: Move original file from `inbox/` to `archive/`
7. **Logging**: Record processing results for governance tracking

### Output Structure

```
raw/
├── full/
│   └── entity_type=customers/
│       └── year=2026/
│           └── month=01/
│               └── day=01/
│                   └── full_customers_snapshot_20260101_20260402_142530.csv
└── delta/
    └── entity_type=customers/
        └── year=2026/
            └── month=01/
                └── day=02/
                    └── delta_customers_batch_001_20260402_20260402_142535.csv
```

## Deployment

This function will be deployed via Terraform as part of the infrastructure automation. It requires:

- Cloud Storage bucket notifications configured
- Service account with appropriate permissions
- Integration with governance logging system

## Error Handling

- Files with unsupported patterns are logged but not processed
- Processing failures are logged to governance.validation_log table
- Original files are preserved in case of processing errors
- Comprehensive logging for debugging and monitoring