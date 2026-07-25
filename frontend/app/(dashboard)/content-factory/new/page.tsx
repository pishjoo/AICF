'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ProjectForm, type ProjectFormValues } from '@/components/content/ProjectForm';
import type { ContentType, TargetPlatform, Language } from '@/types/content';

export default function NewContentProjectPage() {
  const router = useRouter();

  const handleSubmit = async (data: ProjectFormValues) => {
    // Mock submission - in real app this would call API
    console.log('Creating project:', data);
    
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 500));
    
    // Redirect to projects list after creation
    router.push('/content-factory');
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-4">
        <Link href="/content-factory">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Create New Project</h1>
          <p className="text-muted-foreground mt-1">
            Set up a new content production project
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="max-w-2xl">
        <ProjectForm onSubmit={handleSubmit} submitLabel="Create Project" />
      </div>
    </div>
  );
}
