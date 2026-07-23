"""
Rendering Monitoring System

Metrics collection and monitoring for video rendering operations.
Tracks render duration, resource usage, queue latency, and worker performance.
"""

import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict


class MetricType(str, Enum):
    """Types of metrics collected."""
    
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    """Single metric data point."""
    
    name: str
    value: float
    timestamp: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "metric_type": self.metric_type.value,
            "labels": self.labels
        }


@dataclass
class RenderMetrics:
    """Metrics for a single rendering job."""
    
    job_id: str
    organization_id: str
    
    # Timing metrics
    total_duration_seconds: float = 0.0
    timeline_generation_seconds: float = 0.0
    composition_seconds: float = 0.0
    audio_sync_seconds: float = 0.0
    ffmpeg_execution_seconds: float = 0.0
    thumbnail_generation_seconds: float = 0.0
    export_seconds: float = 0.0
    
    # Resource metrics
    cpu_usage_percent: float = 0.0
    gpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0
    
    # Processing metrics
    frames_processed: int = 0
    fps_average: float = 0.0
    output_size_bytes: int = 0
    
    # Queue metrics
    queue_wait_seconds: float = 0.0
    worker_assignment_time: float = 0.0
    
    # Error tracking
    retry_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Cost metrics
    estimated_cost_cents: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "organization_id": self.organization_id,
            "timing": {
                "total_duration_seconds": self.total_duration_seconds,
                "timeline_generation_seconds": self.timeline_generation_seconds,
                "composition_seconds": self.composition_seconds,
                "audio_sync_seconds": self.audio_sync_seconds,
                "ffmpeg_execution_seconds": self.ffmpeg_execution_seconds,
                "thumbnail_generation_seconds": self.thumbnail_generation_seconds,
                "export_seconds": self.export_seconds,
            },
            "resources": {
                "cpu_usage_percent": self.cpu_usage_percent,
                "gpu_usage_percent": self.gpu_usage_percent,
                "memory_usage_mb": self.memory_usage_mb,
                "peak_memory_mb": self.peak_memory_mb,
            },
            "processing": {
                "frames_processed": self.frames_processed,
                "fps_average": self.fps_average,
                "output_size_bytes": self.output_size_bytes,
            },
            "queue": {
                "queue_wait_seconds": self.queue_wait_seconds,
                "worker_assignment_time": self.worker_assignment_time,
            },
            "errors": {
                "retry_count": self.retry_count,
                "error_count": self.error_count,
                "last_error": self.last_error,
            },
            "cost": {
                "estimated_cost_cents": self.estimated_cost_cents,
            }
        }


@dataclass
class WorkerMetrics:
    """Metrics for a rendering worker."""
    
    worker_id: str
    jobs_processed: int = 0
    jobs_failed: int = 0
    current_job_id: Optional[str] = None
    uptime_seconds: float = 0.0
    average_job_duration: float = 0.0
    last_heartbeat: float = field(default_factory=lambda: time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "jobs_processed": self.jobs_processed,
            "jobs_failed": self.jobs_failed,
            "current_job_id": self.current_job_id,
            "uptime_seconds": self.uptime_seconds,
            "average_job_duration": self.average_job_duration,
            "last_heartbeat": self.last_heartbeat,
            "success_rate": (
                self.jobs_processed / (self.jobs_processed + self.jobs_failed) * 100
                if (self.jobs_processed + self.jobs_failed) > 0 else 0.0
            )
        }


