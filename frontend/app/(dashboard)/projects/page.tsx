"use client";

import React, { useMemo, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProtectedRoute } from "@/components/auth/protected-route";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  FolderOpen,
  Plus,
  Search,
  MoreHorizontal,
  ChevronDown,
  Loader2,
  AlertCircle,
  Users,
  FileText,
  CheckSquare,
} from "lucide-react";
import {
  projectsConfig,
  ProjectConfig,
  ProjectStatus,
  sortProjects,
} from "@/lib/projects-config";
import { SimpleNavbar } from "@/components/navigation/simple-navbar";
import { useRouter } from "next/navigation";
import SearchInput from "@/components/ui/SearchInput";
import CreateProjectDialog from "@/components/projects/CreateProjectDialog";
import { projectsApi, Project, ProjectsQueryParams } from "@/lib/api/projects-api";


// Notification interface
interface Notification {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  type: 'info' | 'warning' | 'success' | 'error';
}

function ProjectsPage() {
  const config = projectsConfig;
  const router = useRouter();

  // State management
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("updated_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // Sample notifications - in production, fetch from API
  const [notifications] = useState<Notification[]>([
    {
      id: "1",
      title: "Project Updated",
      message: "Your project 'Research Paper Draft' has been updated by John Doe",
      timestamp: "2 minutes ago",
      read: false,
      type: "info"
    },
    {
      id: "2", 
      title: "New Collaboration",
      message: "Sarah Wilson has joined your project 'AI Research'",
      timestamp: "1 hour ago",
      read: false,
      type: "success"
    },
    {
      id: "3",
      title: "Deadline Reminder",
      message: "Your paper submission deadline is approaching in 3 days",
      timestamp: "2 hours ago", 
      read: true,
      type: "warning"
    }
  ]);

  // Fetch projects from API
  const fetchProjects = async (params: ProjectsQueryParams = {}) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await projectsApi.getProjects({
        ...params,
        sort_by: sortBy,
        sort_order: sortDirection,
        search: searchQuery || undefined,
      });
      
      setProjects(response.projects);
    } catch (error: any) {
      console.error('Failed to fetch projects:', error);
      setError(error.message || 'Failed to load projects');
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Load projects on component mount and when sort/search changes
  useEffect(() => {
    fetchProjects();
  }, [sortBy, sortDirection, searchQuery]);

  const filteredProjects = useMemo(() => {
    return projects; // Filtering is now done server-side
  }, [projects]);

  const hasProjects = projects.length > 0;

  // Handle notification click
  const handleNotificationClick = (notification: Notification) => {
    console.log("Notification clicked:", notification.id);
    // In production, mark notification as read via API
  };

  // Helper to format relative time
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const months = Math.floor(days / 30);
    const years = Math.floor(months / 12);

    if (seconds < 60) return "Just now";
    if (minutes < 60) return `${minutes} min ago`;
    if (hours < 24) return `${hours} hrs ago`;
    if (days === 1) return "1 day ago";
    if (days < 30) return `${days} days ago`;
    if (months === 1) return "1 month ago";
    if (months < 12) return `${months} months ago`;
    if (years === 1) return "1 year ago";
    return `${years} years ago`;
  };

  // Project avatar colors based on project name
  const getAvatarColor = (projectName: string) => {
    const colors = [
      "bg-primary",
      "bg-secondary", 
      "bg-accent",
      "bg-muted",
      "bg-primary"
    ];
    const index = projectName.length % colors.length;
    return colors[index];
  };

  // Handle create project action
  const handleCreateProject = () => {
    setShowCreateDialog(true);
  };

  // Handle project created
  const handleProjectCreated = (newProject: Project) => {
    setProjects(prev => [newProject, ...prev]);
    // Optionally refresh the list to get updated data
    fetchProjects();
  };

  // Handle project actions
  const handleProjectAction = async (projectId: string, action: string) => {
    console.log(`Project action: ${action} for project: ${projectId}`);
    
    switch (action) {
      case 'open':
        // Find the project to get its slug
        const project = projects.find(p => p.id === projectId);
        if (project && project.slug) {
          console.log(`Navigating to: /projects/${project.slug}`);
          router.push(`/projects/${project.slug}`);
        } else if (project) {
          // Fallback to project ID if no slug
          console.log(`Navigating to: /projects/${project.id} (no slug available)`);
          router.push(`/projects/${project.id}`);
        } else {
          console.error('Project not found:', projectId);
        }
        break;
      case 'edit':
        // TODO: Implement edit functionality
        console.log('Edit project:', projectId);
        break;
      case 'share':
        // TODO: Implement share functionality
        console.log('Share project:', projectId);
        break;
      case 'delete':
        // TODO: Implement delete functionality
        if (confirm('Are you sure you want to delete this project?')) {
          try {
            await projectsApi.deleteProject(projectId);
            setProjects(prev => prev.filter(p => p.id !== projectId));
          } catch (error: any) {
            console.error('Failed to delete project:', error);
            alert('Failed to delete project: ' + error.message);
          }
        }
        break;
    }
  };

  const EmptyState = () => (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="rounded-full bg-muted p-6 mb-4">
        <FolderOpen className="h-12 w-12 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        {config.emptyState.title}
      </h3>
      <p className="text-muted-foreground text-center mb-6 max-w-sm">
        {config.emptyState.description}
      </p>
      <Button onClick={handleCreateProject}>
        <Plus className="mr-2 h-4 w-4" />
        {config.emptyState.actionText}
      </Button>
    </div>
  );

  const ErrorState = () => (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="rounded-full bg-red-50 p-6 mb-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        Failed to Load Projects
      </h3>
      <p className="text-muted-foreground text-center mb-6 max-w-sm">
        {error}
      </p>
      <Button onClick={() => fetchProjects()}>
        Try Again
      </Button>
    </div>
  );

  const LoadingState = () => (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
      <p className="text-muted-foreground">Loading projects...</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Simplified Navigation */}
      <SimpleNavbar 
        notifications={notifications}
        onNotificationClick={handleNotificationClick}
      />

      {/* Main Content */}
      <div className="container mx-auto px-6 py-8">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight text-foreground">
            Welcome to ResXiv
          </h1>
        </div>

        {/* Controls Section */}
        <div className="flex items-center justify-between mb-8">
          {/* Left - New Project Button */}
          <Button 
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
            onClick={handleCreateProject}
          >
            <Plus className="mr-2 h-4 w-4" />
            {config.actions.create.text}
          </Button>

          {/* Right - Search, Sort, Filter */}
          <div className="flex items-center gap-4">
            {/* Search Input */}
            <SearchInput
              placeholder={config.actions.search.placeholder}
              value={searchQuery}
              onChange={setSearchQuery}
            />

            {/* Sort Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2">
                  Sort
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => {
                    setSortBy('updated_at');
                    setSortDirection('desc');
                  }}
                >
                  Recently Updated
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    setSortBy('created_at');
                    setSortDirection('desc');
                  }}
                >
                  Recently Created
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    setSortBy('name');
                    setSortDirection('asc');
                  }}
                >
                  Name (A-Z)
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    setSortBy('name');
                    setSortDirection('desc');
                  }}
                >
                  Name (Z-A)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Filter Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2">
                  Filter
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {config.actions.filter.options.map((opt) => (
                  <DropdownMenuItem key={opt.id}>
                    {opt.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Projects Content */}
        {isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState />
        ) : !hasProjects ? (
          <EmptyState />
        ) : (
          <div className="border rounded-lg bg-background">
            <Table>
              <TableHeader>
                <TableRow className="border-b">
                  <TableHead className="font-medium text-muted-foreground">Name</TableHead>
                  <TableHead className="font-medium text-muted-foreground">Members</TableHead>
                  <TableHead className="font-medium text-muted-foreground">Papers</TableHead>
                  <TableHead className="font-medium text-muted-foreground">Tasks</TableHead>
                  <TableHead className="font-medium text-muted-foreground">Last modified</TableHead>
                  <TableHead className="font-medium text-muted-foreground">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProjects.map((project) => (
                  <TableRow 
                    key={project.id} 
                    className="hover:bg-muted/50 cursor-pointer"
                    onClick={() => handleProjectAction(project.id, 'open')}
                  >
                    <TableCell className="py-4">
                      <div className="flex items-center gap-3">
                        <Avatar className={`h-10 w-10 ${getAvatarColor(project.name)}`}>
                          <AvatarFallback className="text-primary-foreground font-medium">
                            {project.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex flex-col">
                          <span className="font-medium">{project.name}</span>
                          {project.description && (
                            <span className="text-sm text-muted-foreground truncate max-w-xs">
                              {project.description}
                            </span>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground py-4">
                      <div className="flex items-center gap-1">
                        <Users className="h-4 w-4" />
                        <span>{project.member_count}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground py-4">
                      <div className="flex items-center gap-1">
                        <FileText className="h-4 w-4" />
                        <span>{project.paper_count}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground py-4">
                      <div className="flex items-center gap-1">
                        <CheckSquare className="h-4 w-4" />
                        <span>{project.task_count}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground py-4">
                      {formatRelativeTime(project.updated_at)}
                    </TableCell>
                    <TableCell className="py-4">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-8 w-8"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleProjectAction(project.id, 'open')}>
                            Open
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleProjectAction(project.id, 'edit')}>
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleProjectAction(project.id, 'share')}>
                            Share
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            className="text-destructive"
                            onClick={() => handleProjectAction(project.id, 'delete')}
                          >
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onProjectCreated={handleProjectCreated}
      />
    </div>
  );
}

export default function ProtectedProjectsPage() {
  return (
    <ProtectedRoute>
      <ProjectsPage />
    </ProtectedRoute>
  );
} 