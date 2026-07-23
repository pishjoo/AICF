"""
Distributed Rendering Workers

Multi-worker support with registration, heartbeat, and job claiming.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.rendering.worker import RenderingWorker, RenderingTaskDefinition
from app.rendering.queue import RenderingQueue, RenderingQueueMessage


@dataclass
class WorkerRegistration:
    """Registered worker information."""
    worker_id: str
    registered_at: float
    last_heartbeat: float
    current_job_id: Optional[str] = None
    jobs_processed: int = 0
    status: str = "active"  # active, busy, offline
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "current_job_id": self.current_job_id,
            "jobs_processed": self.jobs_processed,
            "status": self.status,
            "metadata": self.metadata
        }


class DistributedRenderingWorker(RenderingWorker):
    """
    Distributed rendering worker with registration and heartbeat.
    
    Features:
    - Multiple workers
    - Worker registration
    - Heartbeat monitoring
    - Job claiming
    - Worker failure detection
    """
    
    _registry: Dict[str, WorkerRegistration] = {}
    
    def __init__(
        self,
        queue: Optional[RenderingQueue] = None,
        worker_id: Optional[str] = None,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 90.0
    ):
        super().__init__(queue=queue)
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.registration: Optional[WorkerRegistration] = None
        self.logger = logging.getLogger(f"rendering.worker.distributed.{self.worker_id}")
        
    def register(self, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register this worker with the system."""
        now = time.time()
        
        self.registration = WorkerRegistration(
            worker_id=self.worker_id,
            registered_at=now,
            last_heartbeat=now,
            metadata=metadata or {}
        )
        
        DistributedRenderingWorker._registry[self.worker_id] = self.registration
        self.logger.info(f"Worker {self.worker_id} registered")
        return True
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to indicate worker is alive."""
        if not self.registration:
            return False
        
        now = time.time()
        self.registration.last_heartbeat = now
        
        if self.registration.status == "offline":
            self.registration.status = "active"
        
        return True
    
    def claim_job(self, message: RenderingQueueMessage) -> bool:
        """Claim a job for processing."""
        if not self.registration:
            return False
        
        if self.registration.status == "busy":
            return False
        
        self.registration.current_job_id = message.message_id
        self.registration.status = "busy"
        self.logger.info(f"Worker {self.worker_id} claimed job {message.message_id}")
        return True
    
    def release_job(self, success: bool = True) -> None:
        """Release current job after processing."""
        if not self.registration:
            return
        
        if self.registration.current_job_id:
            self.registration.jobs_processed += 1
            self.registration.current_job_id = None
            self.registration.status = "active"
            
            status_str = "successfully" if success else "with failure"
            self.logger.info(f"Worker {self.worker_id} released job {status_str}")
    
    def process_job(self, message: RenderingQueueMessage) -> bool:
        """Process a job with proper claiming and release."""
        if not self.claim_job(message):
            return False
        
        try:
            result = super().process_job(message)
            self.release_job(success=result)
            return result
        except Exception as e:
            self.logger.exception(f"Job processing failed: {e}")
            self.release_job(success=False)
            return False
    
    @classmethod
    def get_active_workers(cls) -> List[WorkerRegistration]:
        """Get all active workers."""
        now = time.time()
        active = []
        
        for worker in cls._registry.values():
            if now - worker.last_heartbeat < 90:  # Default timeout
                active.append(worker)
        
        return active
    
    @classmethod
    def detect_failed_workers(cls, timeout_seconds: float = 90.0) -> List[str]:
        """Detect workers that have failed (no heartbeat)."""
        now = time.time()
        failed = []
        
        for worker_id, worker in cls._registry.items():
            if now - worker.last_heartbeat > timeout_seconds:
                worker.status = "offline"
                failed.append(worker_id)
        
        return failed
    
    @classmethod
    def requeue_stale_jobs(cls, queue: RenderingQueue) -> int:
        """Requeue jobs from failed workers."""
        failed_workers = cls.detect_failed_workers()
        requeued = 0
        
        for worker_id in failed_workers:
            worker = cls._registry.get(worker_id)
            if worker and worker.current_job_id:
                # In real implementation, would fetch job and requeue
                worker.current_job_id = None
                requeued += 1
        
        return requeued
