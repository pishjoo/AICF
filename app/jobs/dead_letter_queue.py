"""
Dead Letter Queue Implementation

Handles failed jobs that exceed retry limits.
Provides storage and inspection of failed jobs for debugging and recovery.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum


class DLQReason(str, Enum):
    """Reasons for job failure."""
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    TASK_NOT_FOUND = "task_not_found"
    FATAL_ERROR = "fatal_error"
    TIMEOUT = "timeout"
    MANUAL_REJECTION = "manual_rejection"


@dataclass
class DeadLetterJob:
    """Represents a job in the dead letter queue."""
    
    job_id: str
    task_type: str
    payload: Dict[str, Any]
    error_message: str
    failure_reason: DLQReason
    retry_count: int
    max_retries: int
    original_created_at: datetime
    failed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "error_message": self.error_message,
            "failure_reason": self.failure_reason.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "original_created_at": self.original_created_at.isoformat(),
            "failed_at": self.failed_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeadLetterJob":
        return cls(
            job_id=data["job_id"],
            task_type=data["task_type"],
            payload=data["payload"],
            error_message=data["error_message"],
            failure_reason=DLQReason(data["failure_reason"]),
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
            original_created_at=datetime.fromisoformat(
                data["original_created_at"].replace('Z', '+00:00')
            ),
            failed_at=datetime.fromisoformat(
                data["failed_at"].replace('Z', '+00:00')
            ),
            metadata=data.get("metadata", {})
        )


class DeadLetterQueue:
    """
    Dead Letter Queue for storing failed jobs.
    
    Provides:
    - Storage of failed jobs with error details
    - Inspection and listing capabilities
    - Replay functionality for recovery
    - Automatic cleanup of old entries
    """
    
    def __init__(self, max_size: int = 10000, retention_days: int = 30):
        self.max_size = max_size
        self.retention_days = retention_days
        self._queue: List[DeadLetterJob] = []
        self._index: Dict[str, DeadLetterJob] = {}
        self.logger = logging.getLogger("jobs.dlq")
        self.logger.info(f"DeadLetterQueue initialized (max_size={max_size}, retention={retention_days} days)")
    
    def add(
        self,
        job_id: str,
        task_type: str,
        payload: Dict[str, Any],
        error_message: str,
        failure_reason: DLQReason,
        retry_count: int,
        max_retries: int,
        original_created_at: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a failed job to the DLQ."""
        try:
            dlq_job = DeadLetterJob(
                job_id=job_id,
                task_type=task_type,
                payload=payload,
                error_message=error_message,
                failure_reason=failure_reason,
                retry_count=retry_count,
                max_retries=max_retries,
                original_created_at=original_created_at,
                metadata=metadata or {}
            )
            
            # Check size limit
            if len(self._queue) >= self.max_size:
                # Remove oldest entry
                oldest = self._queue.pop(0)
                del self._index[oldest.job_id]
                self.logger.warning(f"DLQ full, removed oldest job: {oldest.job_id}")
            
            self._queue.append(dlq_job)
            self._index[job_id] = dlq_job
            
            self.logger.warning(
                f"Job {job_id} added to DLQ (reason: {failure_reason.value}, errors: {retry_count})"
            )
            return True
            
        except Exception as e:
            self.logger.exception(f"Failed to add job to DLQ: {e}")
            return False
    
    def get(self, job_id: str) -> Optional[DeadLetterJob]:
        """Get a specific job from the DLQ."""
        return self._index.get(job_id)
    
    def list_jobs(
        self,
        limit: int = 100,
        offset: int = 0,
        task_type: Optional[str] = None,
        reason: Optional[DLQReason] = None
    ) -> List[DeadLetterJob]:
        """List jobs in the DLQ with optional filtering."""
        filtered = self._queue
        
        if task_type:
            filtered = [j for j in filtered if j.task_type == task_type]
        
        if reason:
            filtered = [j for j in filtered if j.failure_reason == reason]
        
        # Sort by failed_at descending (most recent first)
        filtered.sort(key=lambda x: x.failed_at, reverse=True)
        
        return filtered[offset:offset + limit]
    
    def remove(self, job_id: str) -> bool:
        """Remove a job from the DLQ (e.g., after successful replay)."""
        if job_id in self._index:
            job = self._index.pop(job_id)
            self._queue.remove(job)
            self.logger.info(f"Removed job {job_id} from DLQ")
            return True
        return False
    
    def clear(self, older_than_days: Optional[int] = None) -> int:
        """Clear jobs from the DLQ. Returns count of cleared jobs."""
        if older_than_days is None:
            count = len(self._queue)
            self._queue.clear()
            self._index.clear()
            self.logger.info(f"Cleared all {count} jobs from DLQ")
            return count
        
        cutoff = datetime.now(timezone.utc).timestamp() - (older_than_days * 86400)
        to_remove = [j for j in self._queue if j.failed_at.timestamp() < cutoff]
        
        for job in to_remove:
            self._queue.remove(job)
            del self._index[job.job_id]
        
        self.logger.info(f"Cleared {len(to_remove)} old jobs from DLQ")
        return len(to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics."""
        by_reason = {}
        by_task_type = {}
        
        for job in self._queue:
            reason = job.failure_reason.value
            task_type = job.task_type
            
            by_reason[reason] = by_reason.get(reason, 0) + 1
            by_task_type[task_type] = by_task_type.get(task_type, 0) + 1
        
        return {
            "total_jobs": len(self._queue),
            "by_reason": by_reason,
            "by_task_type": by_task_type,
            "oldest_job": self._queue[0].failed_at.isoformat() if self._queue else None,
            "newest_job": self._queue[-1].failed_at.isoformat() if self._queue else None
        }
    
    def cleanup_old_jobs(self) -> int:
        """Remove jobs older than retention period."""
        return self.clear(older_than_days=self.retention_days)
