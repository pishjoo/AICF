"""
Rendering Queue Abstraction

Background queue system for rendering jobs with Redis-compatible design.
Uses abstraction pattern similar to existing job system.
"""

import logging
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field


class RenderingQueueStatus(str, Enum):
    """Rendering queue message status."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RenderingQueueMessage:
    """Message structure for rendering queue."""
    
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""  # Reference to RenderingJob.job_id (UUID)
    task_type: str = ""  # Type of rendering task
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: float = 300.0  # 5 minutes default
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: RenderingQueueStatus = RenderingQueueStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "job_id": self.job_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RenderingQueueMessage":
        """Create from dictionary."""
        msg = cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            job_id=data.get("job_id", ""),
            task_type=data.get("task_type", ""),
            payload=data.get("payload", {}),
            priority=data.get("priority", 0),
            max_retries=data.get("max_retries", 3),
            retry_count=data.get("retry_count", 0),
            timeout_seconds=data.get("timeout_seconds", 300.0),
            metadata=data.get("metadata", {}),
            error_message=data.get("error_message")
        )
        msg.status = RenderingQueueStatus(data.get("status", "pending"))
        
        created_at = data.get("created_at")
        if created_at:
            msg.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        started_at = data.get("started_at")
        if started_at:
            msg.started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        
        completed_at = data.get("completed_at")
        if completed_at:
            msg.completed_at = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
        
        return msg
    
    def mark_queued(self):
        """Mark message as queued."""
        self.status = RenderingQueueStatus.QUEUED
    
    def mark_processing(self):
        """Mark message as processing."""
        self.status = RenderingQueueStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
    
    def mark_completed(self):
        """Mark message as completed."""
        self.status = RenderingQueueStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_failed(self, error: str):
        """Mark message as failed."""
        self.status = RenderingQueueStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_cancelled(self):
        """Mark message as cancelled."""
        self.status = RenderingQueueStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_retrying(self):
        """Mark message for retry."""
        self.status = RenderingQueueStatus.QUEUED
        self.retry_count += 1
        self.error_message = None


class RenderingQueue(ABC):
    """
    Abstract base class for rendering job queues.
    
    Provides interface for:
    - Enqueueing rendering jobs
    - Dequeueing for processing
    - Status tracking
    - Retry policy
    - Timeout handling
    """
    
    @abstractmethod
    def enqueue(self, message: RenderingQueueMessage) -> str:
        """
        Add a job to the queue.
        
        Args:
            message: Queue message to enqueue
            
        Returns:
            Message ID
        """
        pass
    
    @abstractmethod
    def dequeue(self, timeout: float = 5.0) -> Optional[RenderingQueueMessage]:
        """
        Remove and return the next job from the queue.
        
        Args:
            timeout: Seconds to wait for a job
            
        Returns:
            Next message or None if queue is empty
        """
        pass
    
    @abstractmethod
    def peek(self) -> Optional[RenderingQueueMessage]:
        """
        Return the next job without removing it.
        
        Returns:
            Next message or None
        """
        pass
    
    @abstractmethod
    def get_status(self, message_id: str) -> Optional[RenderingQueueStatus]:
        """
        Get the status of a specific job.
        
        Args:
            message_id: Message ID to check
            
        Returns:
            Status or None if not found
        """
        pass
    
    @abstractmethod
    def update_status(self, message_id: str, status: RenderingQueueStatus) -> bool:
        """
        Update the status of a job.
        
        Args:
            message_id: Message ID
            status: New status
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    def get_queue_size(self) -> int:
        """
        Return the number of jobs in the queue.
        
        Returns:
            Queue size
        """
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """
        Clear all jobs from the queue.
        
        Returns:
            Count of cleared jobs
        """
        pass
    
    @abstractmethod
    def requeue_failed(self, max_retries: int = 3) -> int:
        """
        Requeue failed jobs that haven't exceeded max retries.
        
        Args:
            max_retries: Maximum retry attempts
            
        Returns:
            Count of requeued jobs
        """
        pass


