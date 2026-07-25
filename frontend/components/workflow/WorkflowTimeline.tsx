import { WorkflowStage } from '@/types/workflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface WorkflowTimelineProps {
  stages: WorkflowStage[];
}

function getStatusBadgeVariant(status: WorkflowStage['status']) {
  switch (status) {
    case 'completed':
      return 'default' as const;
    case 'active':
      return 'secondary' as const;
    case 'pending':
      return 'outline' as const;
    default:
      return 'outline' as const;
  }
}

function getStatusLabel(status: WorkflowStage['status']) {
  switch (status) {
    case 'completed':
      return 'Completed';
    case 'active':
      return 'In Progress';
    case 'pending':
      return 'Pending';
    default:
      return status;
  }
}

export function WorkflowTimeline({ stages }: WorkflowTimelineProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-muted" />

          <div className="space-y-6">
            {stages.map((stage, index) => (
              <div key={stage.id} className="relative flex items-start gap-4">
                {/* Status indicator */}
                <div
                  className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 ${
                    stage.status === 'completed'
                      ? 'border-primary bg-primary text-primary-foreground'
                      : stage.status === 'active'
                        ? 'border-primary bg-background'
                        : 'border-muted bg-background'
                  }`}
                >
                  {stage.status === 'completed' && (
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  )}
                  {stage.status === 'active' && (
                    <div className="h-2 w-2 rounded-full bg-primary" />
                  )}
                </div>

                {/* Stage info */}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{stage.name}</span>
                    <Badge variant={getStatusBadgeVariant(stage.status)}>
                      {getStatusLabel(stage.status)}
                    </Badge>
                  </div>
                  {stage.completedAt && (
                    <p className="text-sm text-muted-foreground">
                      Completed{' '}
                      {new Date(stage.completedAt).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
