"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileImage, FileAudio2, FileVideo, File } from "lucide-react";

const mockMediaItems = [
  { id: 1, filename: "hero-banner.png", type: "image", size: "2.4 MB", date: "2024-01-20" },
  { id: 2, filename: "podcast-ep01.mp3", type: "audio", size: "15.8 MB", date: "2024-01-19" },
  { id: 3, filename: "product-demo.mp4", type: "video", size: "128.5 MB", date: "2024-01-18" },
  { id: 4, filename: "logo-dark.svg", type: "image", size: "45 KB", date: "2024-01-17" },
  { id: 5, filename: "background-music.wav", type: "audio", size: "42.1 MB", date: "2024-01-16" },
  { id: 6, filename: "tutorial-intro.mp4", type: "video", size: "89.3 MB", date: "2024-01-15" },
];

function getAssetIcon(type: string) {
  switch (type) {
    case "image":
      return <FileImage className="w-8 h-8 text-blue-500" />;
    case "audio":
      return <FileAudio2 className="w-8 h-8 text-purple-500" />;
    case "video":
      return <FileVideo className="w-8 h-8 text-red-500" />;
    default:
      return <File className="w-8 h-8 text-gray-500" />;
  }
}

export function MediaGrid() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {mockMediaItems.map((item) => (
        <Card key={item.id} className="hover:shadow-md transition-shadow cursor-pointer">
          <CardContent className="p-4">
            <div className="flex flex-col items-center text-center space-y-3">
              {getAssetIcon(item.type)}
              <div className="space-y-1">
                <p className="text-sm font-medium text-gray-900 line-clamp-1">
                  {item.filename}
                </p>
                <div className="flex items-center justify-center gap-2">
                  <Badge variant="secondary" className="text-xs">
                    {item.type}
                  </Badge>
                  <span className="text-xs text-gray-500">{item.size}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
