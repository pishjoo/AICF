"""
Storage Providers

Abstract interface and implementations for asset storage.
Supports local storage, S3, Cloudflare R2, and MinIO.
"""

import os
import logging
import shutil
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, BinaryIO
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import hashlib


class StorageProviderType(str, Enum):
    """Storage provider types."""
    LOCAL = "local"
    S3 = "s3"
    CLOUDFLARE_R2 = "cloudflare_r2"
    MINIO = "minio"


@dataclass
class StorageMetadata:
    """Metadata for stored assets."""
    
    filename: str
    content_type: Optional[str] = None
    file_size_bytes: int = 0
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "file_size_bytes": self.file_size_bytes,
            "checksum_md5": self.checksum_md5,
            "checksum_sha256": self.checksum_sha256,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "custom_metadata": self.custom_metadata
        }


@dataclass
class UploadResult:
    """Result of an upload operation."""
    
    success: bool
    storage_key: str  # Unique identifier for the stored file
    storage_url: str  # Access URL
    provider: StorageProviderType
    metadata: StorageMetadata
    error: Optional[str] = None
    
    @classmethod
    def success_result(
        cls,
        storage_key: str,
        storage_url: str,
        provider: StorageProviderType,
        metadata: StorageMetadata
    ) -> "UploadResult":
        return cls(
            success=True,
            storage_key=storage_key,
            storage_url=storage_url,
            provider=provider,
            metadata=metadata
        )
    
    @classmethod
    def failure_result(
        cls,
        error: str,
        provider: StorageProviderType
    ) -> "UploadResult":
        return cls(
            success=False,
            storage_key="",
            storage_url="",
            provider=provider,
            metadata=StorageMetadata(filename=""),
            error=error
        )


