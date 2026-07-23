"""
GPU Rendering Support

GPU management for hardware-accelerated video rendering.
Supports NVIDIA CUDA, NVENC encoders, and GPU resource allocation.
"""

import logging
import subprocess
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class GPUVendor(str, Enum):
    """Supported GPU vendors."""
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    UNKNOWN = "unknown"


class RenderBackend(str, Enum):
    """Rendering backend types."""
    CPU = "cpu"
    CUDA = "cuda"
    NVENC = "nvenc"
    VAAPI = "vaapi"  # Intel/AMD hardware acceleration
    QSV = "qsv"  # Intel Quick Sync Video


@dataclass
class GPUInfo:
    """Information about a detected GPU."""
    
    index: int
    name: str
    vendor: GPUVendor
    memory_total_mb: int
    memory_used_mb: int = 0
    memory_free_mb: int = 0
    utilization_percent: float = 0.0
    temperature_celsius: Optional[float] = None
    cuda_compute_capability: Optional[str] = None
    nvenc_available: bool = False
    vaapi_available: bool = False
    qsv_available: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "vendor": self.vendor.value,
            "memory_total_mb": self.memory_total_mb,
            "memory_used_mb": self.memory_used_mb,
            "memory_free_mb": self.memory_free_mb,
            "utilization_percent": self.utilization_percent,
            "temperature_celsius": self.temperature_celsius,
            "cuda_compute_capability": self.cuda_compute_capability,
            "nvenc_available": self.nvenc_available,
            "vaapi_available": self.vaapi_available,
            "qsv_available": self.qsv_available
        }


@dataclass
class GPUAllocation:
    """Represents an allocated GPU resource."""
    
    gpu_index: int
    allocation_id: str
    allocated_at: float
    expires_at: Optional[float] = None
    job_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "gpu_index": self.gpu_index,
            "allocation_id": self.allocation_id,
            "allocated_at": self.allocated_at,
            "expires_at": self.expires_at,
            "job_id": self.job_id,
            "metadata": self.metadata
        }


