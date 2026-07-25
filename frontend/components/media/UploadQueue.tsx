"use client";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";
import { FileImage, FileAudio2, FileVideo, File } from "lucide-react";

const mockQueueItems = [
  {
    id: 1,
    filename: "hero-banner.png",
    assetType: "image" as const,
    progress: 75,
    status: "uploading",
  },
  {
    id: 2,
    filename: "podcast-ep01.mp3",
    assetType: "audio" as const,
    progress: 100,
    status: "completed",
  },
  {
    id: 3,
    filename: "product-demo.mp4",
    assetType: "video" as const,
    progress: 30,
    status: "uploading",
  },
];

function getAssetIcon(assetType: string) {
  switch (assetType) {
    case "image":
      return <FileImage className="w-5 h-5 text-blue-500" />;
    case "audio":
      return <FileAudio2 className="w-5 h-5 text-purple-500" />;
    case "video":
      return <FileVideo className="w-5 h-5 text-red-500" />;
    default:
      return <File className="w-5 h-5 text-gray-500" />;
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case "uploading":
      return (
        <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
          Uploading
        </Badge>
      );
    case "completed":
      return (
        <Badge variant="secondary" className="bg-green-100 text-green-800">
          Completed
        </Badge>
      );
    case "error":
      return (
        <Badge variant="secondary" className="bg-red-100 text-red-800">
          Error
        </Badge>
      );
    default:
      return (
        <Badge variant="secondary" className="bg-gray-100 text-gray-800">
          Pending
        </Badge>
      );
  }
}

export function UploadQueue() {
  return (
    <div className="space-y-3 mt-6">
      <h4 className="text-sm font-semibold text-gray-700">Upload Queue</h4>
      {mockQueueItems.map((item) => (
        <Card key={item.id}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                {getAssetIcon(item.assetType)}
                <span className="text-sm font-medium text-gray-900">
                  {item.filename}
                </span>
              </div>
              {getStatusBadge(item.status)}
            </div>
            <Progress value={item.progress} className="h-2" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