class InMemoryRenderingQueue(RenderingQueue):
    """
    In-memory rendering queue implementation for testing and development.
    
    Note: Not suitable for production as it doesn't persist jobs.
    Use RedisRenderingQueue for production deployments.
    """
    
    def __init__(self):
        self._queue: List[RenderingQueueMessage] = []
        self._status_index: Dict[str, RenderingQueueStatus] = {}
        self._message_index: Dict[str, RenderingQueueMessage] = {}
        self.logger = logging.getLogger("rendering.queue.memory")
    
    def enqueue(self, message: RenderingQueueMessage) -> str:
        message.mark_queued()
        self._status_index[message.message_id] = RenderingQueueStatus.QUEUED
        self._message_index[message.message_id] = message
        
        # Insert based on priority (higher priority first)
        insert_idx = len(self._queue)
        for i, existing in enumerate(self._queue):
            if existing.priority < message.priority:
                insert_idx = i
                break
        self._queue.insert(insert_idx, message)
        
        self.logger.debug(f"Enqueued rendering job {message.message_id} ({message.task_type}) with priority {message.priority}")
        return message.message_id
    
    def dequeue(self, timeout: float = 5.0) -> Optional[RenderingQueueMessage]:
        if not self._queue:
            return None
        
        message = self._queue.pop(0)
        message.mark_processing()
        self._status_index[message.message_id] = RenderingQueueStatus.PROCESSING
        
        self.logger.debug(f"Dequeued rendering job {message.message_id}")
        return message
    
    def peek(self) -> Optional[RenderingQueueMessage]:
        return self._queue[0] if self._queue else None
    
    def get_status(self, message_id: str) -> Optional[RenderingQueueStatus]:
        return self._status_index.get(message_id)
    
    def update_status(self, message_id: str, status: RenderingQueueStatus) -> bool:
        if message_id in self._status_index:
            self._status_index[message_id] = status
            # Also update in queue if present
            for msg in self._queue:
                if msg.message_id == message_id:
                    msg.status = status
                    break
            # Update in message index
            if message_id in self._message_index:
                self._message_index[message_id].status = status
            return True
        return False
    
    def get_queue_size(self) -> int:
        return len(self._queue)
    
    def clear(self) -> int:
        count = len(self._queue)
        self._queue.clear()
        self._status_index.clear()
        self._message_index.clear()
        return count
    
    def requeue_failed(self, max_retries: int = 3) -> int:
        requeued = 0
        for msg in list(self._message_index.values()):
            if msg.status == RenderingQueueStatus.FAILED and msg.retry_count < max_retries:
                msg.mark_retrying()
                self._status_index[msg.message_id] = RenderingQueueStatus.QUEUED
                self._queue.append(msg)
                requeued += 1
        return requeued


