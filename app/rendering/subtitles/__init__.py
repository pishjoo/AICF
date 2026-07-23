"""
Subtitle Generation System

Generates SRT and VTT subtitle files from script data.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import timedelta


class SubtitleFormat(str, Enum):
    """Supported subtitle formats."""
    SRT = "srt"
    VTT = "vtt"


@dataclass
class SubtitleCue:
    """A single subtitle cue with timing and text."""
    
    cue_id: int
    start_time: float  # Seconds
    end_time: float  # Seconds
    text: str
    language: str = "en"
    style: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "language": self.language,
            "style": self.style
        }


@dataclass
class SubtitleTrack:
    """A complete subtitle track with multiple cues."""
    
    track_id: str
    language: str = "en"
    cues: List[SubtitleCue] = field(default_factory=list)
    title: Optional[str] = None
    
    def add_cue(
        self,
        start_time: float,
        end_time: float,
        text: str,
        style: Optional[Dict[str, Any]] = None
    ) -> SubtitleCue:
        """Add a subtitle cue to the track."""
        cue = SubtitleCue(
            cue_id=len(self.cues) + 1,
            start_time=start_time,
            end_time=end_time,
            text=text,
            language=self.language,
            style=style or {}
        )
        self.cues.append(cue)
        return cue
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "language": self.language,
            "cues": [c.to_dict() for c in self.cues],
            "title": self.title
        }


class SubtitleGenerator:
    """
    Generates subtitle files from script data.
    
    Support:
    - SRT output
    - VTT output
    - Generate subtitles from script
    - Timestamp alignment
    - Scene-based subtitle grouping
    - Language support
    """
    
    def __init__(self, default_language: str = "en"):
        self.default_language = default_language
        self.logger = logging.getLogger("rendering.subtitles")
    
    def generate_from_script(
        self,
        script_lines: List[Dict[str, Any]],
        scene_timings: Optional[List[Dict[str, float]]] = None,
        language: Optional[str] = None
    ) -> SubtitleTrack:
        """
        Generate subtitles from script lines.
        
        Args:
            script_lines: List of script lines with text and optional timing
            scene_timings: Optional scene timing data for alignment
            language: Language code (defaults to instance default)
            
        Returns:
            Generated SubtitleTrack
        """
        import uuid
        
        lang = language or self.default_language
        track = SubtitleTrack(
            track_id=str(uuid.uuid4()),
            language=lang
        )
        
        current_time = 0.0
        default_duration = 2.0  # Default subtitle display duration
        
        for idx, line in enumerate(script_lines):
            text = line.get("text", "").strip()
            if not text:
                continue
            
            # Get timing from script or calculate
            start_time = line.get("start_time", current_time)
            end_time = line.get("end_time", start_time + default_duration)
            
            # If scene timings provided, align to scenes
            if scene_timings:
                start_time, end_time = self._align_to_scenes(
                    start_time, end_time, scene_timings
                )
            
            style = line.get("style", {})
            track.add_cue(
                start_time=start_time,
                end_time=end_time,
                text=text,
                style=style
            )
            
            current_time = end_time
        
        self.logger.info(
            f"Generated {len(track.cues)} subtitle cues in {lang}"
        )
        return track
    
    def _align_to_scenes(
        self,
        start_time: float,
        end_time: float,
        scene_timings: List[Dict[str, float]]
    ) -> tuple[float, float]:
        """Align subtitle timing to scene boundaries."""
        # Find which scene contains the start time
        for scene in scene_timings:
            scene_start = scene.get("start_time", 0.0)
            scene_end = scene_start + scene.get("duration", 0.0)
            
            # Adjust start to be within scene
            if scene_start <= start_time < scene_end:
                # Keep start as is but ensure end doesn't exceed scene
                end_time = min(end_time, scene_end)
                break
        
        return start_time, end_time
    
    def export_srt(self, track: SubtitleTrack) -> str:
        """
        Export subtitle track to SRT format.
        
        Args:
            track: SubtitleTrack to export
            
        Returns:
            SRT formatted string
        """
        lines = []
        
        for cue in track.cues:
            # Cue number
            lines.append(str(cue.cue_id))
            
            # Timing line: HH:MM:SS,mmm --> HH:MM:SS,mmm
            start_str = self._format_time_srt(cue.start_time)
            end_str = self._format_time_srt(cue.end_time)
            lines.append(f"{start_str} --> {end_str}")
            
            # Text
            lines.append(cue.text)
            lines.append("")  # Blank line between cues
        
        return "\n".join(lines)
    
    def export_vtt(self, track: SubtitleTrack) -> str:
        """
        Export subtitle track to WebVTT format.
        
        Args:
            track: SubtitleTrack to export
            
        Returns:
            VTT formatted string
        """
        lines = ["WEBVTT", f"Language: {track.language}", ""]
        
        if track.title:
            lines.insert(2, f"Title: {track.title}")
            lines.insert(3, "")
        
        for cue in track.cues:
            # Timing line: HH:MM:SS.mmm --> HH:MM:SS.mmm
            start_str = self._format_time_vtt(cue.start_time)
            end_str = self._format_time_vtt(cue.end_time)
            lines.append(f"{start_str} --> {end_str}")
            
            # Add style if present
            if cue.style:
                style_str = " ".join(f"{k}:{v}" for k, v in cue.style.items())
                lines[-1] += f" {style_str}"
            
            # Text
            lines.append(cue.text)
            lines.append("")  # Blank line between cues
        
        return "\n".join(lines)
    
    def _format_time_srt(self, seconds: float) -> str:
        """Format time in SRT format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_time_vtt(self, seconds: float) -> str:
        """Format time in VTT format (HH:MM:SS.mmm)."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def group_by_scene(
        self,
        track: SubtitleTrack,
        scene_timings: List[Dict[str, float]]
    ) -> List[Dict[str, Any]]:
        """
        Group subtitle cues by scene.
        
        Args:
            track: SubtitleTrack to group
            scene_timings: List of scene timing definitions
            
        Returns:
            List of scene groups with their cues
        """
        groups = []
        
        for idx, scene in enumerate(scene_timings):
            scene_start = scene.get("start_time", 0.0)
            scene_duration = scene.get("duration", 0.0)
            scene_end = scene_start + scene_duration
            
            # Find cues that overlap with this scene
            scene_cues = []
            for cue in track.cues:
                cue_end = cue.start_time + (cue.end_time - cue.start_time)
                if cue.start_time < scene_end and cue_end > scene_start:
                    scene_cues.append(cue.to_dict())
            
            groups.append({
                "scene_index": idx,
                "scene_start": scene_start,
                "scene_duration": scene_duration,
                "cue_count": len(scene_cues),
                "cues": scene_cues
            })
        
        return groups


__all__ = [
    "SubtitleFormat",
    "SubtitleCue",
    "SubtitleTrack",
    "SubtitleGenerator",
]
