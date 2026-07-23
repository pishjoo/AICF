"""
Video Export System

Handles multi-format video export with platform-specific profiles.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class VideoFormat(str, Enum):
    """Supported output video formats."""
    MP4 = "mp4"
    WEBM = "webm"
    MOV = "mov"
    AVI = "avi"


class ExportProfile(str, Enum):
    """Predefined export profiles for different platforms."""
    YOUTUBE_1080P = "youtube_1080p"
    YOUTUBE_720P = "youtube_720p"
    YOUTUBE_SHORTS = "youtube_shorts"
    INSTAGRAM_REELS = "instagram_reels"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    CUSTOM = "custom"


@dataclass
class ExportProfileConfig:
    """Configuration for an export profile."""
    
    profile: ExportProfile
    format: VideoFormat
    resolution: str
    fps: float
    video_codec: str
    audio_codec: str
    video_bitrate: str  # e.g., "5000k"
    audio_bitrate: str  # e.g., "192k"
    max_duration: Optional[float] = None  # Platform max duration
    aspect_ratio: str = "16:9"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.value,
            "format": self.format.value,
            "resolution": self.resolution,
            "fps": self.fps,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "video_bitrate": self.video_bitrate,
            "audio_bitrate": self.audio_bitrate,
            "max_duration": self.max_duration,
            "aspect_ratio": self.aspect_ratio
        }


# Predefined profile configurations
EXPORT_PROFILES: Dict[ExportProfile, ExportProfileConfig] = {
    ExportProfile.YOUTUBE_1080P: ExportProfileConfig(
        profile=ExportProfile.YOUTUBE_1080P,
        format=VideoFormat.MP4,
        resolution="1920x1080",
        fps=30.0,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="192k",
        aspect_ratio="16:9"
    ),
    ExportProfile.YOUTUBE_720P: ExportProfileConfig(
        profile=ExportProfile.YOUTUBE_720P,
        format=VideoFormat.MP4,
        resolution="1280x720",
        fps=30.0,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="5000k",
        audio_bitrate="128k",
        aspect_ratio="16:9"
    ),
    ExportProfile.YOUTUBE_SHORTS: ExportProfileConfig(
        profile=ExportProfile.YOUTUBE_SHORTS,
        format=VideoFormat.MP4,
        resolution="1080x1920",
        fps=30.0,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="192k",
        max_duration=60.0,
        aspect_ratio="9:16"
    ),
    ExportProfile.INSTAGRAM_REELS: ExportProfileConfig(
        profile=ExportProfile.INSTAGRAM_REELS,
        format=VideoFormat.MP4,
        resolution="1080x1920",
        fps=30.0,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="6000k",
        audio_bitrate="128k",
        max_duration=90.0,
        aspect_ratio="9:16"
    ),
    ExportProfile.TIKTOK: ExportProfileConfig(
        profile=ExportProfile.TIKTOK,
        format=VideoFormat.MP4,
        resolution="1080x1920",
        fps=30.0,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="6000k",
        audio_bitrate="128k",
        max_duration=180.0,
        aspect_ratio="9:16"
    ),
    ExportProfile.TWITTER: ExportProfileConfig(
        profile=ExportProfile.TWITTER,
        format=VideoFormat.MP4,
        resolution="1280x720",
        fps=30.0,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="5000k",
        audio_bitrate="128k",
        max_duration=140.0,
        aspect_ratio="16:9"
    ),
    ExportProfile.LINKEDIN: ExportProfileConfig(
        profile=ExportProfile.LINKEDIN,
        format=VideoFormat.MP4,
        resolution="1920x1080",
        fps=30.0,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="5000k",
        audio_bitrate="128k",
        max_duration=600.0,
        aspect_ratio="16:9"
    ),
}


@dataclass
class ExportResult:
    """Result of a video export operation."""
    
    export_id: str
    source_key: str
    output_key: str
    profile: ExportProfile
    format: VideoFormat
    file_size_bytes: int
    duration_seconds: float
    resolution: str
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "export_id": self.export_id,
            "source_key": self.source_key,
            "output_key": self.output_key,
            "profile": self.profile.value,
            "format": self.format.value,
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "resolution": self.resolution,
            "success": self.success,
            "error_message": self.error_message
        }


class VideoExporter:
    """
    Exports videos in multiple formats with platform-specific profiles.
    
    Support:
    Formats: MP4, WebM, MOV
    Profiles: YouTube 1080p, YouTube Shorts, Instagram Reels, TikTok
    """
    
    def __init__(self):
        self.logger = logging.getLogger("rendering.export")
        self.profiles = EXPORT_PROFILES.copy()
    
    def get_profile_config(
        self,
        profile: ExportProfile
    ) -> ExportProfileConfig:
        """Get configuration for a specific export profile."""
        if profile not in self.profiles:
            raise ValueError(f"Unknown export profile: {profile}")
        return self.profiles[profile]
    
    def register_custom_profile(
        self,
        name: str,
        config: ExportProfileConfig
    ) -> None:
        """Register a custom export profile."""
        self.profiles[config.profile] = config
        self.logger.info(f"Registered custom export profile: {name}")
    
    def generate_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        profile: ExportProfile,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate FFmpeg command for video export.
        
        Args:
            input_path: Input video file path
            output_path: Output file path
            profile: Export profile to use
            custom_config: Optional custom configuration overrides
            
        Returns:
            FFmpeg command arguments list
        """
        config = self.get_profile_config(profile)
        
        # Apply custom overrides
        if custom_config:
            if "resolution" in custom_config:
                config.resolution = custom_config["resolution"]
            if "video_bitrate" in custom_config:
                config.video_bitrate = custom_config["video_bitrate"]
            if "audio_bitrate" in custom_config:
                config.audio_bitrate = custom_config["audio_bitrate"]
        
        width, height = config.resolution.split("x")
        
        args = [
            "-i", input_path,
            "-c:v", config.video_codec,
            "-b:v", config.video_bitrate,
            "-vf", f"scale={width}:{height}",
            "-r", str(config.fps),
            "-c:a", config.audio_codec,
            "-b:a", config.audio_bitrate,
            "-pix_fmt", "yuv420p",  # Compatible with most players
            "-movflags", "+faststart",  # Enable fast web start
            "-y",  # Overwrite output
            output_path
        ]
        
        # Add duration limit if specified
        if config.max_duration:
            args.insert(-1, "-t")
            args.insert(-1, str(config.max_duration))
        
        return args
    
    def validate_for_platform(
        self,
        video_duration: float,
        profile: ExportProfile
    ) -> Dict[str, Any]:
        """
        Validate video meets platform requirements.
        
        Args:
            video_duration: Video duration in seconds
            profile: Target export profile
            
        Returns:
            Validation result with any issues
        """
        config = self.get_profile_config(profile)
        issues = []
        warnings = []
        
        # Check duration
        if config.max_duration and video_duration > config.max_duration:
            issues.append(
                f"Video duration ({video_duration}s) exceeds "
                f"{profile.value} maximum ({config.max_duration}s)"
            )
        elif config.max_duration and video_duration > config.max_duration * 0.9:
            warnings.append(
                f"Video duration is close to {profile.value} limit"
            )
        
        return {
            "valid": len(issues) == 0,
            "profile": profile.value,
            "issues": issues,
            "warnings": warnings,
            "requirements": {
                "max_duration": config.max_duration,
                "resolution": config.resolution,
                "aspect_ratio": config.aspect_ratio
            }
        }
    
    def estimate_file_size(
        self,
        duration: float,
        profile: ExportProfile
    ) -> int:
        """
        Estimate output file size based on profile bitrate.
        
        Args:
            duration: Video duration in seconds
            profile: Export profile
            
        Returns:
            Estimated file size in bytes
        """
        config = self.get_profile_config(profile)
        
        # Parse bitrate (e.g., "5000k" -> 5000000 bits/s)
        video_bitrate_str = config.video_bitrate.replace("k", "000")
        audio_bitrate_str = config.audio_bitrate.replace("k", "000")
        
        try:
            video_bps = int(video_bitrate_str)
            audio_bps = int(audio_bitrate_str)
        except ValueError:
            # Fallback estimate
            video_bps = 5000000
            audio_bps = 128000
        
        total_bits = (video_bps + audio_bps) * duration
        total_bytes = total_bits // 8
        
        # Add ~5% overhead for container
        return int(total_bytes * 1.05)


__all__ = [
    "VideoFormat",
    "ExportProfile",
    "ExportProfileConfig",
    "EXPORT_PROFILES",
    "ExportResult",
    "VideoExporter",
]
