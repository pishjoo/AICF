export type ContentProjectStatus = 'draft' | 'in_progress' | 'review' | 'published' | 'archived';

export type PipelineStageStatus = 'pending' | 'in_progress' | 'completed' | 'blocked';

export interface ContentProject {
  id: string;
  title: string;
  description: string;
  status: ContentProjectStatus;
  progress: number;
  currentStage: string;
  createdAt: string;
}

export interface PipelineStage {
  id: string;
  name: string;
  status: PipelineStageStatus;
  completedAt?: string;
}

export type ContentType = 'video' | 'audio' | 'article' | 'social_post' | 'presentation';

export type TargetPlatform = 'youtube' | 'tiktok' | 'instagram' | 'linkedin' | 'twitter' | 'facebook' | 'website' | 'podcast';

export type Language = 'en' | 'es' | 'fr' | 'de' | 'ja' | 'zh' | 'ko' | 'pt' | 'it' | 'ru';

export interface CreateContentProjectInput {
  title: string;
  description: string;
  contentType: ContentType;
  targetPlatform: TargetPlatform;
  language: Language;
}
