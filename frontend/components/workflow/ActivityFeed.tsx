import { ActivityEvent } from '@/types/workflow';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar } from '@/components/ui/avatar';

interface ActivityFeedProps {
  events: ActivityEvent[];
  limit?: number;
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) {
    return 'Just now';
  } else if (diffMins < 60) {
    return `${diffMins}m ago`;
  } else if (diffHours < 24) {
    return `${diffHours}h ago`;
  } else if (diffDays < 7) {
    return `${diffDays}d ago`;
  } else {
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}

export function ActivityFeed({ events, limit }: ActivityFeedProps) {
  const displayEvents = limit ? events.slice(0, limit) : events;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {displayEvents.map((event) => (
            <div key={event.id} className="flex items-start gap-3">
              <Avatar fallback={getInitials(event.user)} className="h-8 w-8" />
              <div className="flex-1 space-y-1">
                <p className="text-sm">
                  <span className="font-medium">{event.user}</span>{' '}
                  <span className="text-muted-foreground">{event.action}</span>
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatTimestamp(event.timestamp)}
                </p>
              </div>
            </div>
          ))}
          {displayEvents.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">
              No activity yet
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
