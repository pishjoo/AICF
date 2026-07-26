import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { CollectionDetail } from '@/types/collection-detail';
import { FolderOpen, User, HardDrive, FileBox, Calendar } from 'lucide-react';

interface CollectionHeaderProps {
  collection: CollectionDetail;
}

const getStatusVariant = (status: string) => {
  return status === 'active' ? 'default' : 'secondary';
};

const getTypeVariant = (type: string) => {
  switch (type) {
    case 'project':
      return 'default';
    case 'campaign':
      return 'secondary';
    case 'personal':
      return 'outline';
    case 'archive':
      return 'secondary';
    default:
      return 'outline';
  }
};

export function CollectionHeader({ collection }: CollectionHeaderProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <CardTitle className="text-2xl">{collection.name}</CardTitle>
            <CardDescription className="text-base">
              {collection.description}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Badge variant={getStatusVariant(collection.status)}>
              {collection.status}
            </Badge>
            <Badge variant={getTypeVariant(collection.type)}>
              {collection.type}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <User className="h-4 w-4" />
              <span>Owner</span>
            </div>
            <span className="font-medium">{collection.owner}</span>
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FolderOpen className="h-4 w-4" />
              <span>Project</span>
            </div>
            <span className="font-medium">{collection.project}</span>
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileBox className="h-4 w-4" />
              <span>Assets</span>
            </div>
            <span className="font-medium">{collection.assetCount}</span>
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <HardDrive className="h-4 w-4" />
              <span>Total Size</span>
            </div>
            <span className="font-medium">{collection.totalSize}</span>
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>Created</span>
            </div>
            <span className="font-medium text-sm">
              {new Date(collection.createdAt).toLocaleDateString()}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>Updated</span>
            </div>
            <span className="font-medium text-sm">
              {new Date(collection.updatedAt).toLocaleDateString()}
            </span>
          </div>
        </div>
        {collection.tags && collection.tags.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex flex-wrap gap-2">
              {collection.tags.map((tag) => (
                <Badge key={tag} variant="outline">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
