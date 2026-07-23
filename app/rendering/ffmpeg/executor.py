"""
FFmpeg Executor Implementation

Concrete implementation of FFmpegExecutor with GPU support.
"""

import logging
import subprocess
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from app.rendering.ffmpeg import (
    FFmpegExecutor,
    MediaMetadata,
    FFmpegExecutionResult,
)
from app.rendering.gpu import RenderBackend, get_gpu_manager


class SubprocessFFmpegExecutor(FFmpegExecutor):
    """
    FFmpeg executor using subprocess.
    
    Supports CPU and GPU-accelerated rendering.
    """

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        global_args: Optional[List[str]] = None
    ):
        super().__init__(ffmpeg_path, ffprobe_path)
        self.global_args = global_args or [
            "-loglevel", "warning",
            "-y"
        ]
        self.gpu_manager = get_gpu_manager()

    def execute(
        self,
        args: List[str],
        timeout: float = 300.0,
        capture_output: bool = True,
        gpu_backend: Optional[RenderBackend] = None,
        gpu_index: Optional[int] = None
    ) -> FFmpegExecutionResult:
        """Execute FFmpeg command with optional GPU acceleration."""
        command = [self.ffmpeg_path] + self.global_args + args
        
        # Add GPU-specific arguments if backend specified
        gpu_used = False
        backend_used = None
        
        if gpu_backend and gpu_backend != RenderBackend.CPU:
            if gpu_index is None:
                gpu_index = 0
            
            gpu_args = self.gpu_manager.get_ffmpeg_gpu_args(gpu_index, gpu_backend)
            command = [self.ffmpeg_path] + self.global_args + gpu_args + args
            gpu_used = True
            backend_used = gpu_backend.value
        
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
                error_message=stderr if not success else None,
                gpu_used=gpu_used,
                gpu_index=gpu_index,
                backend_used=backend_used
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
        
        if not path.exists():
            return False, f"Input file does not exist: {input_path}"
        
        if not path.is_file():
            return False, f"Input path is not a file: {input_path}"
        
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
            
            format_info = data.get("format", {})
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