class RenderingMetrics:
    """
    Central metrics collection for rendering system.
    
    Tracks:
    - Render duration
    - Frames processed
    - CPU usage
    - GPU usage
    - Memory usage
    - Queue latency
    - Worker performance
    """
    
    def __init__(self):
        self.logger = logging.getLogger("rendering.monitoring.metrics")
        
        # Job-level metrics
        self._job_metrics: Dict[str, RenderMetrics] = {}
        
        # Worker metrics
        self._worker_metrics: Dict[str, WorkerMetrics] = {}
        
        # Aggregated metrics
        self._total_jobs_started: int = 0
        self._total_jobs_completed: int = 0
        self._total_jobs_failed: int = 0
        
        # Histograms for timing
        self._render_duration_histogram: List[float] = []
        self._queue_latency_histogram: List[float] = []
        
        # Time series data (limited size)
        self._time_series_max_size = 1000
        self._time_series: List[MetricPoint] = []
    
    def start_job_tracking(
        self,
        job_id: str,
        organization_id: str,
        queued_at: Optional[float] = None
    ) -> RenderMetrics:
        """Start tracking metrics for a new rendering job."""
        now = time.time()
        
        metrics = RenderMetrics(
            job_id=job_id,
            organization_id=organization_id
        )
        
        # Calculate queue wait time if job was queued earlier
        if queued_at:
            metrics.queue_wait_seconds = now - queued_at
            self._record_queue_latency(now - queued_at)
        
        self._job_metrics[job_id] = metrics
        self._total_jobs_started += 1
        
        self.logger.debug(f"Started tracking metrics for job {job_id}")
        return metrics
    
    def update_job_metrics(
        self,
        job_id: str,
        **kwargs
    ) -> Optional[RenderMetrics]:
        """Update metrics for an existing job."""
        if job_id not in self._job_metrics:
            self.logger.warning(f"Cannot update metrics for unknown job {job_id}")
            return None
        
        metrics = self._job_metrics[job_id]
        
        for key, value in kwargs.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)
        
        # Track peak memory
        if 'memory_usage_mb' in kwargs:
            if kwargs['memory_usage_mb'] > metrics.peak_memory_mb:
                metrics.peak_memory_mb = kwargs['memory_usage_mb']
        
        return metrics
    
    def complete_job_tracking(
        self,
        job_id: str,
        success: bool = True
    ) -> Optional[RenderMetrics]:
        """Complete tracking for a finished job."""
        if job_id not in self._job_metrics:
            return None
        
        metrics = self._job_metrics.pop(job_id)
        
        if success:
            self._total_jobs_completed += 1
            self._render_duration_histogram.append(metrics.total_duration_seconds)
        else:
            self._total_jobs_failed += 1
        
        self.logger.info(
            f"Completed tracking for job {job_id}: {'success' if success else 'failed'}, "
            f"duration: {metrics.total_duration_seconds:.2f}s"
        )
        
        return metrics
    
    def register_worker(self, worker_id: str) -> WorkerMetrics:
        """Register a new worker for tracking."""
        metrics = WorkerMetrics(worker_id=worker_id)
        self._worker_metrics[worker_id] = metrics
        self.logger.info(f"Registered worker {worker_id} for tracking")
        return metrics
    
    def update_worker_metrics(
        self,
        worker_id: str,
        **kwargs
    ) -> Optional[WorkerMetrics]:
        """Update metrics for a worker."""
        if worker_id not in self._worker_metrics:
            return None
        
        metrics = self._worker_metrics[worker_id]
        
        for key, value in kwargs.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)
        
        metrics.last_heartbeat = time.time()
        return metrics
    
    def record_worker_job_complete(
        self,
        worker_id: str,
        success: bool = True,
        job_duration: float = 0.0
    ) -> None:
        """Record that a worker completed a job."""
        if worker_id not in self._worker_metrics:
            return
        
        metrics = self._worker_metrics[worker_id]
        
        if success:
            metrics.jobs_processed += 1
        else:
            metrics.jobs_failed += 1
        
        # Update average job duration (simple moving average)
        n = metrics.jobs_processed + metrics.jobs_failed
        metrics.average_job_duration = (
            (metrics.average_job_duration * (n - 1) + job_duration) / n
        )
    
    def _record_queue_latency(self, latency_seconds: float) -> None:
        """Record queue latency for histogram."""
        self._queue_latency_histogram.append(latency_seconds)
        
        # Keep histogram size manageable
        if len(self._queue_latency_histogram) > 10000:
            self._queue_latency_histogram = self._queue_latency_histogram[-5000:]
    
    def _add_time_series_point(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Add a point to the time series."""
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            metric_type=metric_type,
            labels=labels or {}
        )
        
        self._time_series.append(point)
        
        # Trim old points
        if len(self._time_series) > self._time_series_max_size:
            self._time_series = self._time_series[-self._time_series_max_size:]
    
    def get_job_metrics(self, job_id: str) -> Optional[RenderMetrics]:
        """Get metrics for a specific job."""
        return self._job_metrics.get(job_id)
    
    def get_worker_metrics(self, worker_id: str) -> Optional[WorkerMetrics]:
        """Get metrics for a specific worker."""
        return self._worker_metrics.get(worker_id)
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get overview of system-wide metrics."""
        now = time.time()
        
        # Calculate active workers (heartbeat within last 60 seconds)
        active_workers = sum(
            1 for w in self._worker_metrics.values()
            if now - w.last_heartbeat < 60
        )
        
        # Calculate averages from histograms
        avg_render_duration = (
            sum(self._render_duration_histogram) / len(self._render_duration_histogram)
            if self._render_duration_histogram else 0.0
        )
        
        avg_queue_latency = (
            sum(self._queue_latency_histogram) / len(self._queue_latency_histogram)
            if self._queue_latency_histogram else 0.0
        )
        
        return {
            "totals": {
                "jobs_started": self._total_jobs_started,
                "jobs_completed": self._total_jobs_completed,
                "jobs_failed": self._total_jobs_failed,
                "success_rate": (
                    self._total_jobs_completed / self._total_jobs_started * 100
                    if self._total_jobs_started > 0 else 0.0
                ),
            },
            "workers": {
                "total_registered": len(self._worker_metrics),
                "active": active_workers,
            },
            "averages": {
                "render_duration_seconds": avg_render_duration,
                "queue_latency_seconds": avg_queue_latency,
            },
            "histograms": {
                "render_duration_samples": len(self._render_duration_histogram),
                "queue_latency_samples": len(self._queue_latency_histogram),
            }
        }
    
    def get_percentile(
        self,
        histogram: List[float],
        percentile: float
    ) -> float:
        """Calculate percentile from histogram data."""
        if not histogram:
            return 0.0
        
        sorted_data = sorted(histogram)
        index = int(len(sorted_data) * percentile / 100)
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]
    
    def get_render_duration_percentiles(self) -> Dict[str, float]:
        """Get render duration percentiles (p50, p90, p99)."""
        return {
            "p50": self.get_percentile(self._render_duration_histogram, 50),
            "p90": self.get_percentile(self._render_duration_histogram, 90),
            "p99": self.get_percentile(self._render_duration_histogram, 99),
        }
    
    def get_queue_latency_percentiles(self) -> Dict[str, float]:
        """Get queue latency percentiles."""
        return {
            "p50": self.get_percentile(self._queue_latency_histogram, 50),
            "p90": self.get_percentile(self._queue_latency_histogram, 90),
            "p99": self.get_percentile(self._queue_latency_histogram, 99),
        }
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics as dictionary."""
        return {
            "overview": self.get_system_overview(),
            "render_duration_percentiles": self.get_render_duration_percentiles(),
            "queue_latency_percentiles": self.get_queue_latency_percentiles(),
            "workers": {
                wid: w.to_dict() 
                for wid, w in self._worker_metrics.items()
            },
            "active_jobs": {
                jid: j.to_dict()
                for jid, j in self._job_metrics.items()
            }
        }
    
    def cleanup_stale_workers(self, max_idle_seconds: float = 300.0) -> int:
        """Remove workers that haven't sent heartbeat recently."""
        now = time.time()
        removed = 0
        
        stale_workers = [
            wid for wid, w in self._worker_metrics.items()
            if now - w.last_heartbeat > max_idle_seconds
        ]
        
        for wid in stale_workers:
            del self._worker_metrics[wid]
            removed += 1
            self.logger.info(f"Removed stale worker {wid}")
        
        return removed


# Singleton instance
_rendering_metrics: Optional[RenderingMetrics] = None


def get_rendering_metrics() -> RenderingMetrics:
    """Get or create the rendering metrics singleton."""
    global _rendering_metrics
    if _rendering_metrics is None:
        _rendering_metrics = RenderingMetrics()
    return _rendering_metrics
