'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, MoreHorizontal, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Pipeline, PipelineStageCard } from '@/components/content/Pipeline';
import { sampleContentProjects, getPipelineStagesForProject } from '@/lib/mock-data';
import type { ContentProject } from '@/types/content';

const statusLabels: Record<string, string> = {
  draft: 'Draft',
  in_progress: 'In Progress',
  review: 'Review',
  published: 'Published',
  archived: 'Archived',
};

const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  draft: 'secondary',
  in_progress: 'default',
  review: 'default',
  published: 'default',
  archived: 'outline',
};

export default function ContentProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  // Find project from mock data - in real app this would be fetched from API
  const project: ContentProject | undefined = sampleContentProjects.find(
    (p) => p.id === projectId
  );

  if (!project) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/content-factory">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">Project Not Found</h1>
        </div>
        <p className="text-muted-foreground">
          The project you&apos;re looking for doesn&apos;t exist or has been removed.
        </p>
        <Link href="/content-factory">
          <Button>Back to Projects</Button>
        </Link>
      </div>
    );
  }

  const pipelineStages = getPipelineStagesForProject(project.currentStage);

  // Placeholder for future workflow approval components
  const nextActions = [
    { id: 'approve-script', label: 'Approve Script', disabled: project.currentStage !== 'script' },
    { id: 'generate-voice', label: 'Generate Voice Over', disabled: project.currentStage !== 'voice' },
    { id: 'create-visuals', label: 'Create Visuals', disabled: project.currentStage !== 'visual' },
    { id: 'start-editing', label: 'Start Editing', disabled: project.currentStage !== 'editing' },
    { id: 'submit-review', label: 'Submit for Review', disabled: project.currentStage !== 'review' },
  ].filter((action) => !action.disabled);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/content-factory">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{project.title}</h1>
              <Badge variant={statusVariants[project.status] || 'outline'}>
                {statusLabels[project.status] || project.status}
              </Badge>
            </div>
            <p className="text-muted-foreground mt-1">
              Created {new Date(project.createdAt).toLocaleDateString()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <MoreHorizontal className="mr-2 h-4 w-4" />
            More Actions
          </Button>
          {project.status !== 'published' && (
            <Button size="sm">
              <Play className="mr-2 h-4 w-4" />
              Continue Workflow
            </Button>
          )}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Project Info & Pipeline */}
        <div className="lg:col-span-2 space-y-6">
          {/* Project Information */}
          <Card>
            <CardHeader>
              <CardTitle>Project Information</CardTitle>
              <CardDescription>{project.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Current Stage</p>
                  <p className="font-medium capitalize">{project.currentStage}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Overall Progress</p>
                  <p className="font-medium">{project.progress}%</p>
                </div>
              </div>
              <div className="mt-4">
                <Progress value={project.progress} className="h-2" />
              </div>
            </CardContent>
          </Card>

          {/* Pipeline Visualization */}
          <Card>
            <CardHeader>
              <CardTitle>Production Pipeline</CardTitle>
              <CardDescription>
                Track the progress through each production stage
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Pipeline stages={pipelineStages} />
              
              {/* Individual Stage Cards - prepared for future workflow approvals */}
              <div className="grid gap-3 mt-6 md:grid-cols-2">
                {pipelineStages.map((stage) => (
                  <PipelineStageCard key={stage.id} stage={stage} />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Next Actions & Details */}
        <div className="space-y-6">
          {/* Next Actions - Prepared for workflow approval components */}
          <Card>
            <CardHeader>
              <CardTitle>Next Actions</CardTitle>
              <CardDescription>
                Available actions for the current stage
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {nextActions.length > 0 ? (
                nextActions.map((action) => (
                  <Button key={action.id} className="w-full justify-start" variant="outline">
                    <Play className="mr-2 h-4 w-4" />
                    {action.label}
                  </Button>
                ))
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No actions available at this stage
                </p>
              )}
              
              {/* Placeholder for future workflow approval integration */}
              <div className="pt-4 border-t">
                <p className="text-xs text-muted-foreground mb-2">
                  Workflow Approval Status
                </p>
                <div className="flex items-center gap-2 text-sm">
                  <Badge variant="secondary">Pending Review</Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Project Metadata */}
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Project ID</p>
                <p className="font-mono text-sm">{project.id}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <Badge variant={statusVariants[project.status] || 'outline'}>
                  {statusLabels[project.status]}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Created</p>
                <p className="text-sm">
                  {new Date(project.createdAt).toLocaleString()}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