class RedisRenderingQueue(RenderingQueue):
    """
    Redis-based rendering queue implementation for production use.
    
    Uses Redis sorted sets for priority queue and hashes for status tracking.
    Prepared for Celery integration.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        queue_name: str = "aicf_rendering_jobs"
    ):
        try:
            import redis
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()  # Test connection
            self.connected = True
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}. Falling back to in-memory queue.")
            self.connected = False
            self._fallback = InMemoryRenderingQueue()
        
        self.queue_key = f"{queue_name}:queue"
        self.status_prefix = f"{queue_name}:status"
        self.data_prefix = f"{queue_name}:data"
        self.failed_prefix = f"{queue_name}:failed"
        self.logger = logging.getLogger("rendering.queue.redis")
    
    def _check_connection(self) -> bool:
        if not hasattr(self, 'connected') or not self.connected:
            return False
        try:
            self.redis.ping()
            return True
        except Exception:
            return False
    
    def enqueue(self, message: RenderingQueueMessage) -> str:
        if not self._check_connection():
            return self._fallback.enqueue(message)
        
        message.mark_queued()
        
        # Store job data
        job_data = json.dumps(message.to_dict())
        self.redis.set(f"{self.data_prefix}:{message.message_id}", job_data)
        
        # Add to priority queue (sorted set)
        score = -message.priority  # Higher priority = lower score = processed first
        self.redis.zadd(self.queue_key, {message.message_id: score})
        
        # Set initial status
        self.redis.hset(f"{self.status_prefix}", message.message_id, RenderingQueueStatus.QUEUED.value)
        
        self.logger.info(f"Enqueued rendering job {message.message_id} ({message.task_type}) with priority {message.priority}")
        return message.message_id
    
    def dequeue(self, timeout: float = 5.0) -> Optional[RenderingQueueMessage]:
        if not self._check_connection():
            return self._fallback.dequeue(timeout)
        
        # Block waiting for job with timeout
        result = self.redis.bzpopmin(self.queue_key, timeout=int(timeout))
        if not result:
            return None
        
        _, message_id, _ = result
        job_data = self.redis.get(f"{self.data_prefix}:{message_id}")
        if not job_data:
            return None
        
        message = RenderingQueueMessage.from_dict(json.loads(job_data))
        message.mark_processing()
        
        # Update stored data
        self.redis.set(f"{self.data_prefix}:{message_id}", json.dumps(message.to_dict()))
        self.redis.hset(f"{self.status_prefix}", message_id, RenderingQueueStatus.PROCESSING.value)
        
        self.logger.debug(f"Dequeued rendering job {message_id}")
        return message
    
    def peek(self) -> Optional[RenderingQueueMessage]:
        if not self._check_connection():
            return self._fallback.peek()
        
        result = self.redis.zrange(self.queue_key, 0, 0)
        if not result:
            return None
        
        message_id = result[0]
        job_data = self.redis.get(f"{self.data_prefix}:{message_id}")
        if not job_data:
            return None
        
        return RenderingQueueMessage.from_dict(json.loads(job_data))
    
    def get_status(self, message_id: str) -> Optional[RenderingQueueStatus]:
        if not self._check_connection():
            return self._fallback.get_status(message_id)
        
        status = self.redis.hget(f"{self.status_prefix}", message_id)
        if status:
            return RenderingQueueStatus(status)
        return None
    
    def update_status(self, message_id: str, status: RenderingQueueStatus) -> bool:
        if not self._check_connection():
            return self._fallback.update_status(message_id, status)
        
        self.redis.hset(f"{self.status_prefix}", message_id, status.value)
        
        # Also update in stored data
        job_data = self.redis.get(f"{self.data_prefix}:{message_id}")
        if job_data:
            message = RenderingQueueMessage.from_dict(json.loads(job_data))
            message.status = status
            self.redis.set(f"{self.data_prefix}:{message_id}", json.dumps(message.to_dict()))
        return True
    
    def get_queue_size(self) -> int:
        if not self._check_connection():
            return self._fallback.get_queue_size()
        
        return self.redis.zcard(self.queue_key)
    
    def clear(self) -> int:
        if not self._check_connection():
            return self._fallback.clear()
        
        count = self.redis.zcard(self.queue_key)
        
        # Clear all job data
        job_ids = self.redis.zrange(self.queue_key, 0, -1)
        for job_id in job_ids:
            self.redis.delete(f"{self.data_prefix}:{job_id}")
        self.redis.delete(self.queue_key)
        self.redis.delete(f"{self.status_prefix}")
        self.redis.delete(f"{self.failed_prefix}")
        
        self.logger.info(f"Cleared {count} jobs from rendering queue")
        return count
    
    def requeue_failed(self, max_retries: int = 3) -> int:
        if not self._check_connection():
            return self._fallback.requeue_failed(max_retries)
        
        requeued = 0
        # Scan for failed jobs
        failed_jobs = self.redis.hgetall(f"{self.status_prefix}")
        for message_id, status in failed_jobs.items():
            if status == RenderingQueueStatus.FAILED.value:
                job_data = self.redis.get(f"{self.data_prefix}:{message_id}")
                if job_data:
                    message = RenderingQueueMessage.from_dict(json.loads(job_data))
                    if message.retry_count < max_retries:
                        message.mark_retrying()
                        self.enqueue(message)
                        requeued += 1
        
        return requeued
