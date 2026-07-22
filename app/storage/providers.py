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
    AWS S3 storage provider for production use.
    
    Implements all StorageProvider methods using boto3.
    Supports organization isolation through key prefixes.
    """
    
    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        organization_prefix: str = ""
    ):
        super().__init__(StorageProviderType.S3)
        
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            self.boto3 = boto3
            self.ClientError = ClientError
            self.NoCredentialsError = NoCredentialsError
        except ImportError:
            raise ImportError("boto3 is required for S3StorageProvider. Install with: pip install boto3")
        
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url
        self.organization_prefix = organization_prefix
        
        # Initialize S3 client
        self.client = self.boto3.client(
            's3',
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )
        
        self.logger.info(f"S3StorageProvider initialized for bucket '{bucket}' in region '{region}'")
    
    def _get_key(self, key: str) -> str:
        """Add organization prefix to key for isolation."""
        if self.organization_prefix:
            return f"{self.organization_prefix}/{key}"
        return key
    
    def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        try:
            s3_key = self._get_key(key)
            
            # Calculate checksums before upload
            md5_sum, sha256_sum = self._calculate_checksums(file)
            
            # Get file size
            current_pos = file.tell()
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(current_pos)
            
            # Prepare upload arguments
            upload_args = {
                'Bucket': self.bucket,
                'Key': s3_key,
                'Body': file
            }
            
            if content_type:
                upload_args['ContentType'] = content_type
            
            if metadata:
                upload_args['Metadata'] = {str(k): str(v) for k, v in metadata.items()}
            
            # Upload to S3
            self.client.upload_fileobj(**upload_args)
            
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
            
            # Generate URL
            storage_url = f"s3://{self.bucket}/{s3_key}"
            
            self.logger.info(f"Uploaded file to S3: {s3_key} ({file_size} bytes)")
            
            return UploadResult.success_result(
                storage_key=s3_key,
                storage_url=storage_url,
                provider=StorageProviderType.S3,
                metadata=storage_metadata
            )
            
        except self.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = f"S3 upload failed: {error_code} - {str(e)}"
            self.logger.exception(error_msg)
            return UploadResult.failure_result(error_msg, StorageProviderType.S3)
        except Exception as e:
            error_msg = f"Unexpected upload error: {str(e)}"
            self.logger.exception(error_msg)
            return UploadResult.failure_result(error_msg, StorageProviderType.S3)
    
    def download(self, key: str) -> Optional[BinaryIO]:
        try:
            import io
            s3_key = self._get_key(key)
            
            # Download file to BytesIO
            buffer = io.BytesIO()
            self.client.download_fileobj(self.bucket, s3_key, buffer)
            buffer.seek(0)
            
            self.logger.debug(f"Downloaded file from S3: {s3_key}")
            return buffer
            
        except self.ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                self.logger.warning(f"File not found in S3: {s3_key}")
                return None
            error_msg = f"S3 download failed: {str(e)}"
            self.logger.exception(error_msg)
            return None
        except Exception as e:
            error_msg = f"Unexpected download error: {str(e)}"
            self.logger.exception(error_msg)
            return None
    
    def delete(self, key: str) -> bool:
        try:
            s3_key = self._get_key(key)
            
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            
            self.logger.info(f"Deleted file from S3: {s3_key}")
            return True
            
        except self.ClientError as e:
            error_msg = f"S3 delete failed: {str(e)}"
            self.logger.exception(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected delete error: {str(e)}"
            self.logger.exception(error_msg)
            return False
    
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            s3_key = self._get_key(key)
            
            # Check if file exists first
            if not self.exists(key):
                raise FileNotFoundError(f"File not found: {key}")
            
            # Generate presigned URL
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            
            self.logger.debug(f"Generated presigned URL for {s3_key} (expires in {expires_in}s)")
            return url
            
        except FileNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to generate URL: {str(e)}"
            self.logger.exception(error_msg)
            raise
    
    def exists(self, key: str) -> bool:
        try:
            s3_key = self._get_key(key)
            
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
            
        except self.ClientError as e:
            if e.response.get('Error', {}).get('Code') in ['404', 'NoSuchKey']:
                return False
            error_msg = f"S3 exists check failed: {str(e)}"
            self.logger.exception(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected exists check error: {str(e)}"
            self.logger.exception(error_msg)
            return False


class CloudflareR2Provider(StorageProvider):
    """
    Cloudflare R2 storage provider for production use.
    
    R2 is S3-compatible, so we use boto3 with R2 endpoint.
    Supports organization isolation through key prefixes.
    """
    
    def __init__(
        self,
        bucket: str,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "auto",
        organization_prefix: str = ""
    ):
        super().__init__(StorageProviderType.CLOUDFLARE_R2)
        
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            self.boto3 = boto3
            self.ClientError = ClientError
            self.NoCredentialsError = NoCredentialsError
        except ImportError:
            raise ImportError("boto3 is required for CloudflareR2Provider. Install with: pip install boto3")
        
        self.bucket = bucket
        self.account_id = account_id
        self.endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        self.organization_prefix = organization_prefix
        
        # Initialize S3-compatible client for R2
        self.client = self.boto3.client(
            's3',
            region_name=region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )
        
        self.logger.info(f"CloudflareR2Provider initialized for bucket '{bucket}'")
    
    def _get_key(self, key: str) -> str:
        """Add organization prefix to key for isolation."""
        if self.organization_prefix:
            return f"{self.organization_prefix}/{key}"
        return key
    
    def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        try:
            r2_key = self._get_key(key)
            
            # Calculate checksums
            md5_sum, sha256_sum = self._calculate_checksums(file)
            
            # Get file size
            current_pos = file.tell()
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(current_pos)
            
            # Prepare upload arguments
            upload_args = {
                'Bucket': self.bucket,
                'Key': r2_key,
                'Body': file
            }
            
            if content_type:
                upload_args['ContentType'] = content_type
            
            if metadata:
                upload_args['Metadata'] = {str(k): str(v) for k, v in metadata.items()}
            
            # Upload to R2
            self.client.upload_fileobj(**upload_args)
            
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
            
            # Generate URL (R2 public URL pattern)
            storage_url = f"https://pub-{self.account_id}.r2.cloudflarestorage.com/{self.bucket}/{r2_key}"
            
            self.logger.info(f"Uploaded file to R2: {r2_key} ({file_size} bytes)")
            
            return UploadResult.success_result(
                storage_key=r2_key,
                storage_url=storage_url,
                provider=StorageProviderType.CLOUDFLARE_R2,
                metadata=storage_metadata
            )
            
        except self.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = f"R2 upload failed: {error_code} - {str(e)}"
            self.logger.exception(error_msg)
            return UploadResult.failure_result(error_msg, StorageProviderType.CLOUDFLARE_R2)
        except Exception as e:
            error_msg = f"Unexpected upload error: {str(e)}"
            self.logger.exception(error_msg)
            return UploadResult.failure_result(error_msg, StorageProviderType.CLOUDFLARE_R2)
    
    def download(self, key: str) -> Optional[BinaryIO]:
        try:
            import io
            r2_key = self._get_key(key)
            
            buffer = io.BytesIO()
            self.client.download_fileobj(self.bucket, r2_key, buffer)
            buffer.seek(0)
            
            self.logger.debug(f"Downloaded file from R2: {r2_key}")
            return buffer
            
        except self.ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                self.logger.warning(f"File not found in R2: {r2_key}")
                return None
            error_msg = f"R2 download failed: {str(e)}"
            self.logger.exception(error_msg)
            return None
        except Exception as e:
            error_msg = f"Unexpected download error: {str(e)}"
            self.logger.exception(error_msg)
            return None
    
    def delete(self, key: str) -> bool:
        try:
            r2_key = self._get_key(key)
            
            self.client.delete_object(Bucket=self.bucket, Key=r2_key)
            
            self.logger.info(f"Deleted file from R2: {r2_key}")
            return True
            
        except self.ClientError as e:
            error_msg = f"R2 delete failed: {str(e)}"
            self.logger.exception(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected delete error: {str(e)}"
            self.logger.exception(error_msg)
            return False
    
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            r2_key = self._get_key(key)
            
            if not self.exists(key):
                raise FileNotFoundError(f"File not found: {key}")
            
            # Generate presigned URL (R2 supports S3-compatible presigned URLs)
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': r2_key},
                ExpiresIn=expires_in
            )
            
            self.logger.debug(f"Generated presigned URL for {r2_key}")
            return url
            
        except FileNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to generate URL: {str(e)}"
            self.logger.exception(error_msg)
            raise
    
    def exists(self, key: str) -> bool:
        try:
            r2_key = self._get_key(key)
            
            self.client.head_object(Bucket=self.bucket, Key=r2_key)
            return True
            
        except self.ClientError as e:
            if e.response.get('Error', {}).get('Code') in ['404', 'NoSuchKey']:
                return False
            error_msg = f"R2 exists check failed: {str(e)}"
            self.logger.exception(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected exists check error: {str(e)}"
            self.logger.exception(error_msg)
            return False


class MinIOProvider(StorageProvider):
    """
    MinIO storage provider for private cloud deployments.
    
    MinIO is S3-compatible, so we use boto3 with MinIO endpoint.
    Supports organization isolation through buckets or key prefixes.
    """
    
    def __init__(
        self,
        bucket: str,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
        region: str = "us-east-1",
        organization_prefix: str = ""
    ):
        super().__init__(StorageProviderType.MINIO)
        
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            self.boto3 = boto3
            self.ClientError = ClientError
            self.NoCredentialsError = NoCredentialsError
        except ImportError:
            raise ImportError("boto3 is required for MinIOProvider. Install with: pip install boto3")
        
        self.bucket = bucket
        self.endpoint = endpoint
        self.secure = secure
        self.region = region
        self.organization_prefix = organization_prefix
        
        # Build endpoint URL
        protocol = "https" if secure else "http"
        self.endpoint_url = f"{protocol}://{endpoint}"
        
        # Initialize S3-compatible client for MinIO
        self.client = self.boto3.client(
            's3',
            region_name=region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        self.logger.info(f"MinIOProvider initialized for bucket '{bucket}' at '{self.endpoint_url}'")
    
    def _get_key(self, key: str) -> str:
        """Add organization prefix to key for isolation."""
        if self.organization_prefix:
            return f"{self.organization_prefix}/{key}"
        return key
    
    def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        try:
            minio_key = self._get_key(key)
            
            # Calculate checksums
            md5_sum, sha256_sum = self._calculate_checksums(file)
            
            # Get file size
            current_pos = file.tell()
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(current_pos)
            
            # Prepare upload arguments
            upload_args = {
                'Bucket': self.bucket,
                'Key': minio_key,
                'Body': file
            }
            
            if content_type:
                upload_args['ContentType'] = content_type
            
            if metadata:
                upload_args['Metadata'] = {str(k): str(v) for k, v in metadata.items()}
            
            # Upload to MinIO
            self.client.upload_fileobj(**upload_args)
            
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
            
            # Generate URL
            storage_url = f"{self.endpoint_url}/{self.bucket}/{minio_key}"
            
            self.logger.info(f"Uploaded file to MinIO: {minio_key} ({file_size} bytes)")
            
            return UploadResult.success_result(
                storage_key=minio_key,
                storage_url=storage_url,
                provider=StorageProviderType.MINIO,
                metadata=storage_metadata
            )
            
        except self.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = f"MinIO upload failed: {error_code} - {str(e)}"
            self.logger.exception(error_msg)
            return UploadResult.failure_result(error_msg, StorageProviderType.MINIO)
        except Exception as e:
            error_msg = f"Unexpected upload error: {str(e)}"
            self.logger.exception(error_msg)
            return UploadResult.failure_result(error_msg, StorageProviderType.MINIO)
    
    def download(self, key: str) -> Optional[BinaryIO]:
        try:
            import io
            minio_key = self._get_key(key)
            
            buffer = io.BytesIO()
            self.client.download_fileobj(self.bucket, minio_key, buffer)
            buffer.seek(0)
            
            self.logger.debug(f"Downloaded file from MinIO: {minio_key}")
            return buffer
            
        except self.ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                self.logger.warning(f"File not found in MinIO: {minio_key}")
                return None
            error_msg = f"MinIO download failed: {str(e)}"
            self.logger.exception(error_msg)
            return None
        except Exception as e:
            error_msg = f"Unexpected download error: {str(e)}"
            self.logger.exception(error_msg)
            return None
    
    def delete(self, key: str) -> bool:
        try:
            minio_key = self._get_key(key)
            
            self.client.delete_object(Bucket=self.bucket, Key=minio_key)
            
            self.logger.info(f"Deleted file from MinIO: {minio_key}")
            return True
            
        except self.ClientError as e:
            error_msg = f"MinIO delete failed: {str(e)}"
            self.logger.exception(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected delete error: {str(e)}"
            self.logger.exception(error_msg)
            return False
    
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            minio_key = self._get_key(key)
            
            if not self.exists(key):
                raise FileNotFoundError(f"File not found: {key}")
            
            # For MinIO, return direct URL (presigned URLs also supported)
            storage_url = f"{self.endpoint_url}/{self.bucket}/{minio_key}"
            
            self.logger.debug(f"Generated URL for {minio_key}")
            return storage_url
            
        except FileNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to generate URL: {str(e)}"
            self.logger.exception(error_msg)
            raise
    
    def exists(self, key: str) -> bool:
        try:
            minio_key = self._get_key(key)
            
            self.client.head_object(Bucket=self.bucket, Key=minio_key)
            return True
            
        except self.ClientError as e:
            if e.response.get('Error', {}).get('Code') in ['404', 'NoSuchKey']:
                return False
            error_msg = f"MinIO exists check failed: {str(e)}"
            self.logger.exception(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected exists check error: {str(e)}"
            self.logger.exception(error_msg)
            return False
