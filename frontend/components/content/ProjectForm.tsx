'use client';

import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import type { ContentType, TargetPlatform, Language } from '@/types/content';

const projectFormSchema = z.object({
  title: z.string().min(3, 'Title must be at least 3 characters').max(100, 'Title must be less than 100 characters'),
  description: z.string().min(10, 'Description must be at least 10 characters').max(500, 'Description must be less than 500 characters'),
  contentType: z.enum(['video', 'audio', 'article', 'social_post', 'presentation']),
  targetPlatform: z.enum(['youtube', 'tiktok', 'instagram', 'linkedin', 'twitter', 'facebook', 'website', 'podcast']),
  language: z.enum(['en', 'es', 'fr', 'de', 'ja', 'zh', 'ko', 'pt', 'it', 'ru']),
});

export type ProjectFormValues = z.infer<typeof projectFormSchema>;

interface ProjectFormProps {
  defaultValues?: Partial<ProjectFormValues>;
  onSubmit?: (data: ProjectFormValues) => void | Promise<void>;
  isSubmitting?: boolean;
  submitLabel?: string;
}

const contentTypes: { value: ContentType; label: string }[] = [
  { value: 'video', label: 'Video' },
  { value: 'audio', label: 'Audio' },
  { value: 'article', label: 'Article' },
  { value: 'social_post', label: 'Social Post' },
  { value: 'presentation', label: 'Presentation' },
];

const targetPlatforms: { value: TargetPlatform; label: string }[] = [
  { value: 'youtube', label: 'YouTube' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'twitter', label: 'Twitter/X' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'website', label: 'Website' },
  { value: 'podcast', label: 'Podcast' },
];

const languages: { value: Language; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'ja', label: 'Japanese' },
  { value: 'zh', label: 'Chinese' },
  { value: 'ko', label: 'Korean' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'it', label: 'Italian' },
  { value: 'ru', label: 'Russian' },
];

// Custom validation function using Zod
function validateForm(data: ProjectFormValues): Record<string, string> | null {
  const result = projectFormSchema.safeParse(data);
  if (!result.success) {
    const errors: Record<string, string> = {};
    result.error.errors.forEach((err) => {
      if (err.path[0]) {
        errors[err.path[0] as string] = err.message;
      }
    });
    return errors;
  }
  return null;
}

export function ProjectForm({
  defaultValues,
  onSubmit,
  isSubmitting = false,
  submitLabel = 'Create Project',
}: ProjectFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
    clearErrors,
  } = useForm<ProjectFormValues>({
    defaultValues: {
      title: defaultValues?.title || '',
      description: defaultValues?.description || '',
      contentType: defaultValues?.contentType || 'video',
      targetPlatform: defaultValues?.targetPlatform || 'youtube',
      language: defaultValues?.language || 'en',
    },
  });

  const handleFormSubmit = async (data: ProjectFormValues) => {
    clearErrors();
    const validationErrors = validateForm(data);
    
    if (validationErrors) {
      Object.entries(validationErrors).forEach(([field, message]) => {
        setError(field as keyof ProjectFormValues, { type: 'manual', message });
      });
      return;
    }

    if (onSubmit) {
      await onSubmit(data);
    } else {
      // Mock behavior - log to console
      console.log('Project created:', data);
      alert('Project created successfully! (Mock submission)');
    }
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)}>
      <Card>
        <CardHeader>
          <CardTitle>Project Details</CardTitle>
          <CardDescription>
            Fill in the information for your new content project.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Title */}
          <div className="space-y-2">
            <label htmlFor="title" className="text-sm font-medium">
              Project Name
            </label>
            <input
              id="title"
              type="text"
              {...register('title')}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="Enter project name"
            />
            {errors.title && (
              <p className="text-sm text-destructive">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label htmlFor="description" className="text-sm font-medium">
              Description
            </label>
            <textarea
              id="description"
              {...register('description')}
              rows={4}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
              placeholder="Describe your content project"
            />
            {errors.description && (
              <p className="text-sm text-destructive">{errors.description.message}</p>
            )}
          </div>

          {/* Content Type */}
          <div className="space-y-2">
            <label htmlFor="contentType" className="text-sm font-medium">
              Content Type
            </label>
            <select
              id="contentType"
              {...register('contentType')}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-background"
            >
              {contentTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
            {errors.contentType && (
              <p className="text-sm text-destructive">{errors.contentType.message}</p>
            )}
          </div>

          {/* Target Platform */}
          <div className="space-y-2">
            <label htmlFor="targetPlatform" className="text-sm font-medium">
              Target Platform
            </label>
            <select
              id="targetPlatform"
              {...register('targetPlatform')}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-background"
            >
              {targetPlatforms.map((platform) => (
                <option key={platform.value} value={platform.value}>
                  {platform.label}
                </option>
              ))}
            </select>
            {errors.targetPlatform && (
              <p className="text-sm text-destructive">{errors.targetPlatform.message}</p>
            )}
          </div>

          {/* Language */}
          <div className="space-y-2">
            <label htmlFor="language" className="text-sm font-medium">
              Language
            </label>
            <select
              id="language"
              {...register('language')}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-background"
            >
              {languages.map((lang) => (
                <option key={lang.value} value={lang.value}>
                  {lang.label}
                </option>
              ))}
            </select>
            {errors.language && (
              <p className="text-sm text-destructive">{errors.language.message}</p>
            )}
          </div>
        </CardContent>
        <CardFooter>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? 'Creating...' : submitLabel}
          </Button>
        </CardFooter>
      </Card>
    </form>
  );
}
