import type { CollectionType, CollectionStatus } from './collection';

export interface CollectionDetail {
  id: string;
  name: string;
  description: string;
  type: CollectionType;
  status: CollectionStatus;
  createdAt: string;
  updatedAt: string;
  owner: string;
  project: string;
  assetCount: number;
  totalSize: string;
  tags: string[];
}
