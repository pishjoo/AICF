import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { MediaAssetDetail } from './MediaPreview';

interface MetadataPanelProps {
  asset: MediaAssetDetail;
}

const formatDuration = (seconds?: number): string => {
  if (!seconds) return 'N/A';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export function MetadataPanel({ asset }: MetadataPanelProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Technical Metadata</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Dimensions</p>
            <p className="text-sm font-medium">
              {asset.dimensions
                ? `${asset.dimensions.width} x ${asset.dimensions.height}`
                : 'N/A'}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Duration</p>
            <p className="text-sm font-medium">{formatDuration(asset.duration)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Codec</p>
            <p className="text-sm font-medium">{asset.codec || 'N/A'}</p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Uploaded By</p>
            <p className="text-sm font-medium">{asset.uploadedBy || 'Unknown'}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
