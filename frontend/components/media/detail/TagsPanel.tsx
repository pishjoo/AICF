import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { MediaAssetDetail } from './MediaPreview';

interface TagsPanelProps {
  asset: MediaAssetDetail;
}

export function TagsPanel({ asset }: TagsPanelProps) {
  const tags = asset.tags || [];

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Tags</CardTitle>
      </CardHeader>
      <CardContent>
        {tags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <Badge key={tag} variant="secondary">
                {tag}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No tags assigned</p>
        )}
      </CardContent>
    </Card>
  );
}
