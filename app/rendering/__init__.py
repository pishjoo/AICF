"""
Rendering Module

Video rendering infrastructure for AICF v2.

This module provides:
- Rendering job management
- Background queue system
- Worker processing
- FFmpeg integration
- Storage extensions for video assets
- Timeline generation engine
- Scene composition engine
- Audio synchronization
- Subtitle generation
- Thumbnail generation
- Multi-format export
- Complete rendering pipeline
"""

from app.rendering.queue import (
    RenderingQueue,
    RenderingQueueMessage,
    RenderingQueueStatus,
    InMemoryRenderingQueue,
    RedisRenderingQueue,
)

from app.rendering.worker import (
    RenderingWorker,
    RenderingTaskDefinition,
)

from app.rendering.ffmpeg import (
    FFmpegExecutor,
    SubprocessFFmpegExecutor,
    MediaMetadata,
    FFmpegExecutionResult,
)

from app.rendering.timeline import (
    TrackType,
    TimelineElement,
    TimelineTrack,
    TimelineScene,
    Timeline,
    TimelineGenerator,
)

from app.rendering.composition import (
    TransitionType,
    EffectType,
    CameraMovement,
    VideoEffect,
    SceneTransition,
    ComposedScene,
    SceneComposer,
)

from app.rendering.audio import (
    AudioTrackType,
    AudioSegment,
    AudioMixConfig,
    SynchronizedAudio,
    AudioSynchronizer,
)

from app.rendering.subtitles import (
    SubtitleFormat,
    SubtitleCue,
    SubtitleTrack,
    SubtitleGenerator,
)

from app.rendering.thumbnail import (
    ThumbnailSelectionMethod,
    ThumbnailCandidate,
    GeneratedThumbnail,
    ThumbnailGenerator,
)

from app.rendering.export import (
    VideoFormat,
    ExportProfile,
    ExportProfileConfig,
    EXPORT_PROFILES,
    ExportResult,
    VideoExporter,
)

from app.rendering.pipeline import (
    PipelineStage,
    PipelineContext,
    RenderingPipeline,
)

from app.rendering.storage_extensions import RenderingStorageService

from app.rendering.permissions import (
    RENDER_PERMISSIONS,
    get_rendering_permissions,
    get_rendering_permission_slugs,
    create_rendering_permissions_data,
    get_role_rendering_permissions,
)

__all__ = [
    # Queue
    "RenderingQueue",
    "RenderingQueueMessage",
    "RenderingQueueStatus",
    "InMemoryRenderingQueue",
    "RedisRenderingQueue",
    # Worker
    "RenderingWorker",
    "RenderingTaskDefinition",
    # FFmpeg
    "FFmpegExecutor",
    "SubprocessFFmpegExecutor",
    "MediaMetadata",
    "FFmpegExecutionResult",
    # Timeline
    "TrackType",
    "TimelineElement",
    "TimelineTrack",
    "TimelineScene",
    "Timeline",
    "TimelineGenerator",
    # Composition
    "TransitionType",
    "EffectType",
    "CameraMovement",
    "VideoEffect",
    "SceneTransition",
    "ComposedScene",
    "SceneComposer",
    # Audio
    "AudioTrackType",
    "AudioSegment",
    "AudioMixConfig",
    "SynchronizedAudio",
    "AudioSynchronizer",
    # Subtitles
    "SubtitleFormat",
    "SubtitleCue",
    "SubtitleTrack",
    "SubtitleGenerator",
    # Thumbnail
    "ThumbnailSelectionMethod",
    "ThumbnailCandidate",
    "GeneratedThumbnail",
    "ThumbnailGenerator",
    # Export
    "VideoFormat",
    "ExportProfile",
    "ExportProfileConfig",
    "EXPORT_PROFILES",
    "ExportResult",
    "VideoExporter",
    # Pipeline
    "PipelineStage",
    "PipelineContext",
    "RenderingPipeline",
    # Storage
    "RenderingStorageService",
    # Permissions
    "RENDER_PERMISSIONS",
    "get_rendering_permissions",
    "get_rendering_permission_slugs",
    "create_rendering_permissions_data",
    "get_role_rendering_permissions",
]
