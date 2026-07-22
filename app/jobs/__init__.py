"""
AICF v2 Background Job System

Async job architecture using Redis-based queue with Celery integration preparation.
Supports workflow execution, status updates, and failure handling.
"""

from .queue import JobQueue, RedisJobQueue
from .worker import JobWorker
from .tasks import (
    WorkflowTask,
    StageExecutionTask,
    TaskStatus,
    TaskResult
)

__all__ = [
    "JobQueue",
    "RedisJobQueue",
    "JobWorker",
    "WorkflowTask",
    "StageExecutionTask",
    "TaskStatus",
    "TaskResult",
]
