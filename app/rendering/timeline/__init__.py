"""
Timeline Generation Engine

Converts Storyboard data into timeline structures for video rendering.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


class TrackType(str, Enum):
    """Types of tracks in a timeline."""
    VIDEO = "video"
    IMAGE = "image"
    VOICE = "voice"
    MUSIC = "music"
    SUBTITLE = "subtitle"


@dataclass
class TimelineElement:
    """Single element on a timeline track."""
    
    element_id: str
    track_type: TrackType
    start_time: float  # Seconds from timeline start
    duration: float  # Duration in seconds
    asset_key: str  # Storage key for the asset
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "track_type": self.track_type.value,
            "start_time": self.start_time,
            "duration": self.duration,
            "asset_key": self.asset_key,
            "properties": self.properties
        }


@dataclass
class TimelineTrack:
    """A single track containing multiple elements."""
    
    track_id: str
    track_type: TrackType
    elements: List[TimelineElement] = field(default_factory=list)
    
    def add_element(self, element: TimelineElement) -> None:
        self.elements.append(element)
        self.elements.sort(key=lambda e: e.start_time)
    
    def get_total_duration(self) -> float:
        if not self.elements:
            return 0.0
        last_element = max(self.elements, key=lambda e: e.start_time + e.duration)
        return last_element.start_time + last_element.duration
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "track_type": self.track_type.value,
            "elements": [e.to_dict() for e in self.elements],
            "total_duration": self.get_total_duration()
        }


@dataclass
class TimelineScene:
    """A scene within the timeline."""
    
    scene_id: str
    start_time: float
    duration: float
    storyboard_scene_id: Optional[int] = None  # Reference to original storyboard
    elements: List[TimelineElement] = field(default_factory=list)
    transitions: Dict[str, Any] = field(default_factory=dict)
    
    def add_element(self, element: TimelineElement) -> None:
        self.elements.append(element)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "start_time": self.start_time,
            "duration": self.duration,
            "storyboard_scene_id": self.storyboard_scene_id,
            "elements": [e.to_dict() for e in self.elements],
            "transitions": self.transitions
        }


@dataclass
class Timeline:
    """Complete timeline structure for video rendering."""
    
    timeline_id: str
    composition_id: Optional[int] = None
    organization_id: int = 0
    total_duration: float = 0.0
    resolution: str = "1920x1080"
    fps: float = 30.0
    tracks: List[TimelineTrack] = field(default_factory=list)
    scenes: List[TimelineScene] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_track(self, track: TimelineTrack) -> None:
        self.tracks.append(track)
    
    def add_scene(self, scene: TimelineScene) -> None:
        self.scenes.append(scene)
        self.scenes.sort(key=lambda s: s.start_time)
    
    def calculate_total_duration(self) -> float:
        """Calculate total timeline duration from all tracks."""
        if not self.tracks:
            return 0.0
        return max(track.get_total_duration() for track in self.tracks)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeline_id": self.timeline_id,
            "composition_id": self.composition_id,
            "organization_id": self.organization_id,
            "total_duration": self.total_duration,
            "resolution": self.resolution,
            "fps": self.fps,
            "tracks": [t.to_dict() for t in self.tracks],
            "scenes": [s.to_dict() for s in self.scenes],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class TimelineGenerator:
    """
    Generates timeline structures from storyboard and composition data.
    
    Responsibilities:
    - Convert Storyboard data into timeline structure
    - Create scenes
    - Calculate scene duration
    - Position assets on timeline
    - Synchronize voice narration
    - Place music tracks
    - Define transitions
    """
    
    def __init__(self, organization_id: int):
        self.organization_id = organization_id
    
    def generate_timeline(
        self,
        composition_data: Dict[str, Any],
        storyboard_data: Optional[Dict[str, Any]] = None
    ) -> Timeline:
        """
        Generate a complete timeline from composition and storyboard data.
        
        Args:
            composition_data: Video composition configuration
            storyboard_data: Optional storyboard reference data
            
        Returns:
            Generated Timeline object
        """
        import uuid
        
        timeline_id = str(uuid.uuid4())
        composition_id = composition_data.get("id")
        
        timeline = Timeline(
            timeline_id=timeline_id,
            composition_id=composition_id,
            organization_id=self.organization_id,
            resolution=composition_data.get("resolution", "1920x1080"),
            fps=composition_data.get("fps", 30.0)
        )
        
        # Create tracks for each type
        track_types = [
            TrackType.VIDEO,
            TrackType.IMAGE,
            TrackType.VOICE,
            TrackType.MUSIC,
            TrackType.SUBTITLE
        ]
        
        for track_type in track_types:
            track = TimelineTrack(
                track_id=f"track_{track_type.value}",
                track_type=track_type
            )
            timeline.add_track(track)
        
        # Process clips and create scenes
        clips = composition_data.get("clips", [])
        current_time = 0.0
        
        for idx, clip in enumerate(clips):
            scene = self._create_scene_from_clip(
                clip=clip,
                scene_index=idx,
                start_time=current_time,
                storyboard_data=storyboard_data
            )
            timeline.add_scene(scene)
            
            # Add elements to appropriate tracks
            self._add_clip_elements_to_tracks(
                clip=clip,
                timeline=timeline,
                start_time=current_time
            )
            
            current_time += scene.duration
        
        # Process audio tracks
        audio_tracks = composition_data.get("audio_tracks", [])
        self._add_audio_tracks(timeline, audio_tracks)
        
        # Process subtitles
        subtitles = composition_data.get("subtitles", [])
        self._add_subtitles(timeline, subtitles)
        
        # Calculate final duration
        timeline.total_duration = timeline.calculate_total_duration()
        
        return timeline
    
    def _create_scene_from_clip(
        self,
        clip: Dict[str, Any],
        scene_index: int,
        start_time: float,
        storyboard_data: Optional[Dict[str, Any]] = None
    ) -> TimelineScene:
        """Create a timeline scene from a clip definition."""
        import uuid
        
        scene_id = str(uuid.uuid4())
        duration = clip.get("duration", 5.0)
        storyboard_scene_id = clip.get("storyboard_scene_id")
        
        scene = TimelineScene(
            scene_id=scene_id,
            start_time=start_time,
            duration=duration,
            storyboard_scene_id=storyboard_scene_id
        )
        
        # Add transition info if present
        if "transition" in clip:
            scene.transitions = clip["transition"]
        
        return scene
    
    def _add_clip_elements_to_tracks(
        self,
        clip: Dict[str, Any],
        timeline: Timeline,
        start_time: float
    ) -> None:
        """Add clip elements to appropriate timeline tracks."""
        import uuid
        
        asset_key = clip.get("asset_key", "")
        asset_type = clip.get("type", "video")
        duration = clip.get("duration", 5.0)
        
        # Determine track type
        if asset_type in ["video", "image"]:
            track_type = TrackType.VIDEO if asset_type == "video" else TrackType.IMAGE
        else:
            track_type = TrackType.VIDEO
        
        # Find appropriate track
        target_track = next(
            (t for t in timeline.tracks if t.track_type == track_type),
            None
        )
        
        if target_track and asset_key:
            element = TimelineElement(
                element_id=str(uuid.uuid4()),
                track_type=track_type,
                start_time=start_time,
                duration=duration,
                asset_key=asset_key,
                properties={
                    "effects": clip.get("effects", []),
                    "transform": clip.get("transform", {})
                }
            )
            target_track.add_element(element)
    
    def _add_audio_tracks(
        self,
        timeline: Timeline,
        audio_tracks: List[Dict[str, Any]]
    ) -> None:
        """Add audio tracks to timeline."""
        import uuid
        
        voice_track = next(
            (t for t in timeline.tracks if t.track_type == TrackType.VOICE),
            None
        )
        music_track = next(
            (t for t in timeline.tracks if t.track_type == TrackType.MUSIC),
            None
        )
        
        for audio in audio_tracks:
            audio_type = audio.get("type", "music")
            asset_key = audio.get("asset_key", "")
            start_time = audio.get("start_time", 0.0)
            duration = audio.get("duration", 0.0)
            
            if audio_type == "voice" and voice_track:
                element = TimelineElement(
                    element_id=str(uuid.uuid4()),
                    track_type=TrackType.VOICE,
                    start_time=start_time,
                    duration=duration,
                    asset_key=asset_key,
                    properties={"volume": audio.get("volume", 1.0)}
                )
                voice_track.add_element(element)
            elif audio_type == "music" and music_track:
                element = TimelineElement(
                    element_id=str(uuid.uuid4()),
                    track_type=TrackType.MUSIC,
                    start_time=start_time,
                    duration=duration,
                    asset_key=asset_key,
                    properties={"volume": audio.get("volume", 0.5)}
                )
                music_track.add_element(element)
    
    def _add_subtitles(
        self,
        timeline: Timeline,
        subtitles: List[Dict[str, Any]]
    ) -> None:
        """Add subtitle elements to timeline."""
        import uuid
        
        subtitle_track = next(
            (t for t in timeline.tracks if t.track_type == TrackType.SUBTITLE),
            None
        )
        
        if not subtitle_track:
            return
        
        for sub in subtitles:
            start_time = sub.get("start_time", 0.0)
            duration = sub.get("duration", 2.0)
            text = sub.get("text", "")
            language = sub.get("language", "en")
            
            element = TimelineElement(
                element_id=str(uuid.uuid4()),
                track_type=TrackType.SUBTITLE,
                start_time=start_time,
                duration=duration,
                asset_key="",  # Subtitles are text-based
                properties={
                    "text": text,
                    "language": language,
                    "style": sub.get("style", {})
                }
            )
            subtitle_track.add_element(element)


__all__ = [
    "TrackType",
    "TimelineElement",
    "TimelineTrack",
    "TimelineScene",
    "Timeline",
    "TimelineGenerator",
]
