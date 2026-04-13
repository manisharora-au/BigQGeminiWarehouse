## Overview

`file_validator.py` is a GCS-backed CSV validation module. Its job is to pull CSV files from Google Cloud Storage and run them through a series of structural and content checks before they're processed downstream. It supports both single-file and batch (concurrent) validation.

---

## Key Components

### `ValidationResult` (dataclass)

A simple data container that holds the outcome of validating one file. It captures:

* `passed` — overall pass/fail
* `failed_checks` — a list of check names that failed (e.g. `'column_count'`, `'utf8_encoding'`)
* `error_details` — a dict mapping each failed check name to a human-readable message
* `metadata` — entity type, date, file type, source, etc. (extracted from the filename)
* `file_size_bytes`

---

### `FileValidator` (class)

**`__init__`** — Takes a GCP `project_id` and an `expected_schemas` dict (mapping entity types like `'customers'` to their expected column lists). Sets up a GCS storage client and a `FileMetadataExtractor`.

**`load_schema` (static method)** — Reads a `schema.json` file and builds the `expected_schemas` dict. For each entity it creates two entries: one for full loads (`customers`) and one for delta loads (`customers_delta`), where the delta variant appends extra columns like `_delta_type`, `_batch_id`, and `_batch_date`.

---

### `validate_file` (async)

The core single-file validation method. Here's the flow:

1. **Generates a `validation_id`** via `CloudLogging`.
2. **Extracts metadata** from the filename (entity type, load type, date, etc.). Fails early if entity type can't be determined.
3. **Checks file existence** in the GCS bucket.
4. **Downloads the file** as UTF-8 text, capturing its byte size.
5. **Runs 4 validation checks** in sequence:
   * `_check_file_size` — ensures the file is between 1 byte and 500 MB.
   * `_check_utf8_encoding` — confirms the content round-trips cleanly as UTF-8.
   * `_check_non_empty_file` — ensures there's at least a header row plus one data row.
   * `_check_csv_structure` — the most thorough check (see below).
6. **Logs the final result** via `CloudLogging` and returns a `ValidationResult`.

Failures don't stop the pipeline — all checks run and all failures are collected.

---

### `_check_csv_structure` (async)

Looks up the expected columns for the entity type (using the `_delta` schema key for delta files), parses the CSV, and checks:

* **Column count** — actual vs. expected number of columns.
* **Column schema** — exact match of column names and order.
* **Sample data** — delegates to `_validate_sample_data` for up to 100 rows.

### `_validate_sample_data` (async)

Scans up to 100 data rows for two issues: inconsistent column counts per row, and completely empty rows. Caps error collection at 5 to avoid noise.

---

### `validate_batch` (async)

Accepts a list of `(file_path, filename)` tuples and runs `validate_file` on all of them concurrently using `asyncio.gather`. If any individual validation throws an unhandled exception, it's caught and wrapped in a failed `ValidationResult` rather than crashing the whole batch.

---

## Design Notes

* **Error isolation** is a clear priority — no single file failure can break a batch run.
* The `failed_checks` list + `error_details` dict pattern makes it easy for callers to inspect exactly what went wrong without parsing free-form text.
* The `async` methods don't actually do concurrent I/O within a single file validation (the checks are `await`ed sequentially), but the `async` signatures allow `validate_batch` to run multiple files concurrently.
* `_check_utf8_encoding` is somewhat redundant since `download_as_text(encoding='utf-8')` would already raise a `UnicodeDecodeError` (which is caught upstream), but it adds a belt-and-suspenders re-encode check.
