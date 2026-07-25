"""
Job Worker Implementation

Worker process for consuming jobs from the queue and executing tasks.
Prepared for Celery integration.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional, Type
from datetime import datetime, timezone

from .queue import JobQueue, JobMessage, TaskStatus, TaskResult, InMemoryJobQueue


class TaskDefinition:
    """Definition of a task type."""
    
    def __init__(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], TaskResult],
        max_retries: int = 3,
        timeout: float = 300.0  # 5 minutes default
    ):
        self.name = name
        self.handler = handler
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logging.getLogger(f"jobs.tasks.{name}")


class JobWorker:
    """
    Job worker that processes jobs from the queue.
    
    Responsibilities:
    - Consume jobs from queue
    - Execute task handlers
    - Handle retries on failure
    - Update job status
    - Log execution metrics
    """
    
    def __init__(
        self,
        queue: Optional[JobQueue] = None,
        shutdown_timeout: float = 5.0
    ):
        self.queue = queue or InMemoryJobQueue()
        self.tasks: Dict[str, TaskDefinition] = {}
        self.running = False
        self.shutdown_timeout = shutdown_timeout
        self.logger = logging.getLogger("jobs.worker")
        self.processed_count = 0
        self.failed_count = 0
    
    def register_task(self, task_def: TaskDefinition) -> None:
        """Register a task handler."""
        self.tasks[task_def.name] = task_def
        self.logger.info(f"Registered task: {task_def.name}")
    
    def _execute_task(self, message: JobMessage) -> TaskResult:
        """Execute a task based on its type."""
        task_def = self.tasks.get(message.task_type)
        
        if not task_def:
            error_msg = f"Unknown task type: {message.task_type}"
            self.logger.error(error_msg)
            return TaskResult.failure(error_msg)
        
        try:
            self.logger.info(f"Executing task {message.job_id} ({message.task_type})")
            result = task_def.handler(message.payload)
            return result
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            self.logger.exception(error_msg)
            return TaskResult.failure(error_msg, {"exception_type": type(e).__name__})
    
    def _handle_retry(self, message: JobMessage) -> bool:
        """
        Handle retry logic for failed jobs.
        
        Returns True if job will be retried, False otherwise.
        """
        from .dead_letter_queue import get_dead_letter_queue
        
        if message.retry_count >= message.max_retries:
            self.logger.warning(
                f"Job {message.job_id} exceeded max retries ({message.max_retries})"
            )
            # Move to dead letter queue
            dlq = get_dead_letter_queue()
            dlq.add(message, f"Exceeded max retries ({message.max_retries})")
            return False
        
        # Exponential backoff could be implemented here
        delay = min(2 ** message.retry_count, 60)  # Max 60 seconds
        self.logger.info(
            f"Retrying job {message.job_id} in {delay}s (attempt {message.retry_count + 1}/{message.max_retries})"
        )
        
        # Re-enqueue with incremented retry count
        message.mark_retrying()
        time.sleep(delay)  # Simple blocking delay; use delayed queue in production
        self.queue.enqueue(message)
        
        return True
    
    def process_job(self, message: JobMessage) -> bool:
        """
        Process a single job.
        
        Returns True if job completed successfully, False otherwise.
        """
        job_id = message.job_id
        task_type = message.task_type
        
        self.logger.debug(f"Processing job {job_id} ({task_type})")
        
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
            # Handle retry
            if self._handle_retry(message):
                self.logger.info(f"Job {job_id} scheduled for retry")
                return False
            
            # Max retries exceeded
            message.mark_failed()
            self.queue.update_status(job_id, TaskStatus.FAILED)
            self.failed_count += 1
            self.logger.error(f"Job {job_id} failed permanently: {result.error}")
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
                f"Worker stopped. Processed: {self.processed_count}, Failed: {self.failed_count}"
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
            "queue_size": self.queue.get_queue_size(),
            "registered_tasks": list(self.tasks.keys())
        }
