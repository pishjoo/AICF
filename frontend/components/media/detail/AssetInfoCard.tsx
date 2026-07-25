import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { MediaAssetDetail } from './MediaPreview';

interface AssetInfoCardProps {
  asset: MediaAssetDetail;
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getStatusVariant = (status: MediaAssetDetail['status']): 'default' | 'secondary' | 'destructive' | 'outline' => {
  switch (status) {
    case 'ready':
      return 'default';
    case 'processing':
      return 'secondary';
    case 'error':
      return 'destructive';
    case 'pending':
      return 'outline';
    default:
      return 'outline';
  }
};

export function AssetInfoCard({ asset }: AssetInfoCardProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Asset Information</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Filename</p>
            <p className="text-sm font-medium truncate">{asset.filename}</p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Type</p>
            <Badge variant="secondary" className="capitalize">
              {asset.type}
            </Badge>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Size</p>
            <p className="text-sm font-medium">{formatFileSize(asset.size)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Status</p>
            <Badge variant={getStatusVariant(asset.status)} className="capitalize">
              {asset.status}
            </Badge>
          </div>
          <div className="col-span-2 space-y-1">
            <p className="text-sm text-muted-foreground">Created</p>
            <p className="text-sm font-medium">{formatDate(asset.createdAt)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
