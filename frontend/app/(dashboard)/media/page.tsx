"use client";

import { UploadDropzone } from "@/components/media/UploadDropzone";
import { UploadQueue } from "@/components/media/UploadQueue";
import { MediaGrid } from "@/components/media/MediaGrid";

export default function MediaPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Media Library</h1>
        <p className="text-gray-500 mt-1">Manage your images, audio, and video files</p>
      </div>

      <UploadDropzone />

      <UploadQueue />

      <MediaGrid />
    </div>
  );
}
