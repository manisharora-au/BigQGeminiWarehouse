# BigQuery Extension Usage Guide

This guide explains how to use the "BigQuery" extension (`dr666m1.bq-extension-vscode`) in VS Code with your project configuration.

## 1. Authentication

The extension relies on Google Cloud Application Default Credentials (ADC). To authenticate:

1.  Open your terminal in VS Code.
2.  Run the following command:
    ```bash
    gcloud auth application-default login
    ```
3.  Follow the instructions in your browser to log in with your GCP account.

## 2. Accessing BigQuery

1.  Click on the **BigQuery** icon in the VS Code Activity Bar (left sidebar).
2.  You should see the projects configured in your `.vscode/settings.json`:
    - `intelia-hackathon-dev`
    - `manish-sandpit` (Pinned/Default)

## 3. Running Queries

1.  Create a new file with a `.sql` extension or open an existing one.
2.  Write your SQL query.
3.  Right-click in the editor and select **Run Query** or use the shortcut (usually `Shift+Cmd+Enter` on Mac).
4.  Results will appear in a new tab or panel.

## 4. Configuration Details

Your current settings in `.vscode/settings.json` include:
- **Projects**: Explicitly listed projects are shown even if you don't have project-level list permissions.
- **Pinned Projects**: `manish-sandpit` is pinned for easy access.
- **Default Project**: `manish-sandpit` is used for queries unless specified otherwise.
- **Cache TTL**: Set to `0` to ensure you always see the latest dataset/table structure.

## 5. Cancelling a Running Operation

If you need to stop a running query or DML operation:

### In VS Code
1.  Look for a **Cancel** or **Stop** button (usually a square icon) in the query results header or the activity bar while the query is running.
2.  Alternatively, use the **Command Palette** (`Cmd+Shift+P`), type "BigQuery", and look for a "Cancel Query" command.

### In Google Cloud Console
1.  Go to the [BigQuery Console](https://console.cloud.google.com/bigquery).
2.  In the **Job History** pane (Project History or Personal History), find the running job.
3.  Click the **Cancel** button next to the job.

### Using CLI
If you have the `bq` command-line tool installed, you can run:
```bash
bq cancel <job_id>
```
You can find the `<job_id>` in the VS Code results or the Cloud Console.

## 6. IDENTITY and Auto-Increment Columns

Unlike traditional relational databases (like SQL Server or MySQL), **Google BigQuery does not natively support an `IDENTITY` or `AUTO_INCREMENT` column property** on table creation as of 2026. This is because BigQuery is explicitly designed for distributed, analytical workloads rather than transactional record-keeping where sequential IDs are common.

If you need unique identifiers in your BigQuery tables, you must handle them explicitly. Here are the common workarounds:

### `GENERATE_UUID()`
The recommended approach for creating globally unique identifiers, especially for high-throughput ingestion:
```sql
SELECT
  GENERATE_UUID() AS id,
  first_name,
  last_name
FROM `your_project.your_dataset.your_table`
```

### `ROW_NUMBER()`
If you absolutely need sequential integer IDs (e.g., when creating a static dimension table), you can generate them using analytical functions. However, these are not dynamically auto-incremented on new inserts.
```sql
SELECT
  ROW_NUMBER() OVER() AS id,
  first_name,
  last_name
FROM `your_project.your_dataset.your_table`
```

### Custom Implementation
For real transactional auto-increment needs, you must build custom logic outside of BigQuery (e.g., using Cloud Functions or Dataflow) to track and assign the maximum ID before performing inserts, though this is generally discouraged for BigQuery's architecture.
