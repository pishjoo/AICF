# Storage Architecture

## Overview

AICF v2 implements a storage abstraction layer to support multiple backend providers for asset storage. This enables flexibility in deployment scenarios from local development to enterprise cloud infrastructure.

## Current Implementation

### Module Structure

```
app/storage/
├── __init__.py       # Module exports
└── providers.py      # StorageProvider interface and implementations
```

### Provider Types

```python
class StorageProviderType(str, Enum):
    LOCAL = "local"              # Local filesystem
    S3 = "s3"                    # AWS S3
    CLOUDFLARE_R2 = "cloudflare_r2"  # Cloudflare R2
    MINIO = "minio"              # MinIO (self-hosted S3-compatible)
```

### Core Interface

```python
class StorageProvider(ABC):
    """Abstract base class for all storage providers."""
    
    @abstractmethod
    def upload(file: BinaryIO, key: str, content_type: str = None, 
               metadata: dict = None) -> UploadResult:
        pass
    
    @abstractmethod
    def download(key: str) -> Optional[BinaryIO]:
        pass
    
    @abstractmethod
    def delete(key: str) -> bool:
        pass
    
    @abstractmethod
    def get_url(key: str, expires_in: int = 3600) -> str:
        pass
    
    @abstractmethod
    def exists(key: str) -> bool:
        pass
```

### Data Structures

#### StorageMetadata

```python
@dataclass
class StorageMetadata:
    filename: str
    content_type: Optional[str] = None
    file_size_bytes: int = 0
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
```

#### UploadResult

```python
@dataclass
class UploadResult:
    success: bool
    storage_key: str          # Unique identifier
    storage_url: str          # Access URL
    provider: StorageProviderType
    metadata: StorageMetadata
    error: Optional[str] = None
```

## Implemented Providers

### LocalStorageProvider

**Status**: ✅ Fully Implemented

Stores files on the local filesystem.

```python
provider = LocalStorageProvider(base_path="/tmp/aicf_storage")

result = provider.upload(
    file=file_object,
    key="org_1/episode_5/script.txt",
    content_type="text/plain",
    metadata={"stage": "script"}
)

print(result.storage_url)  # file:///tmp/aicf_storage/org_1/episode_5/script.txt
```

**Features**:
- Automatic directory creation based on key structure
- MD5 and SHA256 checksum calculation
- Metadata stored in sidecar `.meta` files
- No external dependencies

**Limitations**:
- Single server only
- No redundancy
- Not suitable for production at scale

### S3StorageProvider

**Status**: 🟡 Prepared (Not Implemented)

AWS S3 integration ready for implementation.

```python
provider = S3StorageProvider(
    bucket="aicf-assets",
    region="us-east-1"
)
```

**To Implement**:
1. Install boto3: `pip install boto3`
2. Configure AWS credentials (env vars or IAM role)
3. Implement methods using boto3 S3 client

### CloudflareR2Provider

**Status**: 🟡 Prepared (Not Implemented)

Cloudflare R2 is S3-compatible with no egress fees.

```python
provider = CloudflareR2Provider(
    bucket="aicf-assets",
    account_id="your_account_id",
    access_key_id="R2_ACCESS_KEY",
    secret_access_key="R2_SECRET_KEY"
)
```

**Benefits over S3**:
- No egress fees
- Lower cost for high-volume storage
- Global edge network

### MinIOProvider

**Status**: 🟡 Prepared (Not Implemented)

MinIO is self-hosted S3-compatible object storage.

```python
provider = MinIOProvider(
    bucket="aicf-assets",
    endpoint="minio.internal:9000",
    access_key="minio_admin",
    secret_key="minio_secret",
    secure=True
)
```

**Use Cases**:
- On-premises deployments
- Private cloud infrastructure
- Air-gapped environments

## Design Decisions

### 1. Abstraction Over Specific Providers

**Decision**: Define common interface with provider-specific implementations.

**Rationale**:
- Swap providers without code changes
- Test with local storage, deploy to cloud
- Support hybrid deployments
- Future-proof for new providers (GCS, Azure Blob)

### 2. Key-Based Addressing

**Decision**: Use hierarchical keys like `org_id/episode_id/asset_type/filename`.

**Rationale**:
- Natural tenant isolation
- Easy lifecycle management by prefix
- Compatible with all object stores
- Enables efficient listing/filtering

### 3. Checksum Verification

**Decision**: Calculate MD5 and SHA256 during upload.

**Rationale**:
- Detect corruption
- Verify uploads
- Support integrity checks
- Compliance requirements

### 4. Metadata Sidecar Files (Local)

**Decision**: Store metadata in separate `.meta` files for local provider.

**Rationale**:
- Simple implementation
- Human-readable
- No database dependency
- Object stores handle this natively

### 5. URL Generation

**Decision**: Provide `get_url()` method with expiry support.

**Rationale**:
- Signed URLs for private assets
- Configurable expiration
- Consistent interface across providers
- CDN integration ready

## Database Integration

### Asset Model Updates

```sql
-- New columns for storage tracking
ALTER TABLE assets ADD COLUMN storage_key VARCHAR(255);
ALTER TABLE assets ADD COLUMN metadata JSON DEFAULT '{}';
CREATE INDEX idx_asset_storage_key ON assets(storage_key);
```

### Usage Pattern

```python
# Upload asset
storage_result = storage_provider.upload(
    file=generated_video,
    key=f"org_{org_id}/ep_{episode_id}/video.mp4",
    content_type="video/mp4",
    metadata={
        "agent_execution_id": execution.id,
        "stage": "video_production",
        "duration_seconds": 120.5
    }
)

# Update database
asset = Asset(
    episode_id=episode_id,
    organization_id=org_id,
    asset_type=AssetType.VIDEO,
    filename="video.mp4",
    storage_provider=storage_result.provider.value,
    storage_key=storage_result.storage_key,
    storage_url=storage_result.storage_url,
    file_size_bytes=storage_result.metadata.file_size_bytes,
    metadata=storage_result.metadata.to_dict()
)
db.add(asset)
db.commit()
```

