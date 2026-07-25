"use client";

import { useParams } from "next/navigation";
import { MediaPreview, type MediaAssetDetail } from "@/components/media/detail/MediaPreview";
import { AssetInfoCard } from "@/components/media/detail/AssetInfoCard";
import { MetadataPanel } from "@/components/media/detail/MetadataPanel";
import { TagsPanel } from "@/components/media/detail/TagsPanel";
import { Card, CardContent } from "@/components/ui/card";

const mockMediaAssets: Record<string, MediaAssetDetail> = {
  '1': {
    id: '1',
    filename: 'hero-banner.png',
    type: 'image',
    size: 2516582,
    status: 'ready',
    createdAt: '2024-01-20T10:30:00Z',
    dimensions: { width: 1920, height: 1080 },
    uploadedBy: 'Alice Brown',
    tags: ['banner', 'hero', 'marketing'],
  },
  '2': {
    id: '2',
    filename: 'podcast-ep01.mp3',
    type: 'audio',
    size: 16567500,
    status: 'ready',
    createdAt: '2024-01-19T14:00:00Z',
    duration: 1845,
    codec: 'MP3',
    uploadedBy: 'Bob Wilson',
    tags: ['podcast', 'audio', 'episode-1'],
  },
  '3': {
    id: '3',
    filename: 'product-demo.mp4',
    type: 'video',
    size: 134758400,
    status: 'processing',
    createdAt: '2024-01-18T09:15:00Z',
    dimensions: { width: 1920, height: 1080 },
    duration: 245,
    codec: 'H.264',
    uploadedBy: 'Sarah Johnson',
    tags: ['demo', 'product', 'video'],
  },
  '4': {
    id: '4',
    filename: 'logo-dark.svg',
    type: 'image',
    size: 46080,
    status: 'ready',
    createdAt: '2024-01-17T11:45:00Z',
    dimensions: { width: 512, height: 512 },
    uploadedBy: 'John Smith',
    tags: ['logo', 'branding'],
  },
  '5': {
    id: '5',
    filename: 'background-music.wav',
    type: 'audio',
    size: 44146688,
    status: 'ready',
    createdAt: '2024-01-16T16:20:00Z',
    duration: 312,
    codec: 'WAV',
    uploadedBy: 'Alice Brown',
    tags: ['music', 'background', 'audio'],
  },
};

export function getMediaAssetDetail(id: string): MediaAssetDetail | undefined {
  return mockMediaAssets[id];
}

export default function MediaAssetDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const asset = getMediaAssetDetail(id);

  if (!asset) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Media Asset Details</h1>
          <p className="text-gray-500 mt-1">View detailed information about your media assets</p>
        </div>
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center justify-center text-center space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Asset Not Found</h2>
              <p className="text-sm text-gray-500 max-w-md">
                The media asset you&apos;re looking for doesn&apos;t exist or has been removed.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Media Asset Details</h1>
        <p className="text-gray-500 mt-1">View detailed information about your media assets</p>
      </div>

      <div className="space-y-6">
        <MediaPreview asset={asset} />
        <AssetInfoCard asset={asset} />
        <MetadataPanel asset={asset} />
        <TagsPanel asset={asset} />
      </div>
    </div>
  );
}
