"use client";

import { Upload } from "lucide-react";

export function UploadDropzone() {
  return (
    <div className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer">
      <Upload className="w-12 h-12 text-gray-400 mb-4" />
      <h3 className="text-lg font-semibold text-gray-700">Drag & Drop Files</h3>
      <p className="text-sm text-gray-500 mt-1">or click to browse</p>
      <p className="text-xs text-gray-400 mt-2">Images, Audio, Video</p>
    </div>
  );
}
