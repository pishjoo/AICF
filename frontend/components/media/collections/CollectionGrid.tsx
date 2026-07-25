"use client";

import { Card, CardContent } from "@/components/ui/card";
import { CollectionCard } from "./CollectionCard";
import { MediaCollection } from "@/types/collection";

interface CollectionGridProps {
  collections: MediaCollection[];
}

export function CollectionGrid({ collections }: CollectionGridProps) {
  if (!collections || collections.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-center text-sm text-gray-500">
            No collections found
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {collections.map((collection) => (
        <CollectionCard key={collection.id} collection={collection} />
      ))}
    </div>
  );
}
