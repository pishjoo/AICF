export interface MediaMetadata {
  dimensions?: {
    width: number;
    height: number;
  };
  duration?: number;
  codec?: string;
  createdAt: string;
  uploadedBy: string;
}

export type MediaType = 'image' | 'video' | 'audio' | 'document';

export type MediaStatus = 'pending' | 'processing' | 'ready' | 'failed';

export interface MediaAssetDetail {
  id: string;
  filename: string;
  type: MediaType;
  status: MediaStatus;
  size: number;
  url: string;
  thumbnail?: string;
  metadata: MediaMetadata;
  tags: string[];
}
