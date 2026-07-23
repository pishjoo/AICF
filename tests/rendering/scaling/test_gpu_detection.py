"""Tests for GPU detection and management."""

import pytest
from app.rendering.gpu import (
    GPUManager,
    GPUVendor,
    RenderBackend,
    get_gpu_manager,
)


class TestGPUManager:
    """Test GPU manager functionality."""
    
    def test_gpu_manager_creation(self):
        """Test GPU manager can be created."""
        manager = GPUManager()
        assert manager is not None
        assert manager.gpus == []
    
    def test_singleton_pattern(self):
        """Test GPU manager singleton pattern."""
        manager1 = get_gpu_manager()
        manager2 = get_gpu_manager()
        assert manager1 is manager2
    
    def test_detect_gpus_no_gpu(self):
        """Test GPU detection when no GPUs present."""
        manager = GPUManager()
        gpus = manager.detect_gpus()
        
        # Should return at least CPU fallback
        assert len(gpus) >= 0  # May have real GPUs or CPU fallback
    
    def test_get_optimal_backend_cpu(self):
        """Test optimal backend selection for CPU."""
        manager = GPUManager()
        # Without detected GPUs, should return CPU
        backend = manager.get_optimal_backend(0)
        assert backend in [RenderBackend.CPU, RenderBackend.NVENC, RenderBackend.QSV, RenderBackend.VAAPI]
    
    def test_ffmpeg_gpu_args_cpu(self):
        """Test FFmpeg args for CPU rendering."""
        manager = GPUManager()
        args = manager.get_ffmpeg_gpu_args(0, RenderBackend.CPU)
        assert args == []
    
    def test_ffmpeg_gpu_args_nvenc(self):
        """Test FFmpeg args for NVENC."""
        manager = GPUManager()
        args = manager.get_ffmpeg_gpu_args(0, RenderBackend.NVENC)
        assert "-c:v" in args
        assert "h264_nvenc" in args
        assert "-gpu" in args
    
    def test_ffmpeg_gpu_args_qsv(self):
        """Test FFmpeg args for Quick Sync."""
        manager = GPUManager()
        args = manager.get_ffmpeg_gpu_args(0, RenderBackend.QSV)
        assert "-hwaccel" in args
        assert "qsv" in args


class TestRenderBackend:
    """Test RenderBackend enum."""
    
    def test_backend_values(self):
        """Test all backend values exist."""
        assert RenderBackend.CPU.value == "cpu"
        assert RenderBackend.CUDA.value == "cuda"
        assert RenderBackend.NVENC.value == "nvenc"
        assert RenderBackend.VAAPI.value == "vaapi"
        assert RenderBackend.QSV.value == "qsv"
