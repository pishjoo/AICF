"""
Rendering Job Service

Service layer for managing rendering jobs with full lifecycle support.
"""

import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import RenderingJob, VideoComposition, RenderOutput, RenderingJobStatus
from app.rendering.schemas import (
    RenderingJobCreate,
    RenderingJobUpdate,
    RenderingJobStatus as SchemaJobStatus,
)


logger = logging.getLogger(__name__)


class RenderingJobService:
    """
    Service for managing rendering jobs.
    
    Capabilities:
    - create rendering job
    - get job status
    - update progress
    - cancel job
    - retry failed jobs
    - track execution time
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.service")
    
    def create_job(
        self,
        job_data: RenderingJobCreate
    ) -> RenderingJob:
        """
        Create a new rendering job.
        
        Args:
            job_data: Job creation schema
            
        Returns:
            Created RenderingJob instance
        """
        job_id = str(uuid.uuid4())
        
        job = RenderingJob(
            job_id=job_id,
            name=job_data.name,
            job_type=job_data.job_type,
            organization_id=job_data.organization_id,
            status=RenderingJobStatus.CREATED,
            progress=0,
            input_files=job_data.input_files,
            output_format=job_data.output_format,
            parameters=job_data.parameters or {},
            priority=job_data.priority,
            metadata=job_data.metadata or {}
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        self.logger.info(f"Created rendering job {job_id} ({job_data.name}) for org {job_data.organization_id}")
        return job
    
    def get_job(self, job_id: int, organization_id: Optional[int] = None) -> Optional[RenderingJob]:
        """
        Get a rendering job by ID.
        
        Args:
            job_id: Job ID
            organization_id: Optional tenant ID for isolation
            
        Returns:
            RenderingJob or None if not found
        """
        query = self.db.query(RenderingJob).filter(RenderingJob.id == job_id)
        
        if organization_id:
            query = query.filter(RenderingJob.organization_id == organization_id)
        
        return query.first()
    
    def get_job_by_uuid(self, job_uuid: str, organization_id: Optional[int] = None) -> Optional[RenderingJob]:
        """
        Get a rendering job by UUID.
        
        Args:
            job_uuid: Job UUID string
            organization_id: Optional tenant ID for isolation
            
        Returns:
            RenderingJob or None if not found
        """
        query = self.db.query(RenderingJob).filter(RenderingJob.job_id == job_uuid)
        
        if organization_id:
            query = query.filter(RenderingJob.organization_id == organization_id)
        
        return query.first()
    
    def get_job_status(self, job_id: int, organization_id: Optional[int] = None) -> Optional[RenderingJobStatus]:
        """
        Get the status of a rendering job.
        
        Args:
            job_id: Job ID
            organization_id: Optional tenant ID for isolation
            
        Returns:
            Job status or None if not found
        """
        job = self.get_job(job_id, organization_id)
        return job.status if job else None
    
    def update_progress(
        self,
        job_id: int,
        progress: int,
        organization_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update job progress percentage.
        
        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            organization_id: Optional tenant ID for isolation
            metadata: Optional metadata to merge
            
        Returns:
            True if updated, False if job not found
        """
        if progress < 0 or progress > 100:
            raise ValueError("Progress must be between 0 and 100")
        
        job = self.get_job(job_id, organization_id)
        if not job:
            return False
        
        job.progress = progress
        if metadata:
            current_metadata = job.metadata or {}
            current_metadata.update(metadata)
            job.metadata = current_metadata
        
        job.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        self.logger.debug(f"Updated job {job_id} progress to {progress}%")
        return True
    
    def update_status(
        self,
        job_id: int,
        status: RenderingJobStatus,
        organization_id: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update job status.
        
        Args:
            job_id: Job ID
            status: New status
            organization_id: Optional tenant ID for isolation
            error_message: Optional error message for FAILED status
            
        Returns:
            True if updated, False if job not found
        """
        job = self.get_job(job_id, organization_id)
        if not job:
            return False
        
        old_status = job.status
        job.status = status
        
        # Track timing
        if status == RenderingJobStatus.PROCESSING and not job.started_at:
            job.started_at = datetime.now(timezone.utc)
        elif status in [RenderingJobStatus.COMPLETED, RenderingJobStatus.FAILED, RenderingJobStatus.CANCELLED]:
            job.completed_at = datetime.now(timezone.utc)
            if job.started_at:
                job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
        
        if error_message:
            job.error_message = error_message
        
        job.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        self.logger.info(f"Job {job_id} status changed from {old_status.value} to {status.value}")
        return True
    
    def cancel_job(
        self,
        job_id: int,
        organization_id: Optional[int] = None
    ) -> bool:
        """
        Cancel a running or queued job.
        
        Args:
            job_id: Job ID
            organization_id: Optional tenant ID for isolation
            
        Returns:
            True if cancelled, False if job not found or cannot be cancelled
        """
        job = self.get_job(job_id, organization_id)
        if not job:
            return False
        
        # Can only cancel CREATED, QUEUED, or PROCESSING jobs
        if job.status not in [RenderingJobStatus.CREATED, RenderingJobStatus.QUEUED, RenderingJobStatus.PROCESSING]:
            self.logger.warning(f"Cannot cancel job {job_id} in status {job.status.value}")
            return False
        
        return self.update_status(job_id, RenderingJobStatus.CANCELLED, organization_id)
    
    def retry_job(
        self,
        job_id: int,
        organization_id: Optional[int] = None,
        max_retries: Optional[int] = None
    ) -> bool:
        """
        Retry a failed job.
        
        Args:
            job_id: Job ID
            organization_id: Optional tenant ID for isolation
            max_retries: Optional max retries override
            
        Returns:
            True if retry scheduled, False if job cannot be retried
        """
        job = self.get_job(job_id, organization_id)
        if not job:
            return False
        
        # Can only retry FAILED jobs
        if job.status != RenderingJobStatus.FAILED:
            self.logger.warning(f"Cannot retry job {job_id} in status {job.status.value}")
            return False
        
        # Check retry count
        current_max = max_retries if max_retries is not None else job.max_retries
        if job.retry_count >= current_max:
            self.logger.warning(f"Job {job_id} exceeded max retries ({current_max})")
            return False
        
        job.retry_count += 1
        job.status = RenderingJobStatus.QUEUED
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        job.duration_seconds = None
        job.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        self.logger.info(f"Job {job_id} scheduled for retry (attempt {job.retry_count}/{current_max})")
        return True
    
    def list_jobs(
        self,
        organization_id: int,
        status: Optional[RenderingJobStatus] = None,
        job_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[RenderingJob], int]:
        """
        List rendering jobs with filtering and pagination.
        
        Args:
            organization_id: Tenant ID (required for isolation)
            status: Optional status filter
            job_type: Optional job type filter
            page: Page number (1-indexed)
            page_size: Items per page
            
        Returns:
            Tuple of (jobs list, total count)
        """
        query = self.db.query(RenderingJob).filter(
            RenderingJob.organization_id == organization_id
        )
        
        if status:
            query = query.filter(RenderingJob.status == status)
        if job_type:
            query = query.filter(RenderingJob.job_type == job_type)
        
        total = query.count()
        
        offset = (page - 1) * page_size
        jobs = query.order_by(RenderingJob.created_at.desc()).offset(offset).limit(page_size).all()
        
        return jobs, total
    
    def delete_job(
        self,
        job_id: int,
        organization_id: Optional[int] = None
    ) -> bool:
        """
        Delete a rendering job.
        
        Args:
            job_id: Job ID
            organization_id: Optional tenant ID for isolation
            
        Returns:
            True if deleted, False if not found
        """
        job = self.get_job(job_id, organization_id)
        if not job:
            return False
        
        self.db.delete(job)
        self.db.commit()
        
        self.logger.info(f"Deleted rendering job {job_id}")
        return True
