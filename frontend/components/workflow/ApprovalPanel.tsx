import { Approval, ApprovalStatus } from '@/types/workflow';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar } from '@/components/ui/avatar';

interface ApprovalPanelProps {
  approval: Approval;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onRequestChanges?: (id: string) => void;
}

function getStatusBadgeVariant(status: ApprovalStatus) {
  switch (status) {
    case 'approved':
      return 'default' as const;
    case 'rejected':
      return 'destructive' as const;
    case 'changes_requested':
      return 'secondary' as const;
    case 'pending':
      return 'outline' as const;
    default:
      return 'outline' as const;
  }
}

function getStatusLabel(status: ApprovalStatus) {
  switch (status) {
    case 'approved':
      return 'Approved';
    case 'rejected':
      return 'Rejected';
    case 'changes_requested':
      return 'Changes Requested';
    case 'pending':
      return 'Pending';
    default:
      return status;
  }
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function ApprovalPanel({
  approval,
  onApprove,
  onReject,
  onRequestChanges,
}: ApprovalPanelProps) {
  const isPending = approval.status === 'pending';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Avatar fallback={getInitials(approval.reviewer)} />
            <div>
              <CardTitle className="text-base">{approval.reviewer}</CardTitle>
              <CardDescription>
                {new Date(approval.createdAt).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </CardDescription>
            </div>
          </div>
          <Badge variant={getStatusBadgeVariant(approval.status)}>
            {getStatusLabel(approval.status)}
          </Badge>
        </div>
      </CardHeader>
      {approval.comment && (
        <CardContent>
          <p className="text-sm text-muted-foreground">{approval.comment}</p>
        </CardContent>
      )}
      {isPending && (onApprove || onReject || onRequestChanges) && (
        <CardFooter className="flex gap-2">
          {onApprove && (
            <Button
              variant="default"
              size="sm"
              onClick={() => onApprove(approval.id)}
            >
              Approve
            </Button>
          )}
          {onReject && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => onReject(approval.id)}
            >
              Reject
            </Button>
          )}
          {onRequestChanges && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onRequestChanges(approval.id)}
            >
              Request Changes
            </Button>
          )}
        </CardFooter>
      )}
    </Card>
  );
}
