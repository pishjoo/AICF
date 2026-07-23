"""
Thumbnail Generator

Extracts and selects best frames from rendered videos.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ThumbnailSelectionMethod(str, Enum):
    """Methods for selecting thumbnail frames."""
    FIRST_FRAME = "first_frame"
    MIDDLE_FRAME = "middle_frame"
    LAST_FRAME = "last_frame"
    BEST_SCORE = "best_score"
    CUSTOM_TIME = "custom_time"


@dataclass
class ThumbnailCandidate:
    """A candidate frame for thumbnail selection."""
    
    frame_index: int
    timestamp: float  # Seconds into video
    score: float = 0.0  # Quality/interest score
    is_dark: bool = False
    is_blurry: bool = False
    has_text: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "timestamp": self.timestamp,
            "score": self.score,
            "is_dark": self.is_dark,
            "is_blurry": self.is_blurry,
            "has_text": self.has_text
        }


@dataclass
class GeneratedThumbnail:
    """Result of thumbnail generation."""
    
    thumbnail_id: str
    source_video_key: str
    selected_timestamp: float
    storage_key: str
    width: int
    height: int
    format: str = "jpg"
    quality: int = 85
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "thumbnail_id": self.thumbnail_id,
            "source_video_key": self.source_video_key,
            "selected_timestamp": self.selected_timestamp,
            "storage_key": self.storage_key,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "quality": self.quality,
            "metadata": self.metadata
        }


class ThumbnailGenerator:
    """
    Generates thumbnails from video files.
    
    Capabilities:
    - Extract frames from rendered video
    - Select best frames
    - Generate thumbnail variants
    """
    
    def __init__(
        self,
        default_width: int = 1280,
        default_height: int = 720,
        default_format: str = "jpg",
        default_quality: int = 85
    ):
        self.default_width = default_width
        self.default_height = default_height
        self.default_format = default_format
        self.default_quality = default_quality
        self.logger = logging.getLogger("rendering.thumbnail")
    
    def select_best_frame(
        self,
        video_duration: float,
        fps: float = 30.0,
        method: ThumbnailSelectionMethod = ThumbnailSelectionMethod.BEST_SCORE,
        custom_time: Optional[float] = None,
        candidates: Optional[List[ThumbnailCandidate]] = None
    ) -> ThumbnailCandidate:
        """
        Select the best frame for thumbnail extraction.
        
        Args:
            video_duration: Total video duration in seconds
            fps: Video frames per second
            method: Selection method to use
            custom_time: Custom timestamp if method is CUSTOM_TIME
            candidates: Pre-analyzed frame candidates
            
        Returns:
            Selected ThumbnailCandidate
        """
        if method == ThumbnailSelectionMethod.CUSTOM_TIME and custom_time is not None:
            frame_index = int(custom_time * fps)
            return ThumbnailCandidate(
                frame_index=frame_index,
                timestamp=custom_time,
                score=1.0
            )
        
        elif method == ThumbnailSelectionMethod.FIRST_FRAME:
            return ThumbnailCandidate(
                frame_index=0,
                timestamp=0.0,
                score=1.0
            )
        
        elif method == ThumbnailSelectionMethod.MIDDLE_FRAME:
            mid_time = video_duration / 2.0
            frame_index = int(mid_time * fps)
            return ThumbnailCandidate(
                frame_index=frame_index,
                timestamp=mid_time,
                score=1.0
            )
        
        elif method == ThumbnailSelectionMethod.LAST_FRAME:
            last_time = video_duration - 0.5  # Slightly before end
            frame_index = int(last_time * fps)
            return ThumbnailCandidate(
                frame_index=frame_index,
                timestamp=last_time,
                score=1.0
            )
        
        elif method == ThumbnailSelectionMethod.BEST_SCORE and candidates:
            # Filter out dark and blurry frames
            valid_candidates = [
                c for c in candidates 
                if not c.is_dark and not c.is_blurry
            ]
            
            if not valid_candidates:
                valid_candidates = candidates
            
            if valid_candidates:
                best = max(valid_candidates, key=lambda c: c.score)
                return best
        
        # Default to middle frame
        mid_time = video_duration / 3.0  # Use 1/3 point as default
        frame_index = int(mid_time * fps)
        return ThumbnailCandidate(
            frame_index=frame_index,
            timestamp=mid_time,
            score=1.0
        )
    
    def generate_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        timestamp: float,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: Optional[int] = None
    ) -> List[str]:
        """
        Generate FFmpeg command for thumbnail extraction.
        
        Args:
            input_path: Input video file path
            output_path: Output thumbnail file path
            timestamp: Time position to extract frame
            width: Target width (optional)
            height: Target height (optional)
            quality: JPEG quality 1-100 (optional)
            
        Returns:
            FFmpeg command arguments list
        """
        w = width or self.default_width
        h = height or self.default_height
        q = quality or self.default_quality
        
        args = [
            "-ss", str(timestamp),  # Seek to timestamp
            "-i", input_path,
            "-vframes", "1",  # Extract single frame
            "-vf", f"scale={w}:{h}",  # Scale to target size
            "-q:v", str(q),  # Quality
            "-y",  # Overwrite output
            output_path
        ]
        
        return args
    
    def generate_variants(
        self,
        video_duration: float,
        fps: float = 30.0,
        variant_count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple thumbnail variant timestamps.
        
        Args:
            video_duration: Total video duration
            fps: Video frames per second
            variant_count: Number of variants to generate
            
        Returns:
            List of variant configurations
        """
        variants = []
        
        # Generate evenly spaced timestamps
        intervals = variant_count + 1
        for i in range(1, variant_count + 1):
            timestamp = (video_duration / intervals) * i
            frame_index = int(timestamp * fps)
            
            variants.append({
                "variant_index": i,
                "timestamp": timestamp,
                "frame_index": frame_index,
                "position": f"{i}/{variant_count}"
            })
        
        return variants
    
    def analyze_frame_quality(
        self,
        frame_data: bytes
    ) -> Dict[str, Any]:
        """
        Analyze frame quality metrics.
        
        Note: Full implementation would use image processing
        libraries to detect blur, darkness, etc.
        
        Args:
            frame_data: Raw frame image data
            
        Returns:
            Quality analysis results
        """
        # Placeholder for actual image analysis
        # Would implement:
        # - Blur detection (Laplacian variance)
        # - Brightness analysis
        # - Contrast measurement
        # - Face/object detection
        
        return {
            "is_dark": False,
            "is_blurry": False,
            "brightness_score": 0.5,
            "sharpness_score": 0.8,
            "has_faces": False,
            "has_text": False
        }


__all__ = [
    "ThumbnailSelectionMethod",
    "ThumbnailCandidate",
    "GeneratedThumbnail",
    "ThumbnailGenerator",
]
