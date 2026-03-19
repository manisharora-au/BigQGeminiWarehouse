"""
BigQuery Connection Utility for Antigravity

This script provides a simple interface for the Antigravity agent to query
Google BigQuery and retrieve results as a Pandas DataFrame or formatted text.
"""

import os
from google.cloud import bigquery
import pandas as pd
from typing import Optional, List, Dict, Any

class BigQueryConnector:
    """
    Handles connectivity and queries for Google BigQuery.
    """
    
    def __init__(self, project_id: str):
        """
        Initializes the BigQuery client.
        
        Args:
            project_id: The GCP Project ID to billing and quota.
        """
        self.project_id = project_id
        # Client will use ADC (Application Default Credentials) 
        # or GOOGLE_APPLICATION_CREDENTIALS environment variable.
        self.client = bigquery.Client(project=self.project_id)

    def query(self, sql: str) -> pd.DataFrame:
        """
        Executes a SQL query and returns the results as a Pandas DataFrame.
        
        Args:
            sql: The SQL query string to execute.
            
        Returns:
            A Pandas DataFrame containing the query results.
        """
        query_job = self.client.query(sql)
        results = query_job.result()
        return results.to_dataframe()

    def list_datasets(self) -> List[str]:
        """
        Lists all datasets in the project.
        """
        datasets = list(self.client.list_datasets())
        return [ds.dataset_id for ds in datasets]

    def list_tables(self, dataset_id: str) -> List[str]:
        """
        Lists all tables in a specific dataset.
        """
        tables = list(self.client.list_tables(dataset_id))
        return [t.table_id for t in tables]

if __name__ == "__main__":
    # Example usage
    PROJECT_ID = "manish-sandpit"
    connector = BigQueryConnector(project_id=PROJECT_ID)
    
    print(f"Connected to project: {PROJECT_ID}")
    print(f"Datasets: {connector.list_datasets()}")
    
    # Simple query test
    TEST_SQL = f"SELECT * FROM `{PROJECT_ID}.raw_ext.customers` LIMIT 5"
    print(f"\nRunning test query: {TEST_SQL}")
    df = connector.query(TEST_SQL)
    print(df)