class StorageProvider(ABC):
    """
    Abstract base class for storage providers.
    
    Interface defining operations for:
    - upload(file, key) -> UploadResult
    - delete(key) -> bool
    - get_url(key) -> str
    - exists(key) -> bool
    """
    
    def __init__(self, provider_type: StorageProviderType):
        self.provider_type = provider_type
        self.logger = logging.getLogger(f"storage.{provider_type.value}")
    
    @abstractmethod
    def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """
        Upload a file to storage.
        
        Args:
            file: File-like object to upload.
            key: Unique storage key/identifier.
            content_type: MIME type of the file.
            metadata: Additional metadata to store.
            
        Returns:
            UploadResult with success status and access details.
        """
        pass
    
    @abstractmethod
    def download(self, key: str) -> Optional[BinaryIO]:
        """
        Download a file from storage.
        
        Args:
            key: Storage key of the file.
            
        Returns:
            File-like object or None if not found.
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            key: Storage key of the file.
            
        Returns:
            True if deleted, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Get access URL for a stored file.
        
        Args:
            key: Storage key of the file.
            expires_in: Seconds until URL expires (for signed URLs).
            
        Returns:
            Access URL string.
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            key: Storage key to check.
            
        Returns:
            True if exists, False otherwise.
        """
        pass
    
    def _calculate_checksums(self, file: BinaryIO) -> tuple:
        """Calculate MD5 and SHA256 checksums of a file."""
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        
        # Save current position
        current_pos = file.tell()
        
        try:
            # Read file from beginning
            file.seek(0)
            for chunk in iter(lambda: file.read(8192), b""):
                md5_hash.update(chunk)
                sha256_hash.update(chunk)
            
            return md5_hash.hexdigest(), sha256_hash.hexdigest()
        finally:
            # Restore position
            file.seek(current_pos)


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider.
    
    Stores files on the local filesystem.
    Suitable for development and small deployments.
    """
    
    def __init__(self, base_path: str = "/tmp/aicf_storage"):
        super().__init__(StorageProviderType.LOCAL)
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"LocalStorageProvider initialized at {self.base_path}")
    
    def _get_file_path(self, key: str) -> Path:
        """Get the filesystem path for a storage key."""
        # Create subdirectories based on key for better organization
        # e.g., key "org_1/episode_5/script.txt" -> base/org_1/episode_5/script.txt
        parts = key.split("/")
        if len(parts) > 1:
            dir_path = self.base_path / "/".join(parts[:-1])
            dir_path.mkdir(parents=True, exist_ok=True)
        return self.base_path / key
    
    def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        try:
            file_path = self._get_file_path(key)
            
            # Calculate checksums
            md5_sum, sha256_sum = self._calculate_checksums(file)
            
            # Get file size
            current_pos = file.tell()
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(current_pos)  # Restore position
            
            # Write file
            file.seek(0)
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file, f)
            
            # Build metadata
            storage_metadata = StorageMetadata(
                filename=key.split("/")[-1],
                content_type=content_type,
                file_size_bytes=file_size,
                checksum_md5=md5_sum,
                checksum_sha256=sha256_sum,
                uploaded_at=datetime.now(timezone.utc),
                custom_metadata=metadata or {}
            )
            
            # Store metadata file
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
            with open(metadata_path, 'w') as f:
                import json
                json.dump(storage_metadata.to_dict(), f)
            
            # Generate URL
            storage_url = f"file://{file_path.absolute()}"
            
            self.logger.info(f"Uploaded file to {key} ({file_size} bytes)")
            
            return UploadResult.success_result(
                storage_key=key,
                storage_url=storage_url,
                provider=StorageProviderType.LOCAL,
                metadata=storage_metadata
            )
            
        except Exception as e:
            self.logger.exception(f"Upload failed for {key}: {e}")
            return UploadResult.failure_result(
                error=str(e),
                provider=StorageProviderType.LOCAL
            )
    
    def download(self, key: str) -> Optional[BinaryIO]:
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            self.logger.warning(f"File not found: {key}")
            return None
        
        try:
            return open(file_path, 'rb')
        except Exception as e:
            self.logger.error(f"Download failed for {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        file_path = self._get_file_path(key)
        metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
        
        try:
            deleted = False
            if file_path.exists():
                file_path.unlink()
                deleted = True
            if metadata_path.exists():
                metadata_path.unlink()
            
            self.logger.info(f"Deleted file: {key}")
            return deleted
        except Exception as e:
            self.logger.error(f"Delete failed for {key}: {e}")
            return False
    
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        
        return f"file://{file_path.absolute()}"
    
    def exists(self, key: str) -> bool:
        file_path = self._get_file_path(key)
        return file_path.exists()


class S3StorageProvider(StorageProvider):
    """
    AWS S3 storage provider (prepared for implementation).
    
    To implement:
    1. Install boto3: pip install boto3
    2. Configure AWS credentials
    3. Implement methods using boto3 S3 client
    """
    
    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None
    ):
        super().__init__(StorageProviderType.S3)
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url
        self.client = None  # Initialize boto3 client when ready
        self.logger.warning("S3StorageProvider is prepared but not fully implemented")
    
    def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        raise NotImplementedError("S3StorageProvider not yet implemented")
    
    def download(self, key: str) -> Optional[BinaryIO]:
        raise NotImplementedError("S3StorageProvider not yet implemented")
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError("S3StorageProvider not yet implemented")
    
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError("S3StorageProvider not yet implemented")
    
    def exists(self, key: str) -> bool:
        raise NotImplementedError("S3StorageProvider not yet implemented")


class CloudflareR2Provider(StorageProvider):
    """
    Cloudflare R2 storage provider (prepared for implementation).
    
    R2 is S3-compatible, so implementation is similar to S3StorageProvider.
    """
    
    def __init__(
        self,
        bucket: str,
        account_id: str,
        access_key_id: str,
        secret_access_key: str
    ):
        super().__init__(StorageProviderType.CLOUDFLARE_R2)
        self.bucket = bucket
        self.account_id = account_id
        self.endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.client = None  # Initialize boto3 client when ready
        self.logger.warning("CloudflareR2Provider is prepared but not fully implemented")
    
    def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        raise NotImplementedError("CloudflareR2Provider not yet implemented")
    
    def download(self, key: str) -> Optional[BinaryIO]:
        raise NotImplementedError("CloudflareR2Provider not yet implemented")
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError("CloudflareR2Provider not yet implemented")
    
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError("CloudflareR2Provider not yet implemented")
    
    def exists(self, key: str) -> bool:
        raise NotImplementedError("CloudflareR2Provider not yet implemented")


class MinIOProvider(StorageProvider):
    """
    MinIO storage provider (prepared for implementation).
    
    MinIO is S3-compatible object storage for private clouds.
    """
    
    def __init__(
        self,
        bucket: str,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False
    ):
        super().__init__(StorageProviderType.MINIO)
        self.bucket = bucket
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.client = None  # Initialize minio client when ready
        self.logger.warning("MinIOProvider is prepared but not fully implemented")
    
    def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        raise NotImplementedError("MinIOProvider not yet implemented")
    
    def download(self, key: str) -> Optional[BinaryIO]:
        raise NotImplementedError("MinIOProvider not yet implemented")
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError("MinIOProvider not yet implemented")
    
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError("MinIOProvider not yet implemented")
    
    def exists(self, key: str) -> bool:
        raise NotImplementedError("MinIOProvider not yet implemented")
