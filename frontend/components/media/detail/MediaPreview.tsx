import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  FileImage,
  FileVideo,
  FileAudio,
  FileText,
  File,
} from 'lucide-react';

export interface MediaAssetDetail {
  id: string;
  filename: string;
  type: 'image' | 'video' | 'audio' | 'document' | 'other';
  size: number;
  status: 'pending' | 'processing' | 'ready' | 'error';
  createdAt: string;
  dimensions?: {
    width: number;
    height: number;
  };
  duration?: number;
  codec?: string;
  uploadedBy?: string;
  tags?: string[];
}

interface MediaPreviewProps {
  asset: MediaAssetDetail;
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const getIconForType = (type: MediaAssetDetail['type']) => {
  switch (type) {
    case 'image':
      return FileImage;
    case 'video':
      return FileVideo;
    case 'audio':
      return FileAudio;
    case 'document':
      return FileText;
    default:
      return File;
  }
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

export function MediaPreview({ asset }: MediaPreviewProps) {
  const IconComponent = getIconForType(asset.type);

  return (
    <Card className="w-full">
      <CardContent className="p-6">
        <div className="flex flex-col items-center justify-center space-y-4 py-12">
          <div className="rounded-lg bg-muted p-8">
            <IconComponent className="h-24 w-24 text-muted-foreground" />
          </div>
          <div className="text-center space-y-2">
            <h3 className="text-lg font-semibold">{asset.filename}</h3>
            <div className="flex items-center justify-center gap-2">
              <Badge variant={getStatusVariant(asset.status)}>
                {asset.status}
              </Badge>
              <span className="text-sm text-muted-foreground">
                {formatFileSize(asset.size)}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
