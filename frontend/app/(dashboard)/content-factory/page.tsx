import Link from 'next/link';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ProjectCard } from '@/components/content/ProjectCard';
import { sampleContentProjects } from '@/lib/mock-data';

export default function ContentFactoryPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Content Factory</h1>
          <p className="text-muted-foreground mt-1">
            Manage your content production projects and pipelines
          </p>
        </div>
        <Link href="/content-factory/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create New Project
          </Button>
        </Link>
      </div>

      {/* Projects Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {sampleContentProjects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>

      {/* Empty State - shown when no projects exist */}
      {sampleContentProjects.length === 0 && (
        <div className="text-center py-12 border-2 border-dashed rounded-lg">
          <h3 className="text-lg font-medium mt-4">No projects yet</h3>
          <p className="text-muted-foreground mt-2">
            Get started by creating your first content project
          </p>
          <Link href="/content-factory/new" className="mt-4 inline-block">
            <Button variant="outline">
              <Plus className="mr-2 h-4 w-4" />
              Create New Project
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
