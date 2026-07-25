import Link from 'next/link';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import type { ContentProject } from '@/types/content';
import { cn } from '@/lib/utils';

interface ProjectCardProps {
  project: ContentProject;
}

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

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <CardTitle className="text-lg font-semibold">{project.title}</CardTitle>
          <Badge variant={statusVariants[project.status] || 'outline'}>
            {statusLabels[project.status] || project.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground line-clamp-2">
          {project.description}
        </p>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">{project.progress}%</span>
          </div>
          <Progress value={project.progress} className="h-2" />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Current Stage:</span>
          <span className={cn(
            'px-2 py-0.5 rounded-full text-xs font-medium',
            'bg-primary/10 text-primary'
          )}>
            {project.currentStage.charAt(0).toUpperCase() + project.currentStage.slice(1)}
          </span>
        </div>
      </CardContent>
      <CardFooter>
        <Link
          href={`/content-factory/${project.id}`}
          className="text-sm text-primary hover:underline font-medium"
        >
          View Details →
        </Link>
      </CardFooter>
    </Card>
  );
}
