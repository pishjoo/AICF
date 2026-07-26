import { CollectionHeader } from '@/components/media/collections/detail/CollectionHeader';
import { getCollectionDetail } from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function CollectionDetailPage({ params }: PageProps) {
  const { id } = await params;
  const collection = getCollectionDetail(id);

  if (!collection) {
    return (
      <div className="container mx-auto py-8">
        <Card>
          <CardHeader>
            <CardTitle>Collection not found</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              The collection you are looking for does not exist.
            </p>
            <Button asChild>
              <Link href="/media/collections">Back to Collections</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      <CollectionHeader collection={collection} />
    </div>
  );
}
