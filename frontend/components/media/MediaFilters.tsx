"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search, Filter, Grid3X3, List, Image, Film, Music, FileText, CheckCircle, Clock, XCircle } from "lucide-react";
import type { MediaTypeFilter, MediaStatusFilter, MediaSortOption } from "@/types/media-filter";

interface MediaFiltersProps {
  onTypeChange?: (type: MediaTypeFilter) => void;
  onStatusChange?: (status: MediaStatusFilter) => void;
  onSortChange?: (sort: MediaSortOption) => void;
}

const typeOptions: { value: MediaTypeFilter; label: string; icon: React.ReactNode }[] = [
  { value: "all", label: "All", icon: <Grid3X3 className="w-4 h-4" /> },
  { value: "image", label: "Images", icon: <Image className="w-4 h-4" /> },
  { value: "video", label: "Videos", icon: <Film className="w-4 h-4" /> },
  { value: "audio", label: "Audio", icon: <Music className="w-4 h-4" /> },
  { value: "document", label: "Documents", icon: <FileText className="w-4 h-4" /> },
];

const statusOptions: { value: MediaStatusFilter; label: string; icon: React.ReactNode }[] = [
  { value: "all", label: "All", icon: <Filter className="w-4 h-4" /> },
  { value: "ready", label: "Ready", icon: <CheckCircle className="w-4 h-4" /> },
  { value: "processing", label: "Processing", icon: <Clock className="w-4 h-4" /> },
  { value: "failed", label: "Failed", icon: <XCircle className="w-4 h-4" /> },
];

const sortOptions: { value: MediaSortOption; label: string }[] = [
  { value: "newest", label: "Newest" },
  { value: "largest", label: "Largest" },
  { value: "name", label: "Name" },
];

export function MediaFilters({ onTypeChange, onStatusChange, onSortChange }: MediaFiltersProps) {
  const [selectedType, setSelectedType] = useState<MediaTypeFilter>("all");
  const [selectedStatus, setSelectedStatus] = useState<MediaStatusFilter>("all");
  const [selectedSort, setSelectedSort] = useState<MediaSortOption>("newest");
  const [searchQuery, setSearchQuery] = useState("");

  const handleTypeChange = (type: MediaTypeFilter) => {
    setSelectedType(type);
    onTypeChange?.(type);
  };

  const handleStatusChange = (status: MediaStatusFilter) => {
    setSelectedStatus(status);
    onStatusChange?.(status);
  };

  const handleSortChange = (sort: MediaSortOption) => {
    setSelectedSort(sort);
    onSortChange?.(sort);
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search media files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {/* Type Filters */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase">Type</p>
          <div className="flex flex-wrap gap-2">
            {typeOptions.map((option) => (
              <Button
                key={option.value}
                variant={selectedType === option.value ? "default" : "outline"}
                size="sm"
                onClick={() => handleTypeChange(option.value)}
                className="gap-1"
              >
                {option.icon}
                {option.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Status Filters */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase">Status</p>
          <div className="flex flex-wrap gap-2">
            {statusOptions.map((option) => (
              <Button
                key={option.value}
                variant={selectedStatus === option.value ? "default" : "outline"}
                size="sm"
                onClick={() => handleStatusChange(option.value)}
                className="gap-1"
              >
                {option.icon}
                {option.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Sort Options */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase">Sort By</p>
          <div className="flex flex-wrap gap-2">
            {sortOptions.map((option) => (
              <Badge
                key={option.value}
                variant={selectedSort === option.value ? "default" : "secondary"}
                className="cursor-pointer"
                onClick={() => handleSortChange(option.value)}
              >
                {option.label}
              </Badge>
            ))}
          </div>
        </div>

        {/* Project Filters */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase">Project</p>
          <div className="flex flex-wrap gap-2">
            {[
              "All Projects",
              "YouTube Horror Episode 01",
              "Marketing Campaign",
              "Product Video Series",
            ].map((project) => (
              <Button
                key={project}
                variant="outline"
                size="sm"
                className="gap-1"
              >
                {project}
              </Button>
            ))}
          </div>
        </div>

        {/* Creator Filters */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase">Creator</p>
          <div className="flex flex-wrap gap-2">
            {[
              "All Creators",
              "Mohammad",
              "Script AI Agent",
              "Image AI Agent",
              "Voice AI Agent",
            ].map((creator) => (
              <Button
                key={creator}
                variant="outline"
                size="sm"
                className="gap-1"
              >
                {creator}
              </Button>
            ))}
          </div>
        </div>

        {/* Source Filters */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase">Source</p>
          <div className="flex flex-wrap gap-2">
            {[
              "All Sources",
              "Uploaded",
              "AI Generated",
              "Edited",
              "Imported",
            ].map((source) => (
              <Badge
                key={source}
                variant="secondary"
                className="cursor-pointer"
              >
                {source}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
