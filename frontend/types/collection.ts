export type CollectionType = 'project' | 'campaign' | 'personal' | 'archive';

export type CollectionStatus = 'active' | 'archived';

export interface MediaCollection {
  id: string;
  name: string;
  description: string;
  type: CollectionType;
  status: CollectionStatus;
  assetCount: number;
  createdAt: string;
  updatedAt: string;
}
