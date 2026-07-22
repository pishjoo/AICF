"""
Job Queue Abstraction

Redis-based queue architecture with Celery integration preparation.
Provides interface for job enqueueing, dequeueing, and status tracking.
"""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskResult:
    """Result of task execution."""
    
    def __init__(
        self,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.result = result or {}
        self.error = error
        self.metadata = metadata or {}
        self.completed_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def success(cls, result: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> "TaskResult":
        return cls(status=TaskStatus.COMPLETED, result=result, metadata=metadata)
    
    @classmethod
    def failure(cls, error: str, metadata: Optional[Dict[str, Any]] = None) -> "TaskResult":
        return cls(status=TaskStatus.FAILED, error=error, metadata=metadata)


class JobMessage:
    """Message structure for job queue."""
    
    def __init__(
        self,
        task_type: str,
        payload: Dict[str, Any],
        job_id: Optional[str] = None,
        priority: int = 0,
        max_retries: int = 3,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.job_id = job_id or str(uuid.uuid4())
        self.task_type = task_type
        self.payload = payload
        self.priority = priority
        self.max_retries = max_retries
        self.retry_count = retry_count
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.status = TaskStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobMessage":
        msg = cls(
            task_type=data["task_type"],
            payload=data["payload"],
            job_id=data.get("job_id"),
            priority=data.get("priority", 0),
            max_retries=data.get("max_retries", 3),
            retry_count=data.get("retry_count", 0),
            metadata=data.get("metadata")
        )
        msg.status = TaskStatus(data.get("status", "pending"))
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
    
    def mark_running(self):
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
    
    def mark_completed(self):
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_failed(self):
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_retrying(self):
        self.status = TaskStatus.RETRYING
        self.retry_count += 1


class JobQueue(ABC):
    """Abstract base class for job queues."""
    
    @abstractmethod
    def enqueue(self, message: JobMessage) -> str:
        """Add a job to the queue. Returns job_id."""
        pass
    
    @abstractmethod
    def dequeue(self, timeout: float = 5.0) -> Optional[JobMessage]:
        """Remove and return the next job from the queue."""
        pass
    
    @abstractmethod
    def peek(self) -> Optional[JobMessage]:
        """Return the next job without removing it."""
        pass
    
    @abstractmethod
    def get_status(self, job_id: str) -> Optional[TaskStatus]:
        """Get the status of a specific job."""
        pass
    
    @abstractmethod
    def update_status(self, job_id: str, status: TaskStatus) -> bool:
        """Update the status of a job."""
        pass
    
    @abstractmethod
    def get_queue_size(self) -> int:
        """Return the number of jobs in the queue."""
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """Clear all jobs from the queue. Returns count of cleared jobs."""
        pass


class InMemoryJobQueue(JobQueue):
    """
    In-memory job queue implementation for testing and development.
    
    Note: This is not suitable for production as it doesn't persist jobs.
    Use RedisJobQueue for production deployments.
    """
    
    def __init__(self):
        self._queue: List[JobMessage] = []
        self._status_index: Dict[str, TaskStatus] = {}
        self._lock = False  # Simple lock for thread safety
        self.logger = logging.getLogger("jobs.queue.memory")
    
    def enqueue(self, message: JobMessage) -> str:
        message.status = TaskStatus.QUEUED
        self._status_index[message.job_id] = TaskStatus.QUEUED
        # Insert based on priority (higher priority first)
        insert_idx = len(self._queue)
        for i, existing in enumerate(self._queue):
            if existing.priority < message.priority:
                insert_idx = i
                break
        self._queue.insert(insert_idx, message)
        self.logger.debug(f"Enqueued job {message.job_id} ({message.task_type}) with priority {message.priority}")
        return message.job_id
    
    def dequeue(self, timeout: float = 5.0) -> Optional[JobMessage]:
        if not self._queue:
            return None
        message = self._queue.pop(0)
        message.mark_running()
        self._status_index[message.job_id] = TaskStatus.RUNNING
        self.logger.debug(f"Dequeued job {message.job_id}")
        return message
    
    def peek(self) -> Optional[JobMessage]:
        return self._queue[0] if self._queue else None
    
    def get_status(self, job_id: str) -> Optional[TaskStatus]:
        return self._status_index.get(job_id)
    
    def update_status(self, job_id: str, status: TaskStatus) -> bool:
        if job_id in self._status_index:
            self._status_index[job_id] = status
            # Also update in queue if present
            for msg in self._queue:
                if msg.job_id == job_id:
                    msg.status = status
                    break
            return True
        return False
    
    def get_queue_size(self) -> int:
        return len(self._queue)
    
    def clear(self) -> int:
        count = len(self._queue)
        self._queue.clear()
        self._status_index.clear()
        return count


class RedisJobQueue(JobQueue):
    """
    Redis-based job queue implementation for production use.
    
    Uses Redis lists for queue storage and hashes for status tracking.
    Prepared for Celery integration.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", queue_name: str = "aicf_jobs"):
        try:
            import redis
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()  # Test connection
            self.connected = True
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}. Falling back to in-memory queue.")
            self.connected = False
            self._fallback = InMemoryJobQueue()
        
        self.queue_key = f"{queue_name}:queue"
        self.status_prefix = f"{queue_name}:status"
        self.data_prefix = f"{queue_name}:data"
        self.logger = logging.getLogger("jobs.queue.redis")
    
    def _check_connection(self) -> bool:
        if not hasattr(self, 'connected') or not self.connected:
            return False
        try:
            self.redis.ping()
            return True
        except Exception:
            return False
    
    def enqueue(self, message: JobMessage) -> str:
        if not self._check_connection():
            return self._fallback.enqueue(message)
        
        message.status = TaskStatus.QUEUED
        # Store job data
        job_data = json.dumps(message.to_dict())
        self.redis.set(f"{self.data_prefix}:{message.job_id}", job_data)
        # Add to queue (with priority using sorted set)
        score = -message.priority  # Higher priority = lower score = processed first
        self.redis.zadd(self.queue_key, {message.job_id: score})
        # Set initial status
        self.redis.hset(f"{self.status_prefix}", message.job_id, TaskStatus.QUEUED.value)
        
        self.logger.info(f"Enqueued job {message.job_id} ({message.task_type}) with priority {message.priority}")
        return message.job_id
    
    def dequeue(self, timeout: float = 5.0) -> Optional[JobMessage]:
        if not self._check_connection():
            return self._fallback.dequeue(timeout)
        
        # Block waiting for job with timeout
        result = self.redis.bzpopmin(self.queue_key, timeout=int(timeout))
        if not result:
            return None
        
        _, job_id, _ = result
        job_data = self.redis.get(f"{self.data_prefix}:{job_id}")
        if not job_data:
            return None
        
        message = JobMessage.from_dict(json.loads(job_data))
        message.mark_running()
        # Update stored data
        self.redis.set(f"{self.data_prefix}:{job_id}", json.dumps(message.to_dict()))
        self.redis.hset(f"{self.status_prefix}", job_id, TaskStatus.RUNNING.value)
        
        self.logger.debug(f"Dequeued job {job_id}")
        return message
    
    def peek(self) -> Optional[JobMessage]:
        if not self._check_connection():
            return self._fallback.peek()
        
        result = self.redis.zrange(self.queue_key, 0, 0)
        if not result:
            return None
        
        job_id = result[0]
        job_data = self.redis.get(f"{self.data_prefix}:{job_id}")
        if not job_data:
            return None
        
        return JobMessage.from_dict(json.loads(job_data))
    
    def get_status(self, job_id: str) -> Optional[TaskStatus]:
        if not self._check_connection():
            return self._fallback.get_status(job_id)
        
        status = self.redis.hget(f"{self.status_prefix}", job_id)
        if status:
            return TaskStatus(status)
        return None
    
    def update_status(self, job_id: str, status: TaskStatus) -> bool:
        if not self._check_connection():
            return self._fallback.update_status(job_id, status)
        
        self.redis.hset(f"{self.status_prefix}", job_id, status.value)
        # Also update in stored data
        job_data = self.redis.get(f"{self.data_prefix}:{job_id}")
        if job_data:
            message = JobMessage.from_dict(json.loads(job_data))
            message.status = status
            self.redis.set(f"{self.data_prefix}:{job_id}", json.dumps(message.to_dict()))
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
        
        self.logger.info(f"Cleared {count} jobs from queue")
        return count
