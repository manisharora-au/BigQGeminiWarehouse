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

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import time
from google.cloud import storage
#  The google.api_core.exceptions module provides a comprehensive set of exception classes that are raised by Google Cloud client libraries.
from google.api_core import exceptions as gcs_exceptions
from .processing_logger import ProcessingLogger

# Configure logging
logger = logging.getLogger(__name__)

class CloudStorageManager:
    """
    Singleton class that manages async cloud storage operations for file routing system.
    
    This class provides async methods for moving files between GCS locations
    with proper error handling, retry logic, and performance monitoring.
    Uses singleton pattern to ensure only one instance exists per application.
    """
    
    # The _instance and _initialized variables are class variables.
    # These maintain the current state of the instance.
    # The leading underscore on _instance and _initialized is a Python convention signalling 
    # that these are internal implementation details — they are not part of the public interface of the class
    # and should not be accessed or modified from outside
    _instance = None
    _initialized = False

    # __new__ runs first — it allocates memory and creates the raw object. It returns the new instance.
    # __init__ runs second — it receives the instance __new__ just created and populates it with attributes.
    # Effectively this is how a singleton implementation is implemented : 
    # The __new__ method is a static method that is called before the __init__ method.
    # It is used to create the instance of the class.

    # The arguments project_id, and max_concurrent_operations are passed to the __init__ method.
    def __new__(cls, project_id: str, max_concurrent_operations: int = 10):
        """
        Singleton implementation - ensures only one instance exists.
        
        Args:
            cls: The class itself
            project_id (str): GCP project ID
            max_concurrent_operations (int): Maximum concurrent storage operations
            
        Returns:
            CloudStorageManager: The singleton instance
        """
        # When you write cls._instance inside __new__, Python looks up _instance on the class directly. 
        # If the instance does not exist, create it.
        if cls._instance is None:
            # The super() function is used to call the __new__ method of the parent class.
            cls._instance = super(CloudStorageManager, cls).__new__(cls)
        return cls._instance

    # This is the constructor. i.e. it invokes first when the class in instantiated.
    #  __init__ will not be invoked again if the instance is already created.
    def __init__(self, project_id: str, max_concurrent_operations: int = 10):
        """
        Initialize the Cloud Storage Manager (singleton pattern).
        Only initializes once, subsequent calls are ignored.
        
        Args:
            project_id (str): GCP project ID
            max_concurrent_operations (int): Maximum concurrent storage operations
        """
        # Only initialize once (singleton pattern)
        if not CloudStorageManager._initialized:
            self.project_id = project_id
            #  Get a GCS Storage Client Handle
            self.client = storage.Client(project=project_id)
            #  A semaphore is a synchronization primitive that controls access to a shared resource, and used to limit the number of concurrent operations.
            #  This is used to prevent overwhelming the GCS API with too many concurrent requests.
            self.semaphore = asyncio.Semaphore(max_concurrent_operations)
            CloudStorageManager._initialized = True
            logger.info(f'CloudStorageManager singleton initialized with {max_concurrent_operations} max concurrent operations')
        else:
            logger.info('CloudStorageManager singleton already initialized - reusing existing instance')
        
    """
    Async copy file from source to destination with retry logic.
    
    Args:
        source_bucket_name (str): Source GCS bucket name
        source_blob_name (str): Source blob path (e.g., "inbox/file.csv")
        destination_bucket_name (str): Destination GCS bucket name  
        destination_blob_name (str): Destination blob path (e.g., "validated/...")
        validation_id (Optional[str]): Validation ID for correlation
        max_retries (int): Maximum retry attempts
        
    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
    """
    async def copy_file_to_destination(
        self, # Why self, because we are using the client and semaphore objects defined in the constructor
        source_bucket_name: str,
        source_blob_name: str, # Blob name represents the file path in the bucket. It includes the file name and extension.
        destination_bucket_name: str,
        destination_blob_name: str,
        validation_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Tuple[bool, Optional[str]]: # A tuple is an immutable ordered sequence of elements. 
        # In the above signature, the return type is a tuple of two elements. 
        # The first element is a boolean value indicating whether the file was copied successfully. In that scenario the second element will be None.
        # The second element is an optional string value indicating the error message if the file was not copied successfully. In that scenario the 
        # second element will be the error message and the first element will be False.

        # The below line acquires a permit from the semaphore.
        # If the semaphore is full, it will wait until a permit is released, and hence the reason for an async implementation.
        # This is used to limit the number of concurrent operations.
        async with self.semaphore:
            source_path = f'gs://{source_bucket_name}/{source_blob_name}'
            #  The source path will look like gs://bucket_name/file_name.csv
            destination_path = f'gs://{destination_bucket_name}/{destination_blob_name}'
            #  The destination path will look like gs://bucket_name/file_name.csv
            start_time = time.time()
            
            # The below code snippet is a retry loop that will retry the file copy operation up to max_retries times.
            for attempt in range(max_retries + 1):
                try:
                    #  Just a blind check to ensure the client handle exists
                    if self.client is None:
                        error_msg = "Cloud Storage Manager client is not initialized"
                        logger.error(f"{error_msg}")
                        return False, error_msg # return false and cease processing
                    
                    # Else not required. If client handle exists then get source and destination bucket handles
                    source_bucket = self.client.bucket(source_bucket_name)
                    destination_bucket = self.client.bucket(destination_bucket_name)
                    
                    # Get a handle to the source blob (indirectly the source File)
                    source_blob = source_bucket.blob(source_blob_name)
                    
                    # Next step is to Check if source file exists
                    # Since, source_blob.exists() is a blocking GCS SDK call — offloaded to the thread pool. If it is executed direcrtly, then
                    # the get event loop is waiting and doing nothing. Whereas when the file is being checked for existence via run_in_executor, 
                    # the event loop is not blocked while waiting for GCS to respond. Without this, the event loop would freeze here and no other 
                    # coroutines could run until GCS responds, defeating the concurrency the semaphore provides.
                    loop = asyncio.get_event_loop()
                    source_exists = await loop.run_in_executor(None, source_blob.exists) 
                    # None means to use the default executor. There are no arguments to be passed to the source_blob.exists() method.
                    if not source_exists:
                        error_msg = f"Source file does not exist: {source_path}"
                        # Log the storage operation to Cloud Logging in async mode.
                        await self._log_storage_operation(
                            operation="copy",
                            source_path=source_path,
                            destination_path=destination_path,
                            success=False,
                            duration_ms=int((time.time() - start_time) * 1000),
                            error_message=error_msg,
                            validation_id=validation_id
                        )
                        return False, error_msg
                    
                    # Copy the blob.
                    # source_bucket.copy_blob() is a blocking GCS SDK call — this is the most
                    # expensive operation in the method and the most important to offload.
                    # Wrapping it in run_in_executor means up to max_concurrent_operations copies
                    # can be in-flight simultaneously across the thread pool while the event loop
                    # remains free to handle other coroutines.
                    destination_blob = await loop.run_in_executor( # The method signature is run_in_executor(executor, func, *args)
                        None, # executor
                        source_bucket.copy_blob, # func
                        source_blob, destination_bucket, destination_blob_name # args
                    )
                    #  The return type of the copy_blob method is a blob object. The output would look like <Blob: my-bucket, path/to/file.txt>
                    
                    
                    # Verify the copy was successful with polling (eventual consistency)
                    max_wait_seconds = 10
                    poll_interval = 2
                    verification_start = time.time()
                    
                    # Start checking if the target blob exists on destination bucket every 2 seconds for 10 seconds, since the copy 
                    # operation is eventually consistent.
                    # destination_blob.exists() is also a blocking GCS SDK call — offloaded to thread pool.
                    # asyncio.sleep() between polls is non-blocking — the event loop remains free during the wait.
                    while time.time() - verification_start < max_wait_seconds:
                        destination_exists = await loop.run_in_executor(None, destination_blob.exists)
                        # The output would be True if the file exists on the destination bucket, False otherwise.
                        if destination_exists:
                            duration_ms = int((time.time() - start_time) * 1000)
                            # Log the storage operation to Cloud Logging in async mode.
                            await self._log_storage_operation(
                                operation="copy",
                                source_path=source_path,
                                destination_path=destination_path,
                                success=True,
                                duration_ms=duration_ms,
                                error_message=None,
                                validation_id=validation_id
                            )
                            return True, None
                        
                        # Else, keep waiting for 2 seconds before next check
                        await asyncio.sleep(poll_interval)
                    
                    # Copy verification timeout. The below block will execute as an else case to the while loop
                    error_msg = f"Copy verification timeout after {max_wait_seconds}s - destination file not found"
                    await self._log_storage_operation(
                        "copy", source_path, destination_path, False,
                        int((time.time() - start_time) * 1000), error_msg, validation_id
                    )
                    return False, error_msg

                #  The NotFound exception will be raised if the source or destination bucket or file is not found
                except gcs_exceptions.NotFound as e:
                    error_msg = f"Bucket or file not found: {str(e)}"
                    await self._log_storage_operation(
                        "copy", source_path, destination_path, False,
                        int((time.time() - start_time) * 1000), error_msg, validation_id
                    )
                    return False, error_msg
                    
                #  The Forbidden exception will be raised if the source or destination bucket or file is not accessible
                except gcs_exceptions.Forbidden as e:
                    error_msg = f"Access denied: {str(e)}"
                    await self._log_storage_operation(
                        "copy", source_path, destination_path, False,
                        int((time.time() - start_time) * 1000), error_msg, validation_id
                    )
                    return False, error_msg

                #  Any other exception will be caught here
                except Exception as e:
                    error_msg = f"Copy operation failed (attempt {attempt + 1}): {str(e)}"
                    
                    # Onlyu log when it is the last attempt and no success
                    if attempt == max_retries:
                        await self._log_storage_operation(
                            "copy", source_path, destination_path, False,
                            int((time.time() - start_time) * 1000), error_msg, validation_id
                        )
                        return False, error_msg
                    
                    # This is an important development construct and an industry standard to retry on failure with exponential backoff
                    # Example with max_retries=3:
                    # - Attempt 0: Fails → wait 1 second → continue loop
                    # - Attempt 1: Fails → wait 2 seconds → continue loop
                    # - Attempt 2: Fails → wait 4 seconds → continue loop   
                    # - Attempt 3: Fails → attempt == max_retries, so give up and return error
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    
            return False, "Max retries exceeded"

    async def move_file_from_inbox_to_destination(
        self,
        source_bucket_name: str,
        source_blob_name: str,
        destination_bucket_name: str,
        destination_blob_name: str,
        validation_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Tuple[bool, Optional[str]]:
        """
        Async move file (copy + delete source) with retry logic.
        
        Args:
            source_bucket_name (str): Source GCS bucket name
            source_blob_name (str): Source blob path
            destination_bucket_name (str): Destination GCS bucket name
            destination_blob_name (str): Destination blob path
            validation_id (Optional[str]): Validation ID for correlation
            max_retries (int): Maximum retry attempts
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        # First copy the file using the method copy_file_to_destination
        copy_success, copy_error = await self.copy_file_to_destination(source_bucket_name
                                                                        ,source_blob_name
                                                                        ,destination_bucket_name
                                                                        ,destination_blob_name
                                                                        ,validation_id
                                                                        ,max_retries
        )
        
        #  If Not True
        if not copy_success:
            return False, f"Move failed during copy: {copy_error}"
        
        # Then delete the source file using the method delete_file_from_bucket
        delete_success, delete_error = await self.delete_file_from_bucket(source_bucket_name
                                                                        ,source_blob_name
                                                                        ,validation_id
                                                                        ,max_retries
        )
        
        # If Not True
        if not delete_success:
            # Copy succeeded but delete failed - log this as a warning
            source_path = f"gs://{source_bucket_name}/{source_blob_name}"
            destination_path = f"gs://{destination_bucket_name}/{destination_blob_name}"
            
            await self._log_storage_operation(
                "move", source_path, destination_path, False,
                0, f"Copy succeeded but source delete failed: {delete_error}", validation_id
            )
            return False, f"Move partially failed - file copied but source not deleted: {delete_error}"
        
        # Both copy and delete succeeded
        source_path = f"gs://{source_bucket_name}/{source_blob_name}"
        destination_path = f"gs://{destination_bucket_name}/{destination_blob_name}"
        
        await self._log_storage_operation(
            operation="move", 
            source_path=source_path, 
            destination_path=destination_path, 
            success=True, 
            duration_ms=0, 
            error_message=None, 
            validation_id=validation_id
        )
        return True, None

    async def delete_file_from_bucket(
        self,
        bucket_name: str,
        blob_name: str,
        validation_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Tuple[bool, Optional[str]]: # Immutable
        """
        Async delete file with retry logic.
        
        Args:
            bucket_name (str): GCS bucket name
            blob_name (str): Blob path to delete
            validation_id (Optional[str]): Validation ID for correlation
            max_retries (int): Maximum retry attempts
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        #  Same semaphore logic applied as in copy_file_to_destination
        #  Semaphores are created once in the constructor to allow max number of concurrent operations to occuer. 
        #  Effectively, if there are copy operations occuring elsewhere, the delete operation will wait for the semaphore to be released.
        async with self.semaphore:
            file_path = f"gs://{bucket_name}/{blob_name}"
            start_time = time.time()
            # The below line is used to get the event loop. An event loop is a programming 
            # construct that manages the execution of asynchronous code.   
            loop = asyncio.get_event_loop()

            for attempt in range(max_retries + 1):
                try:
                    #  Get a bucket object from the client.
                    bucket = self.client.bucket(bucket_name)
                    #  Get a handle to the blob (file) to be deleted.
                    blob = bucket.blob(blob_name)
                    
                    # Check if file exists before attempting delete.
                    # blob.exists() is a blocking GCS SDK call — offloaded to the thread pool
                    # via run_in_executor so the event loop is not blocked while GCS responds.
                    blob_exists = await loop.run_in_executor(None, blob.exists)
                    if not blob_exists:
                        # File already deleted or never existed - consider this success
                        duration_ms = int((time.time() - start_time) * 1000)
                        # Log the operation as successful
                        await self._log_storage_operation(operation="delete"
                                                            ,source_path=file_path
                                                            ,destination_path=""
                                                            ,success=True
                                                            ,duration_ms=duration_ms
                                                            ,error_message="File already deleted or not found"
                                                            ,validation_id=None if validation_id is None else validation_id)
                        return True, None
                    
                    # Delete the blob.
                    # blob.delete() is a blocking GCS SDK call — offloaded to the thread pool
                    # so the event loop remains free to handle other coroutines during the GCS call.
                    await loop.run_in_executor(None, blob.delete)
                    
                    # Verify deletion — also a blocking GCS call, offloaded to thread pool.
                    deletion_confirmed = await loop.run_in_executor(None, blob.exists) # returns a True if the blob exists
                    #  If File not found OR blob does not exist, then the file is deleted successfully.
                    if not deletion_confirmed:
                        duration_ms = int((time.time() - start_time) * 1000)
                        await self._log_storage_operation(operation="delete"
                                                            ,source_path=file_path
                                                            ,destination_path=""
                                                            ,success=True
                                                            ,duration_ms=duration_ms
                                                            ,error_message=None
                                                            ,validation_id=None if validation_id is None else validation_id)
                        return True, None
                    # NotFound means file not found to be deleted. Simply do a cloud logging operation and return True.
                except gcs_exceptions.NotFound:
                    # File not found - consider this success for delete operation
                    duration_ms = int((time.time() - start_time) * 1000)
                    await self._log_storage_operation(operation="delete"
                                                            ,source_path=file_path
                                                            ,destination_path=""
                                                            ,success=True
                                                            ,duration_ms=duration_ms
                                                            ,error_message="File not found (already deleted)"
                                                            ,validation_id=None if validation_id is None else validation_id)
                    return True, None
                    
                except Exception as e:
                    error_msg = f"Delete operation failed (attempt {attempt + 1}): {str(e)}"
                    
                    if attempt == max_retries:
                        await self._log_storage_operation(
                            "delete", file_path, "", False,
                            int((time.time() - start_time) * 1000), error_msg, validation_id
                        )
                        return False, error_msg
                    
                    # Wait before retry with exponential backoff
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    
            return False, "Max retries exceeded"


    async def _log_storage_operation(
        self,
        operation: str,
        source_path: str,
        destination_path: str,
        success: bool,
        duration_ms: int,
        error_message: Optional[str] = None,
        validation_id: Optional[str] = None
    ) -> None:
        """
        Log storage operation using ProcessingLogger (async wrapper).
        
        Args:
            operation (str): Type of operation (copy, move, delete)
            source_path (str): Source file path
            destination_path (str): Destination file path
            success (bool): Whether operation succeeded
            duration_ms (int): Operation duration
            error_message (Optional[str]): Error details if failed
            validation_id (Optional[str]): Validation ID for correlation
        """
        # Run the sync logging method in thread pool to avoid blocking
        #  The run_in_executor method is used to run a function in a separate thread. The mthod signature is run_in_executor(executor, func, *args, **kwargs)
        #  The None argument specifies the default thread pool executor.
        #  The ProcessingLogger.log_cloud_storage_operation_to_cloud_logging is the function to be executed in the thread pool.
        #  The arguments operation, source_path, destination_path, success, duration_ms, error_message are passed to the function.
        await asyncio.get_event_loop().run_in_executor(
                                                    None
                                                    , ProcessingLogger.log_cloud_storage_operation_to_cloud_logging  # Function to be executed in the thread pool
                                                    , operation  # Operation type arg
                                                    , source_path  # Source file path arg
                                                    , destination_path  # Destination file path arg
                                                    , success  # Whether operation succeeded arg
                                                    , duration_ms  # Operation duration arg
                                                    , error_message  # Error details if failed arg
                                                    , None if validation_id is None else validation_id  # Validation ID arg
        )

    def get_blob_size(self, bucket_name: str, blob_name: str) -> Optional[int]:
        """
        Get the size of a blob in bytes.
        
        Args:
            bucket_name (str): GCS bucket name
            blob_name (str): Blob path
            
        Returns:
            Optional[int]: Size in bytes, None if blob doesn't exist
        """
        try:
            #  Get a handle to the bucket
            bucket = self.client.bucket(bucket_name)
            #  Get a handle to the blob
            blob = bucket.blob(blob_name)
            
            if blob.exists():
                blob.reload()  # Refresh metadata
                return blob.size
            return None
            
        except Exception as e:
            logger.error(f"Error getting blob size for {bucket_name}/{blob_name}: {e}")
            return None

    def blob_exists(self, bucket_name: str, blob_name: str) -> bool:
        """
        Check if a blob exists in GCS.
        
        Args:
            bucket_name (str): GCS bucket name
            blob_name (str): Blob path
            
        Returns:
            bool: True if blob exists, False otherwise
        """
        try:
            #  Get a handle to the bucket. These are not GCS Blocking calls
            bucket = self.client.bucket(bucket_name)
            #  Get a handle to the blob
            blob = bucket.blob(blob_name)
            #  Check if the blob exists
            return blob.exists()
            
        except Exception as e:
            logger.error(f"Error checking blob existence for {bucket_name}/{blob_name}: {e}")
            return False