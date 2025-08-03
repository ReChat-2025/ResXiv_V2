"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { projectsApi } from "@/lib/api/projects-api";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { PageLayout } from "@/components/layout/page-layout";
import { CollaborateSidebar } from "@/components/collaborate/CollaborateSidebar";
import { KanbanBoard } from "@/components/tasks/KanbanBoard";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { 
  appConfig, 
  mockTeamMembers, 
  getTeamMembersByProject,
  type TeamMember 
} from "@/lib/config/app-config";
import { tasksApi } from "@/lib/api/tasks-api";

interface Notification {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  type: 'info' | 'warning' | 'success' | 'error';
}

interface Project {
  id: string;
  name: string;
  avatar?: string;
  avatarFallback: string;
}

const mockNotifications: Notification[] = [
  {
    id: "1",
    title: "Task Assigned",
    message: "You have been assigned a new task",
    timestamp: "2 minutes ago",
    read: false,
    type: "info"
  },
  {
    id: "2",
    title: "Task Completed",
    message: "Your task has been marked as completed",
    timestamp: "1 hour ago",
    read: false,
    type: "success"
  }
];

function ProjectTasksPage() {
  const router = useRouter();
  const params = useParams();
  const projectSlug = params.projectSlug as string;
  
  // Current selected section state
  const [selectedSection, setSelectedSection] = useState('tasks');
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [isProjectLoading, setIsProjectLoading] = useState(true);
  
  // Team members for sidebar (using mock data for now)
  const teamMembers = currentProject 
    ? getTeamMembersByProject(currentProject.id)
    : mockTeamMembers;
  
  // Fetch project data based on slug
  useEffect(() => {
    const fetchProject = async () => {
      if (projectSlug) {
        try {
          setIsProjectLoading(true);
          // Get all projects to find the one with matching slug
          const projectsResponse = await projectsApi.getProjects();
          const project = projectsResponse.projects.find((p: any) => 
            p.slug === projectSlug || p.id === projectSlug
          );
          
          if (project) {
            setCurrentProject({
              id: project.id,
              name: project.name,
              avatarFallback: project.name.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase(),
            });
          } else {
            // Project not found, redirect to projects
            router.push('/projects');
          }
        } catch (error) {
          console.error('Failed to fetch project:', error);
          router.push('/projects');
        } finally {
          setIsProjectLoading(false);
        }
      }
    };

    fetchProject();
  }, [projectSlug, router]);

  // Event handlers
  const handleAddMember = () => {
    console.log("Add team member");
    // In production: open add member modal or navigate to team management
  };

  const handleNotificationClick = (notificationId: string) => {
    console.log("Notification clicked:", notificationId);
  };

  const handleProjectChange = (projectId: string) => {
    // Find project by ID and navigate to its slug
    projectsApi.getProjects().then(response => {
      const project = response.projects.find((p: any) => p.id === projectId);
      if (project && project.slug) {
        router.push(`/projects/${project.slug}/tasks`);
      } else if (project) {
        // Fallback to ID if no slug
        router.push(`/projects/${project.id}/tasks`);
      }
    });
  };

  if (isProjectLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading tasks...</p>
        </div>
      </div>
    );
  }

  return (
    <PageLayout
      currentProject={currentProject || undefined}
      showProjectSelector={true}
      userAvatars={[
        { 
          id: "current-user", 
          fallback: teamMembers[0]?.name.split(' ').map(n => n[0]).join('').toUpperCase() || "JS" 
        }
      ]}
      notifications={mockNotifications}
      onNotificationClick={handleNotificationClick}
      onProjectChange={handleProjectChange}
    >
      <div className="flex h-full overflow-hidden">
        {/* Left Sidebar */}
        <CollaborateSidebar
          teamMembers={teamMembers}
          onAddMember={handleAddMember}
          maxDisplayMembers={appConfig.features.maxVisibleAvatars}
          title="Collaborate"
          showCalendar={true}
          selectedSection="tasks"
          onSectionChange={(section) => {
            // Handle section changes if needed
            if (section !== 'tasks') {
              // Navigate to other sections or handle as needed
              console.log('Section changed to:', section);
            }
          }}
        />

        {/* Main Kanban Board */}
        <div className="flex-1 flex flex-col bg-background">
          {/* Header */}
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-foreground">Tasks Board</h1>
                <p className="text-muted-foreground">
                  Manage your project tasks with drag and drop
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm">
                  <Icon name="Funnel" size={16} className="mr-2" />
                  Filter
                </Button>
                <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground">
                  <Icon name="Plus" size={16} className="mr-2" />
                  New Task
                </Button>
              </div>
            </div>
          </div>
          
          {/* Kanban Board */}
          {currentProject ? (
            <KanbanBoard projectId={currentProject.id} />
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                <p className="text-muted-foreground">Loading project...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}

export default function ProtectedProjectTasksPage() {
  return (
    <ProtectedRoute>
      <ProjectTasksPage />
    </ProtectedRoute>
  );
} 