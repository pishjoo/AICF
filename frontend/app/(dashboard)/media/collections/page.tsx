"use client";

import { CollectionGrid } from "@/components/media/collections/CollectionGrid";
import { getMediaCollections } from "@/lib/mock-data";
import { Card, CardContent } from "@/components/ui/card";

export default function MediaCollectionsPage() {
  const collections = getMediaCollections();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Media Collections</h1>
        <p className="text-gray-500 mt-1">
          Organize and manage reusable media assets for your content projects.
        </p>
      </div>

      {collections.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-center text-sm text-gray-500">
              No collections found
            </p>
          </CardContent>
        </Card>
      ) : (
        <CollectionGrid collections={collections} />
      )}
    </div>
  );
}
