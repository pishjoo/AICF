"""
Rendering Storage Extensions

Extended storage support for:
- Video files
- Thumbnails
- Subtitles
- Intermediate render files

With checksum validation, metadata tracking, and tenant isolation.
"""

import logging
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
from datetime import datetime, timezone

from app.storage.providers import (
    StorageProvider,
    StorageMetadata,
    UploadResult,
    StorageProviderType,
)


logger = logging.getLogger(__name__)


class RenderingStorageService:
    """
    Storage service specialized for rendering assets.
    
    Provides organization-isolated storage paths and metadata tracking
    for video production assets.
    """
    
    def __init__(self, storage_provider: StorageProvider):
        self.provider = storage_provider
        self.logger = logging.getLogger(f"{__name__}.service")
    
    def _build_storage_key(
        self,
        organization_id: int,
        asset_type: str,
        filename: str,
        episode_id: Optional[int] = None,
        job_id: Optional[int] = None
    ) -> str:
        """
        Build tenant-isolated storage key.
        
        Format: org_{id}/[episode_{eid}/][job_{jid}/]{type}/{filename}
        """
        parts = [f"org_{organization_id}"]
        
        if episode_id:
            parts.append(f"episode_{episode_id}")
        
        if job_id:
            parts.append(f"job_{job_id}")
        
        parts.append(asset_type)
        parts.append(filename)
        
        return "/".join(parts)
    
    def upload_video(
        self,
        file: BinaryIO,
        organization_id: int,
        filename: str,
        episode_id: Optional[int] = None,
        job_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """Upload a video file with tenant isolation."""
        storage_key = self._build_storage_key(
            organization_id=organization_id,
            asset_type="videos",
            filename=filename,
            episode_id=episode_id,
            job_id=job_id
        )
        
        # Add video-specific metadata
        enhanced_metadata = metadata or {}
        enhanced_metadata["asset_type"] = "video"
        enhanced_metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
        
        result = self.provider.upload(
            file=file,
            key=storage_key,
            content_type="video/mp4",  # Default, can be overridden
            metadata=enhanced_metadata
        )
        
        if result.success:
            self.logger.info(
                f"Uploaded video {storage_key} for org {organization_id}"
            )
        
        return result
    
    def upload_thumbnail(
        self,
        file: BinaryIO,
        organization_id: int,
        filename: str,
        episode_id: Optional[int] = None,
        job_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """Upload a thumbnail image with tenant isolation."""
        storage_key = self._build_storage_key(
            organization_id=organization_id,
            asset_type="thumbnails",
            filename=filename,
            episode_id=episode_id,
            job_id=job_id
        )
        
        enhanced_metadata = metadata or {}
        enhanced_metadata["asset_type"] = "thumbnail"
        enhanced_metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
        
        result = self.provider.upload(
            file=file,
            key=storage_key,
            content_type="image/jpeg",
            metadata=enhanced_metadata
        )
        
        if result.success:
            self.logger.info(
                f"Uploaded thumbnail {storage_key} for org {organization_id}"
            )
        
        return result
    
    def upload_subtitle(
        self,
        file: BinaryIO,
        organization_id: int,
        filename: str,
        episode_id: Optional[int] = None,
        job_id: Optional[int] = None,
        language: str = "en",
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """Upload a subtitle file with tenant isolation."""
        storage_key = self._build_storage_key(
            organization_id=organization_id,
            asset_type=f"subtitles/{language}",
            filename=filename,
            episode_id=episode_id,
            job_id=job_id
        )
        
        enhanced_metadata = metadata or {}
        enhanced_metadata["asset_type"] = "subtitle"
        enhanced_metadata["language"] = language
        enhanced_metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
        
        # Detect content type based on extension
        content_type = "text/vtt"
        if filename.endswith(".srt"):
            content_type = "application/x-subrip"
        elif filename.endswith(".ass"):
            content_type = "text/x-ssa"
        
        result = self.provider.upload(
            file=file,
            key=storage_key,
            content_type=content_type,
            metadata=enhanced_metadata
        )
        
        if result.success:
            self.logger.info(
                f"Uploaded subtitle {storage_key} for org {organization_id}"
            )
        
        return result
    
    def upload_intermediate(
        self,
        file: BinaryIO,
        organization_id: int,
        filename: str,
        job_id: int,
        intermediate_type: str = "frame",
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """Upload an intermediate render file with tenant isolation."""
        storage_key = self._build_storage_key(
            organization_id=organization_id,
            asset_type=f"intermediates/{intermediate_type}",
            filename=filename,
            job_id=job_id
        )
        
        enhanced_metadata = metadata or {}
        enhanced_metadata["asset_type"] = "intermediate"
        enhanced_metadata["intermediate_type"] = intermediate_type
        enhanced_metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
        
        result = self.provider.upload(
            file=file,
            key=storage_key,
            content_type="application/octet-stream",
            metadata=enhanced_metadata
        )
        
        if result.success:
            self.logger.info(
                f"Uploaded intermediate {storage_key} for org {organization_id}"
            )
        
        return result
    
    def get_video_url(
        self,
        organization_id: int,
        storage_key: str,
        expires_in: int = 3600
    ) -> str:
        """Get URL for a video file with tenant verification."""
        # Verify tenant isolation
        if not storage_key.startswith(f"org_{organization_id}/"):
            raise PermissionError(
                f"Access denied: Key {storage_key} does not belong to org {organization_id}"
            )
        
        return self.provider.get_url(storage_key, expires_in)
    
    def delete_asset(
        self,
        organization_id: int,
        storage_key: str
    ) -> bool:
        """Delete an asset with tenant verification."""
        # Verify tenant isolation
        if not storage_key.startswith(f"org_{organization_id}/"):
            raise PermissionError(
                f"Access denied: Key {storage_key} does not belong to org {organization_id}"
            )
        
        result = self.provider.delete(storage_key)
        
        if result:
            self.logger.info(f"Deleted asset {storage_key} for org {organization_id}")
        
        return result
    
    def verify_checksum(
        self,
        storage_key: str,
        expected_md5: Optional[str] = None,
        expected_sha256: Optional[str] = None
    ) -> bool:
        """
        Verify file checksums match expected values.
        
        Returns True if all provided checksums match.
        """
        file = self.provider.download(storage_key)
        if not file:
            self.logger.warning(f"Cannot download {storage_key} for checksum verification")
            return False
        
        try:
            # Calculate checksums
            import hashlib
            md5_hash = hashlib.md5()
            sha256_hash = hashlib.sha256()
            
            for chunk in iter(lambda: file.read(8192), b""):
                md5_hash.update(chunk)
                sha256_hash.update(chunk)
            
            calculated_md5 = md5_hash.hexdigest()
            calculated_sha256 = sha256_hash.hexdigest()
            
            # Verify
            if expected_md5 and calculated_md5 != expected_md5:
                self.logger.error(
                    f"MD5 mismatch for {storage_key}: "
                    f"expected {expected_md5}, got {calculated_md5}"
                )
                return False
            
            if expected_sha256 and calculated_sha256 != expected_sha256:
                self.logger.error(
                    f"SHA256 mismatch for {storage_key}: "
                    f"expected {expected_sha256}, got {calculated_sha256}"
                )
                return False
            
            self.logger.debug(f"Checksum verified for {storage_key}")
            return True
            
        finally:
            file.close()
    
    def get_metadata(
        self,
        storage_key: str
    ) -> Optional[Dict[str, Any]]:
        """Get metadata for a stored asset."""
        # Try to read metadata file (for local storage)
        # For cloud providers, this would use their metadata API
        path = Path(storage_key)
        metadata_path = path.with_suffix(path.suffix + ".meta")
        
        if self.provider.exists(str(metadata_path)):
            meta_file = self.provider.download(str(metadata_path))
            if meta_file:
                import json
                try:
                    return json.load(meta_file)
                finally:
                    meta_file.close()
        
        return None
