"""
FFmpeg Wrapper Foundation

FFmpeg executor interface for video rendering operations.
Does not implement full rendering commands yet - only foundation.
"""

import logging
import subprocess
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MediaMetadata:
    """Metadata extracted from media file."""
    
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None  # bits per second
    audio_codec: Optional[str] = None
    audio_channels: Optional[int] = None
    audio_sample_rate: Optional[int] = None
    format: Optional[str] = None
    file_size_bytes: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration_seconds": self.duration_seconds,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "audio_codec": self.audio_codec,
            "audio_channels": self.audio_channels,
            "audio_sample_rate": self.audio_sample_rate,
            "format": self.format,
            "file_size_bytes": self.file_size_bytes
        }


@dataclass
class FFmpegExecutionResult:
    """Result of FFmpeg execution."""
    
    success: bool
    return_code: int
    stdout: str
    stderr: str
    command: List[str]
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "command": self.command,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message
        }


class FFmpegExecutor(ABC):
    """
    Abstract base class for FFmpeg execution.
    
    Provides interface for:
    - execute() - Run FFmpeg commands
    - validate_input() - Validate input files
    - get_metadata() - Extract media metadata
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.logger = logging.getLogger(f"rendering.ffmpeg.{type(self).__name__}")
    
    @abstractmethod
    def execute(
        self,
        args: List[str],
        timeout: float = 300.0,
        capture_output: bool = True
    ) -> FFmpegExecutionResult:
        """
        Execute FFmpeg with given arguments.
        
        Args:
            args: FFmpeg command arguments (without 'ffmpeg' prefix)
            timeout: Maximum execution time in seconds
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            Execution result with output and status
        """
        pass
    
    @abstractmethod
    def validate_input(self, input_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an input file for FFmpeg processing.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def get_metadata(self, input_path: str) -> Optional[MediaMetadata]:
        """
        Get metadata from a media file using ffprobe.
        
        Args:
            input_path: Path to media file
            
        Returns:
            MediaMetadata or None if extraction failed
        """
        pass


class SubprocessFFmpegExecutor(FFmpegExecutor):
    """
    FFmpeg executor using subprocess.
    
    Standard implementation for local FFmpeg installations.
    """
    
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        global_args: Optional[List[str]] = None
    ):
        super().__init__(ffmpeg_path, ffprobe_path)
        self.global_args = global_args or [
            "-loglevel", "warning",  # Reduce log verbosity
            "-y"  # Overwrite output files without asking
        ]
    
    def execute(
        self,
        args: List[str],
        timeout: float = 300.0,
        capture_output: bool = True
    ) -> FFmpegExecutionResult:
        """Execute FFmpeg command using subprocess."""
        import time
        
        command = [self.ffmpeg_path] + self.global_args + args
        self.logger.debug(f"Executing FFmpeg: {' '.join(command)}")
        
        start_time = time.time()
        
        try:
            if capture_output:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                stdout = result.stdout
                stderr = result.stderr
                return_code = result.returncode
            else:
                result = subprocess.run(
                    command,
                    capture_output=False,
                    timeout=timeout
                )
                stdout = ""
                stderr = ""
                return_code = result.returncode
            
            duration = time.time() - start_time
            success = return_code == 0
            
            if not success:
                self.logger.error(f"FFmpeg command failed with code {return_code}: {stderr[:500]}")
            
            return FFmpegExecutionResult(
                success=success,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                command=command,
                duration_seconds=duration,
                error_message=stderr if not success else None
            )
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"FFmpeg command timed out after {timeout}s")
            return FFmpegExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                command=command,
                duration_seconds=timeout,
                error_message=f"Timeout after {timeout}s"
            )
        except FileNotFoundError:
            self.logger.error(f"FFmpeg not found at {self.ffmpeg_path}")
            return FFmpegExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"FFmpeg not found at {self.ffmpeg_path}",
                command=command,
                error_message="FFmpeg executable not found"
            )
        except Exception as e:
            self.logger.exception(f"FFmpeg execution failed: {e}")
            return FFmpegExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                command=command,
                error_message=str(e)
            )
    
    def validate_input(self, input_path: str) -> Tuple[bool, Optional[str]]:
        """Validate input file exists and is readable by FFmpeg."""
        path = Path(input_path)
        
        # Check file exists
        if not path.exists():
            return False, f"Input file does not exist: {input_path}"
        
        # Check file is readable
        if not path.is_file():
            return False, f"Input path is not a file: {input_path}"
        
        # Try to get metadata to verify it's a valid media file
        metadata = self.get_metadata(input_path)
        if metadata is None:
            return False, f"Cannot read media metadata from: {input_path}"
        
        return True, None
    
    def get_metadata(self, input_path: str) -> Optional[MediaMetadata]:
        """Extract metadata using ffprobe."""
        probe_args = [
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            input_path
        ]
        
        command = [self.ffprobe_path] + probe_args
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30.0
            )
            
            if result.returncode != 0:
                self.logger.warning(f"ffprobe failed for {input_path}: {result.stderr[:200]}")
                return None
            
            data = json.loads(result.stdout)
            
            # Extract format info
            format_info = data.get("format", {})
            
            # Extract stream info (video and audio)
            streams = data.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
            
            metadata = MediaMetadata(
                duration_seconds=float(format_info.get("duration", 0)) if format_info.get("duration") else None,
                width=video_stream.get("width") if video_stream else None,
                height=video_stream.get("height") if video_stream else None,
                fps=self._parse_fps(video_stream) if video_stream else None,
                codec=video_stream.get("codec_name") if video_stream else None,
                bitrate=int(format_info.get("bit_rate", 0)) if format_info.get("bit_rate") else None,
                audio_codec=audio_stream.get("codec_name") if audio_stream else None,
                audio_channels=audio_stream.get("channels") if audio_stream else None,
                audio_sample_rate=int(audio_stream.get("sample_rate", 0)) if audio_stream and audio_stream.get("sample_rate") else None,
                format=format_info.get("format_name"),
                file_size_bytes=int(format_info.get("size", 0)) if format_info.get("size") else None
            )
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to extract metadata from {input_path}: {e}")
            return None
    
    def _parse_fps(self, video_stream: Dict[str, Any]) -> Optional[float]:
        """Parse FPS from video stream info."""
        r_frame_rate = video_stream.get("r_frame_rate")
        if r_frame_rate:
            try:
                num, denom = map(int, r_frame_rate.split("/"))
                if denom > 0:
                    return num / denom
            except (ValueError, ZeroDivisionError):
                pass
        
        avg_frame_rate = video_stream.get("avg_frame_rate")
        if avg_frame_rate:
            try:
                num, denom = map(int, avg_frame_rate.split("/"))
                if denom > 0:
                    return num / denom
            except (ValueError, ZeroDivisionError):
                pass
        
        return None
