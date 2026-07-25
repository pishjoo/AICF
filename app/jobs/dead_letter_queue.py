"""
Dead Letter Queue (DLQ) Implementation

Handles failed jobs that have exceeded their maximum retry attempts.
Provides persistence, inspection, and replay capabilities for failed jobs.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from app.jobs.queue import JobMessage, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class DeadLetterEntry:
    """Represents a job entry in the dead letter queue."""
    
    job_id: str
    task_type: str
    payload: Dict[str, Any]
    original_message: Dict[str, Any]
    failure_reason: str
    retry_count: int
    max_retries: int
    failed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for storage."""
        return {
            "job_id": self.job_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "original_message": self.original_message,
            "failure_reason": self.failure_reason,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "failed_at": self.failed_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeadLetterEntry":
        """Create entry from dictionary."""
        entry = cls(
            job_id=data["job_id"],
            task_type=data["task_type"],
            payload=data["payload"],
            original_message=data.get("original_message", {}),
            failure_reason=data["failure_reason"],
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
            metadata=data.get("metadata", {})
        )
        if "failed_at" in data and data["failed_at"]:
            entry.failed_at = datetime.fromisoformat(data["failed_at"].replace('Z', '+00:00'))
        return entry


class DeadLetterQueue:
    """
    Dead Letter Queue for handling permanently failed jobs.
    
    Responsibilities:
    - Store failed jobs that exceeded retry limits
    - Provide inspection and debugging capabilities
    - Support replay/retry of failed jobs
    - Maintain retention policies
    
    This implementation uses in-memory storage with optional Redis persistence.
    For production use, integrate with Redis or a database backend.
    """
    
    def __init__(self, max_size: int = 1000, retention_days: int = 7):
        """
        Initialize the dead letter queue.
        
        Args:
            max_size: Maximum number of entries to retain (FIFO eviction).
            retention_days: Number of days to keep entries before cleanup.
        """
        self.max_size = max_size
        self.retention_days = retention_days
        self._entries: Dict[str, DeadLetterEntry] = {}
        self._order: List[str] = []  # Maintain insertion order
        self.logger = logging.getLogger("jobs.dlq")
        self.logger.info(f"DeadLetterQueue initialized (max_size={max_size}, retention={retention_days} days)")
    
    def add(self, message: JobMessage, failure_reason: str) -> None:
        """
        Add a failed job to the dead letter queue.
        
        Args:
            message: The failed job message.
            failure_reason: Description of why the job failed.
        """
        entry = DeadLetterEntry(
            job_id=message.job_id,
            task_type=message.task_type,
            payload=message.payload,
            original_message=message.to_dict(),
            failure_reason=failure_reason,
            retry_count=message.retry_count,
            max_retries=message.max_retries,
            failed_at=datetime.now(timezone.utc),
            metadata=message.metadata
        )
        
        # Check size limit and evict oldest if necessary
        if len(self._entries) >= self.max_size:
            self._evict_oldest()
        
        self._entries[message.job_id] = entry
        self._order.append(message.job_id)
        
        self.logger.warning(
            f"Job {message.job_id} ({message.task_type}) moved to DLQ: {failure_reason}"
        )
    
    def _evict_oldest(self) -> None:
        """Remove the oldest entry from the queue."""
        if self._order:
            oldest_id = self._order.pop(0)
            if oldest_id in self._entries:
                del self._entries[oldest_id]
                self.logger.debug(f"Evicted oldest DLQ entry: {oldest_id}")
    
    def get(self, job_id: str) -> Optional[DeadLetterEntry]:
        """
        Retrieve a specific entry by job ID.
        
        Args:
            job_id: The job ID to look up.
            
        Returns:
            DeadLetterEntry if found, None otherwise.
        """
        return self._entries.get(job_id)
    
    def remove(self, job_id: str) -> bool:
        """
        Remove an entry from the dead letter queue.
        
        Args:
            job_id: The job ID to remove.
            
        Returns:
            True if removed, False if not found.
        """
        if job_id in self._entries:
            del self._entries[job_id]
            if job_id in self._order:
                self._order.remove(job_id)
            self.logger.info(f"Removed DLQ entry: {job_id}")
            return True
        return False
    
    def list_entries(
        self,
        limit: int = 50,
        offset: int = 0,
        task_type: Optional[str] = None
    ) -> List[DeadLetterEntry]:
        """
        List entries in the dead letter queue.
        
        Args:
            limit: Maximum number of entries to return.
            offset: Number of entries to skip.
            task_type: Filter by task type.
            
        Returns:
            List of DeadLetterEntry objects.
        """
        entries = list(self._entries.values())
        
        # Sort by failed_at descending (newest first)
        entries.sort(key=lambda e: e.failed_at, reverse=True)
        
        # Filter by task type if specified
        if task_type:
            entries = [e for e in entries if e.task_type == task_type]
        
        # Apply pagination
        return entries[offset:offset + limit]
    
    def count(self) -> int:
        """Return the total number of entries in the DLQ."""
        return len(self._entries)
    
    def clear(self) -> int:
        """
        Clear all entries from the dead letter queue.
        
        Returns:
            Number of entries cleared.
        """
        count = len(self._entries)
        self._entries.clear()
        self._order.clear()
        self.logger.info(f"Cleared {count} entries from DLQ")
        return count
    
    def cleanup_old_entries(self) -> int:
        """
        Remove entries older than the retention period.
        
        Returns:
            Number of entries removed.
        """
        from datetime import timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        removed = 0
        
        expired_ids = [
            job_id for job_id, entry in self._entries.items()
            if entry.failed_at < cutoff
        ]
        
        for job_id in expired_ids:
            self.remove(job_id)
            removed += 1
        
        if removed > 0:
            self.logger.info(f"Cleaned up {removed} expired DLQ entries")
        
        return removed
    
    def replay_job(self, job_id: str) -> Optional[JobMessage]:
        """
        Prepare a job for replay by reconstructing the original message.
        
        Args:
            job_id: The job ID to replay.
            
        Returns:
            Reconstructed JobMessage if found, None otherwise.
        """
        entry = self.get(job_id)
        if not entry:
            return None
        
        # Reconstruct the original message
        original_data = entry.original_message.copy()
        original_data["retry_count"] = 0  # Reset retry count for replay
        
        message = JobMessage.from_dict(original_data)
        
        self.logger.info(f"Prepared job {job_id} for replay")
        return message
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the dead letter queue.
        
        Returns:
            Dictionary with DLQ statistics.
        """
        from collections import Counter
        
        if not self._entries:
            return {
                "total_entries": 0,
                "task_types": {},
                "oldest_entry": None,
                "newest_entry": None
            }
        
        entries = list(self._entries.values())
        task_type_counts = Counter(e.task_type for e in entries)
        
        oldest = min(entries, key=lambda e: e.failed_at)
        newest = max(entries, key=lambda e: e.failed_at)
        
        return {
            "total_entries": len(entries),
            "task_types": dict(task_type_counts),
            "oldest_entry": {
                "job_id": oldest.job_id,
                "failed_at": oldest.failed_at.isoformat()
            },
            "newest_entry": {
                "job_id": newest.job_id,
                "failed_at": newest.failed_at.isoformat()
            },
            "max_size": self.max_size,
            "retention_days": self.retention_days
        }
    
    def export_to_json(self) -> str:
        """
        Export all DLQ entries to JSON format.
        
        Returns:
            JSON string containing all entries.
        """
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_entries": len(self._entries),
            "entries": [entry.to_dict() for entry in self._entries.values()]
        }
        return json.dumps(data, indent=2)
    
    def import_from_json(self, json_data: str) -> int:
        """
        Import entries from a JSON export.
        
        Args:
            json_data: JSON string containing exported entries.
            
        Returns:
            Number of entries imported.
        """
        data = json.loads(json_data)
        imported = 0
        
        for entry_data in data.get("entries", []):
            try:
                entry = DeadLetterEntry.from_dict(entry_data)
                if len(self._entries) < self.max_size:
                    self._entries[entry.job_id] = entry
                    self._order.append(entry.job_id)
                    imported += 1
            except Exception as e:
                self.logger.error(f"Failed to import DLQ entry: {e}")
        
        self.logger.info(f"Imported {imported} entries into DLQ")
        return imported


# Global DLQ instance (singleton pattern for application-wide access)
_global_dlq: Optional[DeadLetterQueue] = None


def get_dead_letter_queue() -> DeadLetterQueue:
    """Get or create the global dead letter queue instance."""
    global _global_dlq
    if _global_dlq is None:
        _global_dlq = DeadLetterQueue()
    return _global_dlq


def reset_dead_letter_queue() -> None:
    """Reset the global DLQ instance (useful for testing)."""
    global _global_dlq
    _global_dlq = None
