import type { ContentProject, PipelineStage } from '@/types/content';

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
