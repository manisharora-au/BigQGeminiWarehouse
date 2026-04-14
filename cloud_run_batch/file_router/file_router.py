"""
File Router Module

Handles routing of validated files to appropriate GCS destinations based on
validation results and business rules. This module focuses purely on file
routing logic without performing validation or processing.

Key Responsibilities:
- Route PASS files to processed/ folder with Hive partitioning
- Route FAIL files to failed/ folder for manual review
- Generate destination paths based on entity type and date
- Coordinate with CloudStorageManager for async file operations
- Track routing metrics and success rates

Routing Rules:
- PASS: gs://bucket/processed/{entity_type}/year={YYYY}/month={MM}/day={DD}/filename
- FAIL: gs://bucket/failed/filename
- Source files in inbox/ are moved (not copied) to final destinations

Author: Manish Arora
Version: 1.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .cloud_storage_manager import CloudStorageManager
from .file_validator import ValidationResult
from .cloud_logging import CloudLogging
from . import settings

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class RoutingResult:
    """
    Represents the result of file routing operation.
    
    Attributes:
        filename (str): Name of the routed file
        validation_id (str): Validation ID for correlation
        success (bool): Whether routing was successful
        source_path (str): Original file path in inbox/
        destination_path (Optional[str]): Final destination path
        routing_type (str): Type of routing (passed/failed)
        error_message (Optional[str]): Error details if routing failed
        duration_ms (int): Routing operation duration
    """
    filename: str
    validation_id: str
    success: bool
    source_path: str
    destination_path: Optional[str]
    routing_type: str
    error_message: Optional[str]
    duration_ms: int

class FileRouter:
    """
    Handles routing of validated files to appropriate GCS destinations.
    
    This class implements business rules for file placement based on validation
    results, with support for Hive partitioning and error isolation.
    """
    
    def __init__(self):
        """
        Initialize the File Router with storage client and configuration.
        """
        self.storage_manager = CloudStorageManager()
        self.project_id = settings.get_project_id()
        
    async def route_validated_files(
        self,
        bucket_name: str,
        validation_results: List[ValidationResult]
    ) -> List[RoutingResult]:
        """
        Route multiple validated files to their destinations concurrently.
        
        Args:
            bucket_name (str): GCS bucket name
            validation_results (List[ValidationResult]): Results from file validation
            
        Returns:
            List[RoutingResult]: Results for each routing operation
        """
        routing_tasks = [
            self._route_single_file(bucket_name, result)
            for result in validation_results
        ]
        
        results = await asyncio.gather(*routing_tasks, return_exceptions=True)
        
        # Handle any exceptions in the results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                validation_result = validation_results[i]
                final_results.append(RoutingResult(
                    filename=validation_result.filename,
                    validation_id=validation_result.validation_id,
                    success=False,
                    source_path=f"inbox/{validation_result.filename}",
                    destination_path=None,
                    routing_type="error",
                    error_message=f"Routing exception: {str(result)}",
                    duration_ms=0
                ))
            else:
                final_results.append(result)
        
        # Log batch routing metrics
        await self._log_batch_routing_metrics(bucket_name, final_results)
        
        return final_results
    
    async def _route_single_file(
        self,
        bucket_name: str,
        validation_result: ValidationResult
    ) -> RoutingResult:
        """
        Route a single validated file to its destination.
        
        Args:
            bucket_name (str): GCS bucket name
            validation_result (ValidationResult): Validation result for the file
            
        Returns:
            RoutingResult: Result of the routing operation
        """
        start_time = datetime.now()
        source_path = f"inbox/{validation_result.filename}"
        
        try:
            if validation_result.passed:
                # Route to processed/ with Hive partitioning
                destination_path = self._generate_processed_path(validation_result)
                routing_type = "passed"
            else:
                # Route to failed/ for manual review
                destination_path = f"failed/{validation_result.filename}"
                routing_type = "failed"
            
            # Move file to destination
            move_success = await self.storage_manager.move_file_from_inbox_to_destination(
                bucket_name=bucket_name,
                source_filename=validation_result.filename,
                destination_path=destination_path
            )
            
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            if move_success:
                # Log successful routing
                CloudLogging.log_cloud_storage_operation(
                    operation="move",
                    source_path=f"gs://{bucket_name}/{source_path}",
                    destination_path=f"gs://{bucket_name}/{destination_path}",
                    success=True,
                    duration_ms=duration_ms
                )
                
                return RoutingResult(
                    filename=validation_result.filename,
                    validation_id=validation_result.validation_id,
                    success=True,
                    source_path=source_path,
                    destination_path=destination_path,
                    routing_type=routing_type,
                    error_message=None,
                    duration_ms=duration_ms
                )
            else:
                return RoutingResult(
                    filename=validation_result.filename,
                    validation_id=validation_result.validation_id,
                    success=False,
                    source_path=source_path,
                    destination_path=destination_path,
                    routing_type=routing_type,
                    error_message="File move operation failed",
                    duration_ms=duration_ms
                )
                
        except Exception as e:
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            error_message = f"Routing error: {str(e)}"
            
            # Log failed routing
            CloudLogging.log_cloud_storage_operation(
                operation="move",
                source_path=f"gs://{bucket_name}/{source_path}",
                destination_path=f"gs://{bucket_name}/{destination_path if 'destination_path' in locals() else 'unknown'}",
                success=False,
                duration_ms=duration_ms,
                error_message=error_message
            )
            
            return RoutingResult(
                filename=validation_result.filename,
                validation_id=validation_result.validation_id,
                success=False,
                source_path=source_path,
                destination_path=None,
                routing_type="error",
                error_message=error_message,
                duration_ms=duration_ms
            )
    
    def _generate_processed_path(self, validation_result: ValidationResult) -> str:
        """
        Generate Hive-partitioned destination path for processed files.
        
        Args:
            validation_result (ValidationResult): Validation result containing metadata
            
        Returns:
            str: Destination path with Hive partitioning
            
        Example:
            processed/customers/year=2026/month=01/day=01/customers_20260101.csv
        """
        entity_type = validation_result.metadata.get('entity_type', 'unknown')
        file_date = validation_result.metadata.get('file_date')
        
        if file_date and len(file_date) == 8:  # Format: YYYYMMDD
            year = file_date[:4]
            month = file_date[4:6]
            day = file_date[6:8]
            
            return f"processed/{entity_type}/year={year}/month={month}/day={day}/{validation_result.filename}"
        else:
            # Fallback to current date if file_date is invalid
            now = datetime.now(timezone.utc)
            return f"processed/{entity_type}/year={now.year}/month={now.month:02d}/day={now.day:02d}/{validation_result.filename}"
    
    async def _log_batch_routing_metrics(
        self,
        bucket_name: str,
        routing_results: List[RoutingResult]
    ) -> None:
        """
        Log batch routing metrics for operational monitoring.
        
        Args:
            bucket_name (str): GCS bucket name
            routing_results (List[RoutingResult]): Results from routing operations
        """
        total_files = len(routing_results)
        successful_routes = sum(1 for r in routing_results if r.success)
        failed_routes = total_files - successful_routes
        
        passed_files = sum(1 for r in routing_results if r.routing_type == "passed" and r.success)
        failed_files = sum(1 for r in routing_results if r.routing_type == "failed" and r.success)
        error_files = sum(1 for r in routing_results if r.routing_type == "error")
        
        avg_duration_ms = sum(r.duration_ms for r in routing_results) / total_files if total_files > 0 else 0
        
        # Log routing summary
        logger.info(
            f"Batch routing completed: {successful_routes}/{total_files} files routed successfully",
            extra={
                'bucket_name': bucket_name,
                'total_files': total_files,
                'successful_routes': successful_routes,
                'failed_routes': failed_routes,
                'passed_files': passed_files,
                'failed_files': failed_files,
                'error_files': error_files,
                'avg_duration_ms': avg_duration_ms,
                'event_type': 'batch_routing_complete',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
    
    async def route_single_validated_file(
        self,
        bucket_name: str,
        validation_result: ValidationResult
    ) -> RoutingResult:
        """
        Route a single validated file (convenience method for single file operations).
        
        Args:
            bucket_name (str): GCS bucket name
            validation_result (ValidationResult): Validation result for the file
            
        Returns:
            RoutingResult: Result of the routing operation
        """
        return await self._route_single_file(bucket_name, validation_result)
    
    def get_expected_destination_path(self, validation_result: ValidationResult) -> str:
        """
        Get the expected destination path without performing the routing operation.
        
        Args:
            validation_result (ValidationResult): Validation result for the file
            
        Returns:
            str: Expected destination path
        """
        if validation_result.passed:
            return self._generate_processed_path(validation_result)
        else:
            return f"failed/{validation_result.filename}"