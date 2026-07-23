"""
Rendering Pipeline Orchestrator

Orchestrates the complete video rendering workflow from job to output.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.rendering.timeline import TimelineGenerator, Timeline
from app.rendering.composition import SceneComposer, ComposedScene
from app.rendering.audio import AudioSynchronizer, SynchronizedAudio
from app.rendering.subtitles import SubtitleGenerator, SubtitleTrack
from app.rendering.thumbnail import ThumbnailGenerator
from app.rendering.export import VideoExporter, ExportProfile, ExportResult
from app.rendering.ffmpeg import FFmpegExecutor, SubprocessFFmpegExecutor


class PipelineStage(str, Enum):
    """Stages in the rendering pipeline."""
    VALIDATE_ASSETS = "validate_assets"
    GENERATE_TIMELINE = "generate_timeline"
    COMPOSE_SCENES = "compose_scenes"
    SYNCHRONIZE_AUDIO = "synchronize_audio"
    GENERATE_SUBTITLES = "generate_subtitles"
    EXECUTE_FFMPEG = "execute_ffmpeg"
    GENERATE_THUMBNAIL = "generate_thumbnail"
    STORE_OUTPUT = "store_output"
    QUALITY_EVALUATION = "quality_evaluation"
    APPROVAL_WORKFLOW = "approval_workflow"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineContext:
    """Context data passed through pipeline stages."""
    
    job_id: int
    organization_id: int
    composition_data: Dict[str, Any]
    storyboard_data: Optional[Dict[str, Any]] = None
    timeline: Optional[Timeline] = None
    composed_scenes: List[ComposedScene] = field(default_factory=list)
    synchronized_audio: Optional[SynchronizedAudio] = None
    subtitle_track: Optional[SubtitleTrack] = None
    ffmpeg_result: Optional[Dict[str, Any]] = None
    thumbnail_result: Optional[Dict[str, Any]] = None
    export_results: List[ExportResult] = field(default_factory=list)
    current_stage: PipelineStage = PipelineStage.VALIDATE_ASSETS
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "organization_id": self.organization_id,
            "current_stage": self.current_stage.value,
            "has_timeline": self.timeline is not None,
            "scene_count": len(self.composed_scenes),
            "has_audio": self.synchronized_audio is not None,
            "has_subtitles": self.subtitle_track is not None,
            "export_count": len(self.export_results),
            "errors": self.errors,
            "warnings": self.warnings,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class RenderingPipeline:
    """
    Orchestrates the complete video rendering workflow.
    
    Flow:
    RenderingJob
        |
        v
    Validate Assets
        |
        v
    Generate Timeline
        |
        v
    Compose Scenes
        |
        v
    Synchronize Audio
        |
        v
    Generate Subtitles
        |
        v
    Execute FFmpeg Render
        |
        v
    Generate Thumbnail
        |
        v
    Store Output
        |
        v
    Quality Evaluation
        |
        v
    Approval Workflow
    """
    
    def __init__(
        self,
        ffmpeg_executor: Optional[FFmpegExecutor] = None,
        storage_service: Optional[Any] = None
    ):
        self.ffmpeg_executor = ffmpeg_executor or SubprocessFFmpegExecutor()
        self.storage_service = storage_service
        self.logger = logging.getLogger("rendering.pipeline")
        
        # Initialize component engines
        self.timeline_generator: Optional[TimelineGenerator] = None
        self.scene_composer: Optional[SceneComposer] = None
        self.audio_synchronizer: Optional[AudioSynchronizer] = None
        self.subtitle_generator: Optional[SubtitleGenerator] = None
        self.thumbnail_generator: Optional[ThumbnailGenerator] = None
        self.video_exporter: Optional[VideoExporter] = None
    
    def execute(
        self,
        context: PipelineContext,
        progress_callback: Optional[callable] = None
    ) -> PipelineContext:
        """
        Execute the complete rendering pipeline.
        
        Args:
            context: Pipeline context with job data
            progress_callback: Optional callback for progress updates
            
        Returns:
            Updated PipelineContext with results
        """
        self.logger.info(f"Starting rendering pipeline for job {context.job_id}")
        
        try:
            # Initialize components with organization context
            self._initialize_components(context.organization_id)
            
            # Stage 1: Validate Assets
            context = self._stage_validate_assets(context)
            self._report_progress(context, progress_callback, 10)
            
            # Stage 2: Generate Timeline
            context = self._stage_generate_timeline(context)
            self._report_progress(context, progress_callback, 20)
            
            # Stage 3: Compose Scenes
            context = self._stage_compose_scenes(context)
            self._report_progress(context, progress_callback, 35)
            
            # Stage 4: Synchronize Audio
            context = self._stage_synchronize_audio(context)
            self._report_progress(context, progress_callback, 50)
            
            # Stage 5: Generate Subtitles
            context = self._stage_generate_subtitles(context)
            self._report_progress(context, progress_callback, 60)
            
            # Stage 6: Execute FFmpeg Render
            context = self._stage_execute_ffmpeg(context)
            self._report_progress(context, progress_callback, 80)
            
            # Stage 7: Generate Thumbnail
            context = self._stage_generate_thumbnail(context)
            self._report_progress(context, progress_callback, 90)
            
            # Stage 8: Store Output
            context = self._stage_store_output(context)
            self._report_progress(context, progress_callback, 95)
            
            # Stage 9: Quality Evaluation
            context = self._stage_quality_evaluation(context)
            
            # Stage 10: Approval Workflow
            context = self._stage_approval_workflow(context)
            
            # Mark completed
            context.current_stage = PipelineStage.COMPLETED
            context.completed_at = datetime.now(timezone.utc)
            
            self.logger.info(
                f"Rendering pipeline completed for job {context.job_id} "
                f"in {len(context.composed_scenes)} scenes"
            )
            
        except Exception as e:
            self.logger.exception(f"Pipeline failed for job {context.job_id}: {e}")
            context.current_stage = PipelineStage.FAILED
            context.errors.append(str(e))
            context.completed_at = datetime.now(timezone.utc)
        
        return context
    
    def _initialize_components(self, organization_id: int) -> None:
        """Initialize pipeline components."""
        self.timeline_generator = TimelineGenerator(organization_id)
        self.scene_composer = SceneComposer()
        self.audio_synchronizer = AudioSynchronizer()
        self.subtitle_generator = SubtitleGenerator()
        self.thumbnail_generator = ThumbnailGenerator()
        self.video_exporter = VideoExporter()
    
    def _stage_validate_assets(self, context: PipelineContext) -> PipelineContext:
        """Validate all input assets exist and are accessible."""
        context.current_stage = PipelineStage.VALIDATE_ASSETS
        self.logger.debug(f"Validating assets for job {context.job_id}")
        
        # Validate composition data exists
        if not context.composition_data:
            context.errors.append("No composition data provided")
            return context
        
        # Validate clips have asset keys
        clips = context.composition_data.get("clips", [])
        for idx, clip in enumerate(clips):
            if not clip.get("asset_key"):
                context.errors.append(f"Clip {idx} missing asset_key")
        
        # In full implementation, would verify assets exist in storage
        if context.errors:
            self.logger.warning(f"Asset validation failed: {context.errors}")
        
        return context
    
    def _stage_generate_timeline(self, context: PipelineContext) -> PipelineContext:
        """Generate timeline from composition data."""
        context.current_stage = PipelineStage.GENERATE_TIMELINE
        self.logger.debug(f"Generating timeline for job {context.job_id}")
        
        if context.timeline_generator and not context.errors:
            context.timeline = self.timeline_generator.generate_timeline(
                composition_data=context.composition_data,
                storyboard_data=context.storyboard_data
            )
            self.logger.debug(
                f"Generated timeline with {len(context.timeline.tracks)} tracks, "
                f"{len(context.timeline.scenes)} scenes"
            )
        
        return context
    
    def _stage_compose_scenes(self, context: PipelineContext) -> PipelineContext:
        """Compose individual scenes with effects and transitions."""
        context.current_stage = PipelineStage.COMPOSE_SCENES
        self.logger.debug(f"Composing scenes for job {context.job_id}")
        
        if context.timeline and context.scene_composer and not context.errors:
            clips = context.composition_data.get("clips", [])
            
            for idx, (clip, scene) in enumerate(zip(clips, context.timeline.scenes)):
                asset_key = clip.get("asset_key", "")
                composed = self.scene_composer.compose_scene(
                    scene_data={
                        "scene_id": scene.scene_id,
                        "duration": scene.duration,
                        "resolution": context.timeline.resolution,
                        "camera_movement": clip.get("camera_movement"),
                        "effects": clip.get("effects", []),
                        "transition_in": clip.get("transition_in"),
                        "transition_out": clip.get("transition_out"),
                        "overlays": clip.get("overlays", [])
                    },
                    asset_key=asset_key
                )
                context.composed_scenes.append(composed)
        
        return context
    
    def _stage_synchronize_audio(self, context: PipelineContext) -> PipelineContext:
        """Synchronize audio tracks with video."""
        context.current_stage = PipelineStage.SYNCHRONIZE_AUDIO
        self.logger.debug(f"Synchronizing audio for job {context.job_id}")
        
        if context.timeline and context.audio_synchronizer and not context.errors:
            voice_tracks = context.composition_data.get("audio_tracks", [])
            music_tracks = [t for t in voice_tracks if t.get("type") == "music"]
            voice_only = [t for t in voice_tracks if t.get("type") == "voice"]
            
            context.synchronized_audio = self.audio_synchronizer.synchronize(
                voice_tracks=voice_only,
                music_tracks=music_tracks,
                video_duration=context.timeline.total_duration
            )
        
        return context
    
    def _stage_generate_subtitles(self, context: PipelineContext) -> PipelineContext:
        """Generate subtitle files."""
        context.current_stage = PipelineStage.GENERATE_SUBTITLES
        self.logger.debug(f"Generating subtitles for job {context.job_id}")
        
        if context.subtitle_generator and not context.errors:
            subtitles_data = context.composition_data.get("subtitles", [])
            
            if subtitles_data:
                script_lines = [
                    {"text": sub.get("text", ""), "start_time": sub.get("start_time")}
                    for sub in subtitles_data
                ]
                
                context.subtitle_track = self.subtitle_generator.generate_from_script(
                    script_lines=script_lines
                )
        
        return context
    
    def _stage_execute_ffmpeg(self, context: PipelineContext) -> PipelineContext:
        """Execute FFmpeg rendering command."""
        context.current_stage = PipelineStage.EXECUTE_FFMPEG
        self.logger.debug(f"Executing FFmpeg render for job {context.job_id}")
        
        if not context.errors and context.composed_scenes:
            # Generate filter graph from composed scenes
            if context.scene_composer and context.timeline:
                filter_graph = self.scene_composer.generate_filter_graph(
                    scenes=context.composed_scenes,
                    output_resolution=context.timeline.resolution
                )
                
                # In full implementation, would execute FFmpeg here
                context.ffmpeg_result = {
                    "filter_graph": filter_graph,
                    "status": "simulated",
                    "message": "FFmpeg execution would occur here"
                }
                self.logger.debug(f"Generated filter graph: {filter_graph[:100]}...")
        
        return context
    
    def _stage_generate_thumbnail(self, context: PipelineContext) -> PipelineContext:
        """Generate video thumbnail."""
        context.current_stage = PipelineStage.GENERATE_THUMBNAIL
        self.logger.debug(f"Generating thumbnail for job {context.job_id}")
        
        if context.thumbnail_generator and context.timeline and not context.errors:
            candidate = self.thumbnail_generator.select_best_frame(
                video_duration=context.timeline.total_duration
            )
            
            context.thumbnail_result = {
                "selected_timestamp": candidate.timestamp,
                "frame_index": candidate.frame_index
            }
        
        return context
    
    def _stage_store_output(self, context: PipelineContext) -> PipelineContext:
        """Store rendered outputs to storage."""
        context.current_stage = PipelineStage.STORE_OUTPUT
        self.logger.debug(f"Storing outputs for job {context.job_id}")
        
        # In full implementation, would upload files to storage
        if context.timeline:
            # Create export result placeholder
            pass
        
        return context
    
    def _stage_quality_evaluation(self, context: PipelineContext) -> PipelineContext:
        """Evaluate output quality."""
        context.current_stage = PipelineStage.QUALITY_EVALUATION
        self.logger.debug(f"Evaluating quality for job {context.job_id}")
        
        # Placeholder for quality checks
        # Would verify:
        # - Video codec/format
        # - Audio sync
        # - Resolution matches target
        # - No encoding artifacts
        
        return context
    
    def _stage_approval_workflow(self, context: PipelineContext) -> PipelineContext:
        """Trigger approval workflow if configured."""
        context.current_stage = PipelineStage.APPROVAL_WORKFLOW
        self.logger.debug(f"Processing approval for job {context.job_id}")
        
        # In full implementation, would trigger approval workflow
        # based on organization settings
        
        return context
    
    def _report_progress(
        self,
        context: PipelineContext,
        callback: Optional[callable],
        percentage: int
    ) -> None:
        """Report progress via callback if provided."""
        if callback:
            try:
                callback(job_id=context.job_id, progress=percentage)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")


__all__ = [
    "PipelineStage",
    "PipelineContext",
    "RenderingPipeline",
]