class GPUManager:
    """
    Manages GPU resources for video rendering.
    
    Capabilities:
    - Detect available GPUs
    - NVIDIA CUDA support
    - Hardware acceleration detection
    - NVENC encoder support
    - GPU resource allocation
    """
    
    def __init__(self):
        self.logger = logging.getLogger("rendering.gpu.manager")
        self.gpus: List[GPUInfo] = []
        self.allocations: Dict[str, GPUAllocation] = {}
        self._detected = False
    
    def detect_gpus(self) -> List[GPUInfo]:
        """
        Detect available GPUs on the system.
        
        Returns list of detected GPU information.
        """
        self.logger.info("Detecting available GPUs...")
        self.gpus = []
        
        # Try NVIDIA detection first
        nvidia_gpus = self._detect_nvidia_gpus()
        if nvidia_gpus:
            self.gpus.extend(nvidia_gpus)
            self.logger.info(f"Detected {len(nvidia_gpus)} NVIDIA GPU(s)")
        
        # Try Intel detection
        intel_gpus = self._detect_intel_gpus()
        if intel_gpus:
            self.gpus.extend(intel_gpus)
            self.logger.info(f"Detected {len(intel_gpus)} Intel GPU(s)")
        
        # Try AMD detection
        amd_gpus = self._detect_amd_gpus()
        if amd_gpus:
            self.gpus.extend(amd_gpus)
            self.logger.info(f"Detected {len(amd_gpus)} AMD GPU(s)")
        
        if not self.gpus:
            self.logger.warning("No GPUs detected, falling back to CPU rendering")
            # Create a virtual CPU-only "GPU" entry
            self.gpus.append(GPUInfo(
                index=0,
                name="CPU",
                vendor=GPUVendor.UNKNOWN,
                memory_total_mb=0,
                vaapi_available=False,
                nvenc_available=False,
                qsv_available=False
            ))
        
        self._detected = True
        return self.gpus
    
    def _detect_nvidia_gpus(self) -> List[GPUInfo]:
        """Detect NVIDIA GPUs using nvidia-smi."""
        gpus = []
        
        try:
            # Check if nvidia-smi is available
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,compute_cap",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10.0
            )
            
            if result.returncode != 0:
                self.logger.debug("nvidia-smi not available or failed")
                return gpus
            
            lines = result.stdout.strip().split('\n')
            
            for idx, line in enumerate(lines):
                if not line.strip():
                    continue
                
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 8:
                    continue
                
                gpu_index = int(parts[0])
                gpu_name = parts[1]
                memory_total = int(parts[2])
                memory_used = int(parts[3])
                memory_free = int(parts[4])
                utilization = float(parts[5]) if parts[5] else 0.0
                temperature = float(parts[6]) if parts[6] else None
                compute_cap = parts[7] if parts[7] else None
                
                # Check NVENC availability
                nvenc_available = self._check_nvenc_support(gpu_index)
                
                gpu_info = GPUInfo(
                    index=gpu_index,
                    name=gpu_name,
                    vendor=GPUVendor.NVIDIA,
                    memory_total_mb=memory_total,
                    memory_used_mb=memory_used,
                    memory_free_mb=memory_free,
                    utilization_percent=utilization,
                    temperature_celsius=temperature,
                    cuda_compute_capability=compute_cap,
                    nvenc_available=nvenc_available,
                    vaapi_available=False,
                    qsv_available=False
                )
                gpus.append(gpu_info)
                
        except FileNotFoundError:
            self.logger.debug("nvidia-smi not found")
        except subprocess.TimeoutExpired:
            self.logger.warning("nvidia-smi timed out")
        except Exception as e:
            self.logger.error(f"Error detecting NVIDIA GPUs: {e}")
        
        return gpus
    
    def _detect_intel_gpus(self) -> List[GPUInfo]:
        """Detect Intel GPUs (Quick Sync Video)."""
        gpus = []
        
        try:
            # Check for Intel devices in /dev/dri
            dri_path = Path("/dev/dri")
            if not dri_path.exists():
                return gpus
            
            # Check for i915 driver (Intel)
            result = subprocess.run(
                ["lspci", "-nn"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            
            if result.returncode == 0:
                intel_devices = [
                    line for line in result.stdout.split('\n')
                    if 'VGA' in line or 'Display' in line
                    if 'Intel' in line or '8086' in line  # Intel PCI ID
                ]
                
                for idx, device in enumerate(intel_devices[:2]):  # Max 2 Intel GPUs
                    gpu_name = device.split(':')[-1].strip() if ':' in device else f"Intel GPU {idx}"
                    
                    # Check QSV availability
                    qsv_available = self._check_qsv_support()
                    
                    gpu_info = GPUInfo(
                        index=idx,
                        name=gpu_name,
                        vendor=GPUVendor.INTEL,
                        memory_total_mb=0,  # Shared memory
                        vaapi_available=True,
                        nvenc_available=False,
                        qsv_available=qsv_available
                    )
                    gpus.append(gpu_info)
                    
        except Exception as e:
            self.logger.debug(f"Error detecting Intel GPUs: {e}")
        
        return gpus
    
    def _detect_amd_gpus(self) -> List[GPUInfo]:
        """Detect AMD GPUs."""
        gpus = []
        
        try:
            result = subprocess.run(
                ["lspci", "-nn"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            
            if result.returncode == 0:
                amd_devices = [
                    line for line in result.stdout.split('\n')
                    if ('VGA' in line or 'Display' in line)
                    and ('AMD' in line or 'Advanced Micro Devices' in line or '1002' in line)
                ]
                
                for idx, device in enumerate(amd_devices[:2]):
                    gpu_name = device.split(':')[-1].strip() if ':' in device else f"AMD GPU {idx}"
                    
                    gpu_info = GPUInfo(
                        index=idx,
                        name=gpu_name,
                        vendor=GPUVendor.AMD,
                        memory_total_mb=0,  # Would need rocm-smi for detailed info
                        vaapi_available=True,
                        nvenc_available=False,
                        qsv_available=False
                    )
                    gpus.append(gpu_info)
                    
        except Exception as e:
            self.logger.debug(f"Error detecting AMD GPUs: {e}")
        
        return gpus
    
    def _check_nvenc_support(self, gpu_index: int = 0) -> bool:
        """Check if NVENC encoder is available on NVIDIA GPU."""
        try:
            # Try to run ffmpeg with nvenc to check support
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            
            if result.returncode == 0:
                return "h264_nvenc" in result.stdout.lower() or "hevc_nvenc" in result.stdout.lower()
        except Exception:
            pass
        
        return False
    
    def _check_qsv_support(self) -> bool:
        """Check if Intel Quick Sync Video is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            
            if result.returncode == 0:
                return "h264_qsv" in result.stdout.lower() or "hevc_qsv" in result.stdout.lower()
        except Exception:
            pass
        
        return False
    
    def get_gpu(self, index: int) -> Optional[GPUInfo]:
        """Get information about a specific GPU."""
        if not self._detected:
            self.detect_gpus()
        
        for gpu in self.gpus:
            if gpu.index == index:
                return gpu
        return None
    
    def get_available_gpu(self, min_memory_mb: int = 0) -> Optional[GPUInfo]:
        """
        Get an available GPU with sufficient memory.
        
        Args:
            min_memory_mb: Minimum required free memory in MB
            
        Returns:
            GPUInfo if available GPU found, None otherwise
        """
        if not self._detected:
            self.detect_gpus()
        
        for gpu in self.gpus:
            if gpu.memory_free_mb >= min_memory_mb:
                # Check if not already allocated
                is_allocated = any(
                    alloc.gpu_index == gpu.index and alloc.expires_at is None
                    for alloc in self.allocations.values()
                )
                if not is_allocated:
                    return gpu
        
        return None
    
    def allocate_gpu(
        self,
        gpu_index: int,
        job_id: Optional[str] = None,
        expiration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[GPUAllocation]:
        """
        Allocate a GPU for a rendering job.
        
        Args:
            gpu_index: Index of GPU to allocate
            job_id: Optional job identifier
            expiration_seconds: Optional allocation expiration time
            metadata: Optional metadata about the allocation
            
        Returns:
            GPUAllocation if successful, None if GPU not available
        """
        import time
        import uuid
        
        if not self._detected:
            self.detect_gpus()
        
        gpu = self.get_gpu(gpu_index)
        if not gpu:
            self.logger.warning(f"Cannot allocate GPU {gpu_index}: GPU not found")
            return None
        
        allocation_id = str(uuid.uuid4())
        now = time.time()
        
        allocation = GPUAllocation(
            gpu_index=gpu_index,
            allocation_id=allocation_id,
            allocated_at=now,
            expires_at=now + expiration_seconds if expiration_seconds else None,
            job_id=job_id,
            metadata=metadata or {}
        )
        
        self.allocations[allocation_id] = allocation
        self.logger.info(f"Allocated GPU {gpu_index} for job {job_id} (allocation: {allocation_id})")
        
        return allocation
    
    def release_allocation(self, allocation_id: str) -> bool:
        """
        Release a GPU allocation.
        
        Args:
            allocation_id: ID of allocation to release
            
        Returns:
            True if released successfully, False if allocation not found
        """
        if allocation_id not in self.allocations:
            self.logger.warning(f"Cannot release allocation {allocation_id}: not found")
            return False
        
        allocation = self.allocations.pop(allocation_id)
        self.logger.info(f"Released GPU {allocation.gpu_index} allocation {allocation_id}")
        return True
    
    def get_ffmpeg_gpu_args(self, gpu_index: int, backend: RenderBackend) -> List[str]:
        """
        Get FFmpeg arguments for GPU-accelerated encoding.
        
        Args:
            gpu_index: Index of GPU to use
            backend: Rendering backend type
            
        Returns:
            List of FFmpeg command arguments
        """
        args = []
        
        if backend == RenderBackend.CUDA:
            args.extend(["-hwaccel", "cuda", "-hwaccel_device", str(gpu_index)])
        
        elif backend == RenderBackend.NVENC:
            args.extend([
                "-c:v", "h264_nvenc",
                "-gpu", str(gpu_index),
                "-preset", "p4",  # Quality preset
                "-tune", "hq"
            ])
        
        elif backend == RenderBackend.VAAPI:
            args.extend([
                "-hwaccel", "vaapi",
                "-hwaccel_device", f"/dev/dri/renderD128",
                "-hwaccel_output_format", "vaapi"
            ])
        
        elif backend == RenderBackend.QSV:
            args.extend([
                "-hwaccel", "qsv",
                "-qsv_device", str(gpu_index),
                "-c:v", "h264_qsv",
                "-preset", "balanced"
            ])
        
        return args
    
    def get_optimal_backend(self, gpu_index: int) -> RenderBackend:
        """
        Determine optimal rendering backend for a GPU.
        
        Args:
            gpu_index: Index of GPU
            
        Returns:
            Optimal RenderBackend for the GPU
        """
        if not self._detected:
            self.detect_gpus()
        
        gpu = self.get_gpu(gpu_index)
        if not gpu:
            return RenderBackend.CPU
        
        if gpu.vendor == GPUVendor.NVIDIA:
            if gpu.nvenc_available:
                return RenderBackend.NVENC
            elif gpu.cuda_compute_capability:
                return RenderBackend.CUDA
        
        elif gpu.vendor == GPUVendor.INTEL:
            if gpu.qsv_available:
                return RenderBackend.QSV
            elif gpu.vaapi_available:
                return RenderBackend.VAAPI
        
        elif gpu.vendor == GPUVendor.AMD:
            if gpu.vaapi_available:
                return RenderBackend.VAAPI
        
        return RenderBackend.CPU
    
    def get_all_gpus_info(self) -> List[Dict[str, Any]]:
        """Get information about all detected GPUs."""
        if not self._detected:
            self.detect_gpus()
        
        return [gpu.to_dict() for gpu in self.gpus]
    
    def refresh_gpu_stats(self) -> None:
        """Refresh GPU statistics (utilization, memory, temperature)."""
        if not self._detected:
            return
        
        # Re-detect to get updated stats
        self.detect_gpus()


# Singleton instance
_gpu_manager: Optional[GPUManager] = None


def get_gpu_manager() -> GPUManager:
    """Get or create the GPU manager singleton."""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUManager()
    return _gpu_manager
