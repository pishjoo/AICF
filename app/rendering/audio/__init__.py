"""
Audio Synchronization Engine

Handles voice narration synchronization, music mixing, and audio ducking.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class AudioTrackType(str, Enum):
    """Types of audio tracks."""
    VOICE = "voice"
    MUSIC = "music"
    SFX = "sfx"
    AMBIENCE = "ambience"


@dataclass
class AudioSegment:
    """A segment of audio with timing information."""
    
    segment_id: str
    asset_key: str
    track_type: AudioTrackType
    start_time: float  # Seconds from timeline start
    duration: float
    volume: float = 1.0  # Normalized 0-1
    fade_in: float = 0.0  # Fade in duration in seconds
    fade_out: float = 0.0  # Fade out duration in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "asset_key": self.asset_key,
            "track_type": self.track_type.value,
            "start_time": self.start_time,
            "duration": self.duration,
            "volume": self.volume,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out
        }


@dataclass
class AudioMixConfig:
    """Configuration for audio mixing."""
    
    voice_priority: float = 1.0  # Voice volume priority
    music_ducking_level: float = 0.3  # Music reduction when voice present
    music_base_volume: float = 0.5  # Base music volume
    normalize_target: float = -16.0  # LUFS target for normalization
    crossfade_duration: float = 2.0  # Crossfade between music segments
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_priority": self.voice_priority,
            "music_ducking_level": self.music_ducking_level,
            "music_base_volume": self.music_base_volume,
            "normalize_target": self.normalize_target,
            "crossfade_duration": self.crossfade_duration
        }


@dataclass
class SynchronizedAudio:
    """Result of audio synchronization."""
    
    voice_segments: List[AudioSegment] = field(default_factory=list)
    music_segments: List[AudioSegment] = field(default_factory=list)
    sfx_segments: List[AudioSegment] = field(default_factory=list)
    mix_config: AudioMixConfig = field(default_factory=AudioMixConfig)
    total_duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_segments": [s.to_dict() for s in self.voice_segments],
            "music_segments": [s.to_dict() for s in self.music_segments],
            "sfx_segments": [s.to_dict() for s in self.sfx_segments],
            "mix_config": self.mix_config.to_dict(),
            "total_duration": self.total_duration
        }


class AudioSynchronizer:
    """
    Synchronizes audio tracks with video timeline.
    
    Responsibilities:
    - Match voice duration with scenes
    - Normalize volume
    - Mix narration + background music
    - Apply ducking (voice priority over music)
    """
    
    def __init__(self, mix_config: Optional[AudioMixConfig] = None):
        self.mix_config = mix_config or AudioMixConfig()
        self.logger = logging.getLogger("rendering.audio")
    
    def synchronize(
        self,
        voice_tracks: List[Dict[str, Any]],
        music_tracks: List[Dict[str, Any]],
        video_duration: float,
        scene_timings: Optional[List[Dict[str, float]]] = None
    ) -> SynchronizedAudio:
        """
        Synchronize audio tracks with video timeline.
        
        Args:
            voice_tracks: List of voice narration track definitions
            music_tracks: List of background music track definitions
            video_duration: Total video duration in seconds
            scene_timings: Optional list of scene start/end times
            
        Returns:
            SynchronizedAudio configuration
        """
        import uuid
        
        result = SynchronizedAudio(
            mix_config=self.mix_config,
            total_duration=video_duration
        )
        
        # Process voice tracks
        for idx, voice_data in enumerate(voice_tracks):
            segment = AudioSegment(
                segment_id=str(uuid.uuid4()),
                asset_key=voice_data.get("asset_key", ""),
                track_type=AudioTrackType.VOICE,
                start_time=voice_data.get("start_time", 0.0),
                duration=voice_data.get("duration", 0.0),
                volume=voice_data.get("volume", self.mix_config.voice_priority),
                fade_in=voice_data.get("fade_in", 0.1),
                fade_out=voice_data.get("fade_out", 0.1)
            )
            result.voice_segments.append(segment)
        
        # Process music tracks with ducking
        music_segments = self._process_music_with_ducking(
            music_tracks=music_tracks,
            voice_segments=result.voice_segments,
            video_duration=video_duration
        )
        result.music_segments = music_segments
        
        # Calculate actual total duration
        if result.voice_segments or result.music_segments:
            all_segments = result.voice_segments + result.music_segments
            max_end = max(s.start_time + s.duration for s in all_segments)
            result.total_duration = max(max_end, video_duration)
        
        return result
    
    def _process_music_with_ducking(
        self,
        music_tracks: List[Dict[str, Any]],
        voice_segments: List[AudioSegment],
        video_duration: float
    ) -> List[AudioSegment]:
        """
        Process music tracks applying ducking when voice is present.
        
        Ducking reduces music volume when voice narration is active.
        """
        import uuid
        
        music_segments = []
        
        for music_data in music_tracks:
            base_volume = music_data.get(
                "volume",
                self.mix_config.music_base_volume
            )
            
            # Create base music segment
            segment = AudioSegment(
                segment_id=str(uuid.uuid4()),
                asset_key=music_data.get("asset_key", ""),
                track_type=AudioTrackType.MUSIC,
                start_time=music_data.get("start_time", 0.0),
                duration=music_data.get("duration", video_duration),
                volume=base_volume,
                fade_in=music_data.get("fade_in", self.mix_config.crossfade_duration),
                fade_out=music_data.get("fade_out", self.mix_config.crossfade_duration)
            )
            
            # Apply ducking based on voice segments
            ducked_segment = self._apply_ducking(
                music_segment=segment,
                voice_segments=voice_segments
            )
            music_segments.append(ducked_segment)
        
        return music_segments
    
    def _apply_ducking(
        self,
        music_segment: AudioSegment,
        voice_segments: List[AudioSegment]
    ) -> AudioSegment:
        """
        Apply volume ducking to music when voice is present.
        
        Returns a new segment with adjusted volume envelope.
        """
        # For simplicity, we adjust the base volume
        # A full implementation would create volume envelope points
        
        music_start = music_segment.start_time
        music_end = music_start + music_segment.duration
        
        # Check for overlap with voice segments
        has_voice_overlap = False
        for voice in voice_segments:
            voice_start = voice.start_time
            voice_end = voice_start + voice.duration
            
            # Check for overlap
            if music_start < voice_end and music_end > voice_start:
                has_voice_overlap = True
                break
        
        if has_voice_overlap:
            # Reduce music volume during voice sections
            ducked_volume = music_segment.volume * self.mix_config.music_ducking_level
            self.logger.debug(
                f"Applied ducking to music segment {music_segment.segment_id}: "
                f"{music_segment.volume} -> {ducked_volume}"
            )
            # Return new segment with reduced volume
            return AudioSegment(
                segment_id=music_segment.segment_id,
                asset_key=music_segment.asset_key,
                track_type=music_segment.track_type,
                start_time=music_segment.start_time,
                duration=music_segment.duration,
                volume=ducked_volume,
                fade_in=music_segment.fade_in,
                fade_out=music_segment.fade_out
            )
        
        return music_segment
    
    def generate_audio_filter(
        self,
        synchronized: SynchronizedAudio
    ) -> str:
        """
        Generate FFmpeg audio filter complex string.
        
        Args:
            synchronized: Synchronized audio configuration
            
        Returns:
            FFmpeg audio filter string
        """
        filters = []
        inputs = []
        
        # Process voice tracks
        voice_inputs = []
        for idx, segment in enumerate(synchronized.voice_segments):
            input_label = f"[{idx}:a]"
            voice_inputs.append(input_label)
            
            # Add volume and fade filters
            filter_parts = []
            if segment.volume != 1.0:
                filter_parts.append(f"volume={segment.volume}")
            if segment.fade_in > 0:
                filter_parts.append(
                    f"afade=t=in:st={segment.start_time}:d={segment.fade_in}"
                )
            if segment.fade_out > 0:
                fade_start = segment.start_time + segment.duration - segment.fade_out
                filter_parts.append(
                    f"afade=t=out:st={fade_start}:d={segment.fade_out}"
                )
            
            if filter_parts:
                filters.append(f"{input_label},{','.join(filter_parts)}[v{idx}]")
        
        # Process music tracks
        music_inputs = []
        voice_offset = len(synchronized.voice_segments)
        for idx, segment in enumerate(synchronized.music_segments):
            input_idx = voice_offset + idx
            input_label = f"[{input_idx}:a]"
            music_inputs.append(input_label)
            
            # Add volume and fade filters
            filter_parts = []
            if segment.volume != 1.0:
                filter_parts.append(f"volume={segment.volume}")
            if segment.fade_in > 0:
                filter_parts.append(
                    f"afade=t=in:st={segment.start_time}:d={segment.fade_in}"
                )
            if segment.fade_out > 0:
                fade_start = segment.start_time + segment.duration - segment.fade_out
                filter_parts.append(
                    f"afade=t=out:st={fade_start}:d={segment.fade_out}"
                )
            
            if filter_parts:
                filters.append(f"{input_label},{','.join(filter_parts)}[m{idx}]")
        
        # Mix all tracks together
        if voice_inputs and music_inputs:
            all_inputs = voice_inputs + music_inputs
            mix_labels = "".join(f"[{i}]" for i in all_inputs)
            filters.append(f"{mix_labels}amix=inputs={len(all_inputs)}[out]")
        elif voice_inputs:
            mix_labels = "".join(f"[{i}]" for i in voice_inputs)
            filters.append(f"{mix_labels}amix=inputs={len(voice_inputs)}[out]")
        elif music_inputs:
            mix_labels = "".join(f"[{i}]" for i in music_inputs)
            filters.append(f"{mix_labels}amix=inputs={len(music_inputs)}[out]")
        
        return ";".join(filters) if filters else ""
    
    def calculate_scene_voice_mapping(
        self,
        voice_segments: List[AudioSegment],
        scene_timings: List[Dict[str, float]]
    ) -> List[Dict[str, Any]]:
        """
        Map voice segments to scenes for synchronization.
        
        Args:
            voice_segments: Voice narration segments
            scene_timings: List of scene start/duration times
            
        Returns:
            List of scene-to-voice mappings
        """
        mapping = []
        
        for scene in scene_timings:
            scene_start = scene.get("start_time", 0.0)
            scene_duration = scene.get("duration", 0.0)
            scene_end = scene_start + scene_duration
            
            # Find overlapping voice segments
            overlapping_voices = []
            for voice in voice_segments:
                voice_end = voice.start_time + voice.duration
                if scene_start < voice_end and scene_end > voice.start_time:
                    overlapping_voices.append({
                        "segment_id": voice.segment_id,
                        "asset_key": voice.asset_key,
                        "overlap_start": max(scene_start, voice.start_time),
                        "overlap_end": min(scene_end, voice_end)
                    })
            
            mapping.append({
                "scene_start": scene_start,
                "scene_duration": scene_duration,
                "voice_segments": overlapping_voices
            })
        
        return mapping


__all__ = [
    "AudioTrackType",
    "AudioSegment",
    "AudioMixConfig",
    "SynchronizedAudio",
    "AudioSynchronizer",
]
