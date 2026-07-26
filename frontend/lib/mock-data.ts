import type { ContentProject, PipelineStage } from '@/types/content';
import type { WorkflowStage, Approval, ActivityEvent } from '@/types/workflow';
import type { MediaCollection } from '@/types/collection';
import type { CollectionDetail } from '@/types/collection-detail';

export const sampleContentProjects: ContentProject[] = [
  {
    id: '1',
    title: 'Product Launch Video Series',
    description: 'A comprehensive video series showcasing our new product features and benefits for the Q1 launch campaign.',
    status: 'in_progress',
    progress: 65,
    currentStage: 'voice',
    createdAt: '2024-01-15T10:30:00Z',
  },
  {
    id: '2',
    title: 'Social Media Content Batch #12',
    description: 'Weekly social media content batch for Instagram and LinkedIn platforms including posts and stories.',
    status: 'review',
    progress: 85,
    currentStage: 'review',
    createdAt: '2024-01-18T14:00:00Z',
  },
  {
    id: '3',
    title: 'Customer Testimonial Compilation',
    description: 'Edited compilation of customer testimonials for website and marketing materials.',
    status: 'published',
    progress: 100,
    currentStage: 'published',
    createdAt: '2024-01-10T09:15:00Z',
  },
  {
    id: '4',
    title: 'Training Module - Onboarding',
    description: 'Internal training content for new employee onboarding process.',
    status: 'draft',
    progress: 20,
    currentStage: 'idea',
    createdAt: '2024-01-20T11:45:00Z',
  },
  {
    id: '5',
    title: 'Podcast Episode 42 - Industry Trends',
    description: 'Monthly podcast episode discussing latest industry trends and insights.',
    status: 'in_progress',
    progress: 45,
    currentStage: 'script',
    createdAt: '2024-01-17T16:20:00Z',
  },
];

export const pipelineStages: PipelineStage[] = [
  { id: 'idea', name: 'Idea', status: 'completed' },
  { id: 'script', name: 'Script', status: 'pending' },
  { id: 'voice', name: 'Voice', status: 'pending' },
  { id: 'visual', name: 'Visual', status: 'pending' },
  { id: 'editing', name: 'Editing', status: 'pending' },
  { id: 'review', name: 'Review', status: 'pending' },
  { id: 'published', name: 'Published', status: 'pending' },
];

export const getPipelineStagesForProject = (currentStage: string): PipelineStage[] => {
  const stageOrder = ['idea', 'script', 'voice', 'visual', 'editing', 'review', 'published'];
  const currentIndex = stageOrder.indexOf(currentStage);

  return pipelineStages.map((stage) => ({
    ...stage,
    status:
      stageOrder.indexOf(stage.id) < currentIndex
        ? 'completed'
        : stageOrder.indexOf(stage.id) === currentIndex
          ? 'in_progress'
          : 'pending',
  }));
};

export const workflowStages: WorkflowStage[] = [
  { id: '1', name: 'Draft', status: 'completed', completedAt: '2024-01-15T10:00:00Z' },
  { id: '2', name: 'Review', status: 'active', completedAt: undefined },
  { id: '3', name: 'Approval', status: 'pending', completedAt: undefined },
  { id: '4', name: 'Publish', status: 'pending', completedAt: undefined },
];

export const approvalRequests: Approval[] = [
  {
    id: '1',
    reviewer: 'John Smith',
    status: 'approved',
    comment: 'Looks great, approved for publishing.',
    createdAt: '2024-01-16T09:30:00Z',
  },
  {
    id: '2',
    reviewer: 'Sarah Johnson',
    status: 'pending',
    comment: undefined,
    createdAt: '2024-01-17T14:00:00Z',
  },
  {
    id: '3',
    reviewer: 'Mike Chen',
    status: 'changes_requested',
    comment: 'Please update the title and add more details to the description.',
    createdAt: '2024-01-18T11:15:00Z',
  },
];