## Future Scaling Approach

### Phase 1: Current (Local Storage)

- Single server deployment
- Development and testing
- Limited by disk space

### Phase 2: Single Cloud Provider (S3/R2)

```
┌─────────────┐
│ Application │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   S3/R2     │
│   Bucket    │
└─────────────┘
```

- Production-ready
- Unlimited scale
- Built-in redundancy
- CDN integration

### Phase 3: Multi-Provider Strategy

```
┌─────────────┐
│ Application │
└──────┬──────┘
       │
   ┌───┴───┐
   ▼       ▼
┌─────┐ ┌─────┐
│ S3  │ │ R2  │  (Active-Active or Active-Passive)
└─────┘ └─────┘
```

**Benefits**:
- Vendor lock-in avoidance
- Cost optimization
- Geographic distribution
- Disaster recovery

### Phase 4: Intelligent Routing

```python
class SmartStorageRouter:
    def select_provider(self, asset_type: str, size: int) -> StorageProvider:
        if asset_type == "thumbnail" and size < 1024 * 1024:
            return self.r2_provider  # Cheap for small files
        elif asset_type == "video":
            return self.s3_provider  # Better video tools
        else:
            return self.default_provider
```

### Phase 5: Edge Caching

```
┌─────────────┐     ┌─────────┐
│ Application │────▶│   CDN   │
└─────────────┘     └────┬────┘
                         │
                   ┌─────┴─────┐
                   ▼           ▼
              ┌────────┐ ┌────────┐
              │ Origin │ │ Origin │
              │  S3    │ │  R2    │
              └────────┘ └────────┘
```

- Reduced latency
- Lower origin costs
- Better user experience

## Security Considerations

### 1. Access Control

- IAM roles for cloud providers
- Service accounts with minimal permissions
- Regular credential rotation

### 2. Encryption

- At-rest encryption (provider-managed or customer keys)
- In-transit encryption (TLS)
- Client-side encryption for sensitive data

### 3. Signed URLs

```python
# Generate time-limited access URL
url = provider.get_url(
    key="private/asset.mp4",
    expires_in=3600  # 1 hour
)
```

### 4. Audit Logging

```python
logger.info(f"Upload: {key} ({size} bytes) to {provider.provider_type}")
logger.info(f"Download: {key} by user {user_id}")
logger.info(f"Delete: {key} by user {user_id}")
```

## Cost Optimization

### Storage Tiering

| Provider | Standard | IA | Archive |
|----------|----------|-----|---------|
| S3 | $0.023/GB | $0.0125/GB | $0.004/GB |
| R2 | $0.015/GB | N/A | N/A |
| MinIO | Hardware cost | N/A | N/A |

### Recommendations

1. **Thumbnails/Small Assets**: Use R2 (no egress fees)
2. **Video Files**: Use S3 with CloudFront (better streaming)
3. **Archived Content**: Move to S3 Glacier after 90 days
4. **Hot Assets**: Cache at edge (CDN)

### Lifecycle Policies

```python
# Example S3 lifecycle configuration
lifecycle_rules = [
    {
        "id": "archive-old-videos",
        "filter": {"prefix": "videos/"},
        "transitions": [
            {"days": 90, "storage_class": "GLACIER"}
        ],
        "expiration": {"days": 730}  # Delete after 2 years
    }
]
```

## Testing Strategy

### Unit Tests

```python
def test_local_storage_upload(tmp_path):
    provider = LocalStorageProvider(base_path=str(tmp_path))
    
    result = provider.upload(
        file=io.BytesIO(b"test content"),
        key="test/file.txt"
    )
    
    assert result.success
    assert result.storage_key == "test/file.txt"
    assert result.metadata.file_size_bytes == 12
```

### Integration Tests

```python
@pytest.mark.integration
def test_s3_upload():
    provider = S3StorageProvider(bucket="test-bucket")
    
    result = provider.upload(
        file=io.BytesIO(b"test"),
        key="integration/test.txt"
    )
    
    assert result.success
    assert provider.exists("integration/test.txt")
```

### Mock Provider for Testing

```python
class MockStorageProvider(StorageProvider):
    def __init__(self):
        self.files = {}
    
    def upload(self, file, key, **kwargs):
        self.files[key] = file.read()
        return UploadResult.success_result(...)
    
    def download(self, key):
        return io.BytesIO(self.files.get(key))
    
    # ... other methods
```

## Migration Path

### From Local to Cloud

1. **Assessment**: Identify all assets and their sizes
2. **Provider Selection**: Choose target provider (S3, R2, etc.)
3. **Bulk Upload**: Migrate existing assets
4. **Update References**: Change storage URLs in database
5. **Switch Configuration**: Update provider factory
6. **Cleanup**: Remove local copies after verification

### Code Changes Required

```python
# Before (hardcoded local)
storage = LocalStorageProvider("/var/aicf/assets")

# After (configurable)
from core.config import settings

storage = create_storage_provider(settings.STORAGE_PROVIDER_TYPE)
# Returns appropriate provider based on config
```

## Monitoring

### Metrics to Track

1. **Storage Growth**
   - Total bytes stored
   - Files count by type
   - Growth rate per day

2. **Performance**
   - Upload latency (P50, P95, P99)
   - Download latency
   - Error rate by operation

3. **Cost**
   - Monthly storage cost
   - Egress charges
   - API request costs

### Alerts

- Storage approaching quota
- Unusual egress patterns
- High error rates
- Failed uploads exceeding threshold
