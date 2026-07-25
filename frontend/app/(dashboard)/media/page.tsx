"use client";

import { MediaFilters } from "@/components/media/MediaFilters";
import { MediaGrid } from "@/components/media/MediaGrid";

export default function MediaPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Media Library</h1>
        <p className="text-gray-500 mt-1">Manage and organize your generated media assets.</p>
      </div>

      {/* Filters */}
      <MediaFilters />

      {/* Media Grid */}
      <MediaGrid />
    </div>
  );
}