export const activityEvents: ActivityEvent[] = [
  { id: '1', user: 'Alice Brown', action: 'Created project', timestamp: '2024-01-15T08:00:00Z' },
  { id: '2', user: 'Bob Wilson', action: 'Updated script', timestamp: '2024-01-15T14:30:00Z' },
  { id: '3', user: 'John Smith', action: 'Approved review', timestamp: '2024-01-16T09:30:00Z' },
  { id: '4', user: 'Sarah Johnson', action: 'Requested changes', timestamp: '2024-01-17T10:00:00Z' },
  { id: '5', user: 'Alice Brown', action: 'Applied feedback', timestamp: '2024-01-17T16:45:00Z' },
  { id: '6', user: 'Mike Chen', action: 'Started approval process', timestamp: '2024-01-18T11:15:00Z' },
];

export const getWorkflowStagesForProject = (projectId?: string): WorkflowStage[] => {
  // In a real implementation, this would filter by projectId
  return workflowStages;
};

export const getApprovalsForProject = (projectId?: string): Approval[] => {
  // In a real implementation, this would filter by projectId
  return approvalRequests;
};

export const getActivityEventsForProject = (projectId?: string): ActivityEvent[] => {
  // In a real implementation, this would filter by projectId
  return activityEvents;
};

export const sampleMediaCollections: MediaCollection[] = [
  {
    id: '1',
    name: 'YouTube Episode Assets',
    description: 'Video assets and thumbnails for YouTube episode series',
    type: 'project',
    status: 'active',
    assetCount: 24,
    createdAt: '2024-01-10T08:00:00Z',
    updatedAt: '2024-01-20T14:30:00Z',
  },
  {
    id: '2',
    name: 'Marketing Campaign Media',
    description: 'Images, videos, and graphics for Q1 marketing campaign',
    type: 'campaign',
    status: 'active',
    assetCount: 56,
    createdAt: '2024-01-05T10:00:00Z',
    updatedAt: '2024-01-22T09:15:00Z',
  },
  {
    id: '3',
    name: 'AI Generated Videos',
    description: 'Collection of AI-generated video content for experimentation',
    type: 'personal',
    status: 'active',
    assetCount: 18,
    createdAt: '2024-01-12T16:45:00Z',
    updatedAt: '2024-01-21T11:00:00Z',
  },
  {
    id: '4',
    name: 'Archived Projects',
    description: 'Legacy project assets from previous campaigns',
    type: 'archive',
    status: 'archived',
    assetCount: 142,
    createdAt: '2023-11-01T09:00:00Z',
    updatedAt: '2024-01-08T17:30:00Z',
  },
];

export const getMediaCollections = (): MediaCollection[] => {
  return sampleMediaCollections;
};

export const sampleCollectionDetails: CollectionDetail[] = [
  {
    id: '1',
    name: 'YouTube Horror Episode 01',
    description: 'Assets for the first episode of the YouTube horror channel series including raw footage, sound effects, and thumbnails.',
    type: 'project',
    status: 'active',
    createdAt: '2024-01-10T08:00:00Z',
    updatedAt: '2024-01-20T14:30:00Z',
    owner: 'Mohammad',
    project: 'YouTube Horror Channel',
    assetCount: 34,
    totalSize: '4.8 GB',
    tags: ['youtube', 'horror', 'episode-01'],
  },
  {
    id: '2',
    name: 'Marketing Campaign Q1',
    description: 'Complete media assets for Q1 marketing campaign including promotional videos, social media graphics, and banners.',
    type: 'campaign',
    status: 'active',
    createdAt: '2024-01-05T10:00:00Z',
    updatedAt: '2024-01-22T09:15:00Z',
    owner: 'Sarah Johnson',
    project: 'Q1 Marketing Push',
    assetCount: 56,
    totalSize: '12.3 GB',
    tags: ['marketing', 'q1', 'campaign', 'social-media'],
  },
  {
    id: '3',
    name: 'AI Generated Content',
    description: 'Experimental AI-generated video content for testing new workflows and techniques.',
    type: 'personal',
    status: 'active',
    createdAt: '2024-01-12T16:45:00Z',
    updatedAt: '2024-01-21T11:00:00Z',
    owner: 'Alex Chen',
    project: 'AI Experiments',
    assetCount: 18,
    totalSize: '2.1 GB',
    tags: ['ai', 'experimental', 'video'],
  },
];

export const getCollectionDetail = (id: string): CollectionDetail | undefined => {
  return sampleCollectionDetails.find((collection) => collection.id === id);
};

export const getAllCollectionDetails = (): CollectionDetail[] => {
  return sampleCollectionDetails;
};
