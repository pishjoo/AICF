"""
Storage Abstraction Layer

Provider interface for asset storage with support for multiple backends:
- LocalStorageProvider (implemented)
- S3Provider (prepared)
- CloudflareR2Provider (prepared)
- MinIOProvider (prepared)
"""

from .providers import (
    StorageProvider,
    LocalStorageProvider,
    StorageMetadata,
    UploadResult,
    StorageProviderType
)

__all__ = [
    "StorageProvider",
    "LocalStorageProvider",
    "StorageMetadata",
    "UploadResult",
    "StorageProviderType",
]
