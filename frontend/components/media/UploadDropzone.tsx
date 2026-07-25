"use client";

import { Upload, Image, Music, Video } from "lucide-react";
import { cn } from "@/lib/utils";

export function UploadDropzone() {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg transition-colors cursor-pointer",
        "border-gray-300 bg-gray-50 hover:bg-gray-100 hover:border-blue-400"
      )}
    >
      <div className="flex items-center justify-center w-16 h-16 mb-4 rounded-full bg-white shadow-sm">
        <Upload className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-700">Drag & Drop Files</h3>
      <p className="text-sm text-gray-500 mt-1">or click to browse</p>
      <div className="flex items-center gap-4 mt-4 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <Image className="w-3 h-3" /> Images
        </span>
        <span className="flex items-center gap-1">
          <Music className="w-3 h-3" /> Audio
        </span>
        <span className="flex items-center gap-1">
          <Video className="w-3 h-3" /> Video
        </span>
      </div>
    </div>
  );
}
