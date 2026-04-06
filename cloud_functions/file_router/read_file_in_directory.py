from google.cloud import storage
from typing import List

def list_bucket_files(bucket_name: str) -> List[str]:
    """
    Lists all files (blobs) in a given Google Cloud Storage bucket.

    Args:
        bucket_name (str): The name of the GCP bucket without the 'gs://' prefix.

    Returns:
        List[str]: A list of the file names found in the bucket.
    """
    # Initialize a client
    storage_client = storage.Client()
    
    # Get the bucket and list its blobs
    blobs = storage_client.list_blobs(bucket_name)

    # Return a list of the blob names
    return [blob.name for blob in blobs]

# Example usage:
bucket_name = "gs://intelia-hackathon-files/"
files = list_bucket_files(bucket_name)
print(files)
