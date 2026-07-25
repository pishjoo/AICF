import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

// KPI Data interface
interface KpiCardProps {
  title: string;
  value: string | number;
  description?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

function KpiCard({ title, value, description, trend, trendValue }: KpiCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {trend && (
          <Badge variant={trend === 'up' ? 'default' : trend === 'down' ? 'destructive' : 'secondary'}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trendValue}
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  // Mock data - will be replaced with real API calls
  const kpis = {
    totalProjects: 24,
    activeAgents: 8,
    processingJobs: 3,
    publishedVideos: 156,
  };

  const recentActivity = [
    { id: 1, action: 'Project created', item: 'Q4 Marketing Campaign', time: '2 min ago', status: 'success' },
    { id: 2, action: 'Agent completed', item: 'Blog Post Generator', time: '15 min ago', status: 'success' },
    { id: 3, action: 'Approval pending', item: 'Product Demo Video', time: '1 hour ago', status: 'warning' },
    { id: 4, action: 'Job failed', item: 'Social Media Batch #42', time: '2 hours ago', status: 'error' },
    { id: 5, action: 'Published', item: 'Tutorial Series Ep.5', time: '3 hours ago', status: 'success' },
  ];

  const pipelineSummary = [
    { stage: 'Ideation', count: 12, progress: 100 },
    { stage: 'Script Generation', count: 8, progress: 75 },
    { stage: 'Video Production', count: 5, progress: 50 },
    { stage: 'Review & Approval', count: 3, progress: 25 },
    { stage: 'Published', count: 156, progress: 100 },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Welcome to AICF v2</h1>
        <p className="text-muted-foreground">
          Manage your AI-powered content production pipeline from one centralized dashboard.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Content Projects"
          value={kpis.totalProjects}
          description="Active and archived projects"
          trend="up"
          trendValue="12%"
        />
        <KpiCard
          title="Active AI Agents"
          value={kpis.activeAgents}
          description="Currently running agents"
          trend="neutral"
          trendValue="0%"
        />
        <KpiCard
          title="Processing Jobs"
          value={kpis.processingJobs}
          description="Jobs in queue"
          trend="down"
          trendValue="5%"
        />
        <KpiCard
          title="Published Videos"
          value={kpis.publishedVideos}
          description="Total published content"
          trend="up"
          trendValue="24%"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest actions in your workspace</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-none">{activity.action}</p>
                    <p className="text-sm text-muted-foreground">{activity.item}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        activity.status === 'success'
                          ? 'default'
                          : activity.status === 'warning'
                            ? 'secondary'
                            : activity.status === 'error'
                              ? 'destructive'
                              : 'outline'
                      }
                    >
                      {activity.status}
                    </Badge>
                    <span className="text-xs text-muted-foreground">{activity.time}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Production Pipeline Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Production Pipeline</CardTitle>
            <CardDescription>Content distribution across stages</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {pipelineSummary.map((stage) => (
              <div key={stage.stage} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{stage.stage}</span>
                  <span className="text-sm text-muted-foreground">{stage.count} items</span>
                </div>
                <Progress value={stage.progress} className="h-2" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
