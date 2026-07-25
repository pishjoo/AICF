"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Folder, Image, Archive } from "lucide-react";
import { MediaCollection } from "@/types/collection";

interface CollectionCardProps {
  collection: MediaCollection;
}

function getTypeIcon(type: string) {
  switch (type) {
    case "project":
      return <Folder className="w-5 h-5 text-blue-500" />;
    case "campaign":
      return <Image className="w-5 h-5 text-green-500" />;
    case "archive":
      return <Archive className="w-5 h-5 text-orange-500" />;
    default:
      return <Folder className="w-5 h-5 text-gray-500" />;
  }
}

function getStatusVariant(status: string) {
  return status === "active" ? "default" : "secondary";
}

function getStatusLabel(status: string) {
  return status === "active" ? "Active" : "Archived";
}

function formatType(type: string) {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

export function CollectionCard({ collection }: CollectionCardProps) {
  const formattedDate = new Date(collection.createdAt).toLocaleDateString();

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer">
      <CardContent className="p-4">
        <div className="flex flex-col space-y-3">
          <div className="flex items-center gap-2">
            {getTypeIcon(collection.type)}
            <h3 className="text-sm font-semibold text-gray-900 line-clamp-1">
              {collection.name}
            </h3>
          </div>

          <p className="text-xs text-gray-500 line-clamp-2">
            {collection.description}
          </p>

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {formatType(collection.type)}
            </Badge>
            <Badge variant={getStatusVariant(collection.status)} className="text-xs">
              {getStatusLabel(collection.status)}
            </Badge>
          </div>

          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{collection.assetCount} assets</span>
            <span>Created {formattedDate}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
