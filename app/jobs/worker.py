"""
Job Worker Implementation

Worker process for consuming jobs from the queue and executing tasks.
Prepared for Celery integration.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional, Type
from datetime import datetime, timezone, timedelta

from .queue import JobQueue, JobMessage, TaskStatus, TaskResult, InMemoryJobQueue
from .dead_letter_queue import DeadLetterQueue, DLQReason


class TaskDefinition:
    """Definition of a task type."""
    
    def __init__(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], TaskResult],
        max_retries: int = 3,
        timeout: float = 300.0,  # 5 minutes default
        retry_backoff_base: float = 2.0,
        retry_backoff_max: float = 60.0
    ):
        self.name = name
        self.handler = handler
        self.max_retries = max_retries
        self.timeout = timeout
        self.retry_backoff_base = retry_backoff_base
        self.retry_backoff_max = retry_backoff_max
        self.logger = logging.getLogger(f"jobs.tasks.{name}")


class JobWorker:
    """
    Job worker that processes jobs from the queue.
    
    Responsibilities:
    - Consume jobs from queue
    - Execute task handlers
    - Handle retries on failure with exponential backoff
    - Update job status
    - Log execution metrics
    - Move failed jobs to dead letter queue
    """
    
    def __init__(
        self,
        queue: Optional[JobQueue] = None,
        dlq: Optional[DeadLetterQueue] = None,
        shutdown_timeout: float = 5.0
    ):
        self.queue = queue or InMemoryJobQueue()
        self.dlq = dlq or DeadLetterQueue()
        self.tasks: Dict[str, TaskDefinition] = {}
        self.running = False
        self.shutdown_timeout = shutdown_timeout
        self.logger = logging.getLogger("jobs.worker")
        self.processed_count = 0
        self.failed_count = 0
        self.retry_count = 0
    
    def register_task(self, task_def: TaskDefinition) -> None:
        """Register a task handler."""
        self.tasks[task_def.name] = task_def
        self.logger.info(f"Registered task: {task_def.name} (max_retries={task_def.max_retries})")
    
    def _calculate_backoff_delay(self, retry_count: int, task_def: TaskDefinition) -> float:
        """Calculate exponential backoff delay with jitter."""
        import random
        
        # Exponential backoff: base^retry_count
        delay = min(
            task_def.retry_backoff_base ** retry_count,
            task_def.retry_backoff_max
        )
        
        # Add jitter (±10%)
        jitter = delay * 0.1 * (random.random() * 2 - 1)
        delay += jitter
        
        return max(0.1, delay)  # Minimum 100ms
    
    def _execute_task(self, message: JobMessage) -> TaskResult:
        """Execute a task based on its type."""
        task_def = self.tasks.get(message.task_type)
        
        if not task_def:
            error_msg = f"Unknown task type: {message.task_type}"
            self.logger.error(error_msg)
            return TaskResult.failure(error_msg)
        
        try:
            self.logger.info(f"Executing task {message.job_id} ({message.task_type})")
            
            # Execute with timeout (simplified - use threading in production)
            result = task_def.handler(message.payload)
            return result
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            self.logger.exception(error_msg)
            return TaskResult.failure(error_msg, {"exception_type": type(e).__name__})
    
    def _handle_retry(self, message: JobMessage, task_def: TaskDefinition) -> bool:
        """
        Handle retry logic for failed jobs with exponential backoff.
        
        Returns True if job will be retried, False otherwise.
        """
        if message.retry_count >= message.max_retries:
            self.logger.warning(
                f"Job {message.job_id} exceeded max retries ({message.max_retries})"
            )
            return False
        
        # Calculate backoff delay
        delay = self._calculate_backoff_delay(message.retry_count, task_def)
        
        self.logger.info(
            f"Retrying job {message.job_id} in {delay:.2f}s "
            f"(attempt {message.retry_count + 1}/{message.max_retries})"
        )
        
        # Re-enqueue with incremented retry count
        message.mark_retrying()
        
        # For now, use blocking sleep; in production use delayed queue
        time.sleep(delay)
        self.queue.enqueue(message)
        
        self.retry_count += 1
        return True
    
    def _send_to_dlq(self, message: JobMessage, error_message: str, reason: DLQReason) -> None:
        """Send a failed job to the dead letter queue."""
        self.dlq.add(
            job_id=message.job_id,
            task_type=message.task_type,
            payload=message.payload,
            error_message=error_message,
            failure_reason=reason,
            retry_count=message.retry_count,
            max_retries=message.max_retries,
            original_created_at=message.created_at,
            metadata=message.metadata
        )
        self.failed_count += 1
    
    def process_job(self, message: JobMessage) -> bool:
        """
        Process a single job.
        
        Returns True if job completed successfully, False otherwise.
        """
        job_id = message.job_id
        task_type = message.task_type
        
        self.logger.debug(f"Processing job {job_id} ({task_type})")
        
        # Get task definition
        task_def = self.tasks.get(task_type)
        
        if not task_def:
            # Unknown task - send directly to DLQ
            error_msg = f"Unknown task type: {task_type}"
            self._send_to_dlq(message, error_msg, DLQReason.TASK_NOT_FOUND)
            self.queue.update_status(job_id, TaskStatus.FAILED)
            self.logger.error(f"Job {job_id} sent to DLQ: {error_msg}")
            return False
        
        # Execute the task
        result = self._execute_task(message)
        
        # Update job status based on result
        if result.status == TaskStatus.COMPLETED:
            message.mark_completed()
            self.queue.update_status(job_id, TaskStatus.COMPLETED)
            self.processed_count += 1
            self.logger.info(f"Job {job_id} completed successfully")
            return True
        else:
            # Handle retry with exponential backoff
            if self._handle_retry(message, task_def):
                self.logger.info(f"Job {job_id} scheduled for retry")
                self.queue.update_status(job_id, TaskStatus.RETRYING)
                return False
            
            # Max retries exceeded - send to DLQ
            message.mark_failed()
            self._send_to_dlq(
                message,
                result.error or "Max retries exceeded",
                DLQReason.MAX_RETRIES_EXCEEDED
            )
            self.queue.update_status(job_id, TaskStatus.FAILED)
            self.logger.error(f"Job {job_id} sent to DLQ after {message.retry_count} retries")
            return False
    
    def run(self, max_jobs: Optional[int] = None, poll_interval: float = 1.0) -> None:
        """
        Run the worker loop.
        
        Args:
            max_jobs: Maximum number of jobs to process (None for unlimited)
            poll_interval: Seconds to wait between queue polls when empty
        """
        self.running = True
        self.logger.info(f"Starting worker (max_jobs={max_jobs}, poll_interval={poll_interval}s)")
        
        jobs_processed = 0
        
        try:
            while self.running:
                if max_jobs and jobs_processed >= max_jobs:
                    self.logger.info(f"Reached max jobs limit: {max_jobs}")
                    break
                
                message = self.queue.dequeue(timeout=poll_interval)
                
                if message:
                    success = self.process_job(message)
                    if success:
                        jobs_processed += 1
                else:
                    # Queue is empty, continue polling
                    continue
                    
        except KeyboardInterrupt:
            self.logger.info("Worker interrupted by user")
        finally:
            self.running = False
            self.logger.info(
                f"Worker stopped. Processed: {self.processed_count}, "
                f"Failed: {self.failed_count}, Retries: {self.retry_count}"
            )
    
    def stop(self) -> None:
        """Stop the worker gracefully."""
        self.logger.info("Stopping worker...")
        self.running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            "running": self.running,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "retry_count": self.retry_count,
            "queue_size": self.queue.get_queue_size(),
            "dlq_size": len(self.dlq.list_jobs(limit=1)),
            "registered_tasks": list(self.tasks.keys())
        }
