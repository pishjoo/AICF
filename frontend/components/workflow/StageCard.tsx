import { WorkflowStage } from '@/types/workflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface StageCardProps {
  stage: WorkflowStage;
  isActive?: boolean;
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

export function StageCard({ stage, isActive = false }: StageCardProps) {
  return (
    <Card className={isActive ? 'ring-2 ring-primary' : ''}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-medium">{stage.name}</span>
              {isActive && (
                <span className="flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                </span>
              )}
            </div>
            {stage.completedAt && (
              <p className="text-xs text-muted-foreground">
                {new Date(stage.completedAt).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                })}
              </p>
            )}
          </div>
          <Badge variant={getStatusBadgeVariant(stage.status)}>
            {getStatusLabel(stage.status)}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
