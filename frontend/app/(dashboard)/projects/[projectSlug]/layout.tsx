"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { projectsApi } from "@/lib/api/projects-api";
import { PageLayout } from "@/components/layout/page-layout";

interface Project {
  id: string;
  name: string;
  slug?: string;
  avatar?: string;
  avatarFallback: string;
}

interface ProjectLayoutProps {
  children: React.ReactNode;
}

export default function ProjectLayout({ children }: ProjectLayoutProps) {
  const router = useRouter();
  const params = useParams();
  const projectSlug = params.projectSlug as string;
  
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch project data based on slug
  useEffect(() => {
    const fetchProject = async () => {
      if (projectSlug) {
        try {
          setIsLoading(true);
          const projectsResponse = await projectsApi.getProjects();
          const project = projectsResponse.projects.find((p: any) => 
            p.slug === projectSlug || p.id === projectSlug
          );
          
          if (project) {
            setCurrentProject({
              id: project.id,
              name: project.name,
              slug: project.slug || project.id, // Use slug if available, fallback to ID
              avatarFallback: project.name.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase(),
            });
          } else {
            // Project not found, redirect to projects list
            router.push('/projects');
          }
        } catch (error) {
          console.error('Failed to fetch project:', error);
          // On API error, redirect to projects list
          router.push('/projects');
        } finally {
          setIsLoading(false);
        }
      }
    };

    fetchProject();
  }, [projectSlug, router]);

  // Handle project change from navbar
  const handleProjectChange = (projectId: string) => {
    // Find project by ID and navigate to its home page
    projectsApi.getProjects().then(response => {
      const project = response.projects.find((p: any) => p.id === projectId);
      if (project && project.slug) {
        router.push(`/projects/${project.slug}`);
      } else if (project) {
        // Fallback to ID if no slug
        router.push(`/projects/${project.id}`);
      }
    }).catch(() => {
      // Fallback - just use the projectId
      router.push(`/projects/${projectId}`);
    });
  };

  // Show loading state while fetching project
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // If no project found, this will have already redirected
  if (!currentProject) {
    return null;
  }

  return (
    <PageLayout
      currentProject={currentProject}
      showProjectSelector={true}
      onProjectChange={handleProjectChange}
    >
      {children}
    </PageLayout>
  );
} 