import type { ContentProject, PipelineStage } from '@/types/content';
import type { WorkflowStage, Approval, ActivityEvent } from '@/types/workflow';
import type { MediaAssetDetail } from '@/types/media-detail';

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

export const sampleMediaAssets: MediaAssetDetail[] = [
  {
    id: '1',
    filename: 'product-launch-hero.mp4',
    type: 'video',
    status: 'ready',
    size: 52428800,
    url: 'https://cdn.example.com/media/product-launch-hero.mp4',
    thumbnail: 'https://cdn.example.com/thumbnails/product-launch-hero.jpg',
    metadata: {
      dimensions: { width: 1920, height: 1080 },
      duration: 120,
      codec: 'h264',
      createdAt: '2024-01-15T10:30:00Z',
      uploadedBy: 'Alice Brown',
    },
    tags: ['product', 'launch', 'hero', 'q1'],
  },
  {
    id: '2',
    filename: 'social-banner-2024.png',
    type: 'image',
    status: 'ready',
    size: 2048576,
    url: 'https://cdn.example.com/media/social-banner-2024.png',
    thumbnail: 'https://cdn.example.com/thumbnails/social-banner-2024.png',
    metadata: {
      dimensions: { width: 1200, height: 630 },
      createdAt: '2024-01-18T14:00:00Z',
      uploadedBy: 'Bob Wilson',
    },
    tags: ['social', 'banner', 'marketing'],
  },
  {
    id: '3',
    filename: 'podcast-ep42.mp3',
    type: 'audio',
    status: 'processing',
    size: 15728640,
    url: 'https://cdn.example.com/media/podcast-ep42.mp3',
    metadata: {
      duration: 1800,
      codec: 'mp3',
      createdAt: '2024-01-17T16:20:00Z',
      uploadedBy: 'Sarah Johnson',
    },
    tags: ['podcast', 'episode', 'audio'],
  },
  {
    id: '4',
    filename: 'brand-guidelines.pdf',
    type: 'document',
    status: 'ready',
    size: 4194304,
    url: 'https://cdn.example.com/media/brand-guidelines.pdf',
    thumbnail: 'https://cdn.example.com/thumbnails/brand-guidelines.png',
    metadata: {
      createdAt: '2024-01-10T09:15:00Z',
      uploadedBy: 'John Smith',
    },
    tags: ['brand', 'guidelines', 'document'],
  },
  {
    id: '5',
    filename: 'testimonial-raw.mov',
    type: 'video',
    status: 'pending',
    size: 104857600,
    url: 'https://cdn.example.com/media/testimonial-raw.mov',
    metadata: {
      dimensions: { width: 3840, height: 2160 },
      duration: 300,
      codec: 'prores',
      createdAt: '2024-01-20T11:45:00Z',
      uploadedBy: 'Mike Chen',
    },
    tags: ['testimonial', 'raw', 'customer'],
  },
];

export const getMediaAssetDetail = (id: string): MediaAssetDetail | undefined => {
  return sampleMediaAssets.find((asset) => asset.id === id);
};
