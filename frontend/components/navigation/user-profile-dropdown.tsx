"use client";

import React, { useState, useEffect } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Icon } from "@/components/ui/icon";
import { userApi, type UserResponse, type UserStats } from "@/lib/api/user-api";
import { projectsApi, type Project } from "@/lib/api/projects-api";
// Using simple scrollable div instead of ScrollArea

// User settings configuration following auth API endpoints
const userSettingsSections = [
  {
    id: "profile",
    label: "Profile",
    iconName: "User",
    description: "Update profile information",
    endpoint: "/api/v1/auth/me"
  },
  {
    id: "security",
    label: "Password & Security",
    iconName: "Shield",
    description: "Change password and security settings",
    endpoint: "/api/v1/auth/me/change-password"
  },
  {
    id: "account",
    label: "Account Settings",
    iconName: "Settings",
    description: "Delete account and data management",
    endpoint: "/api/v1/auth/me"
  },
  {
    id: "stats",
    label: "Statistics",
    iconName: "ChartBar",
    description: "View your activity statistics",
    endpoint: "/api/v1/auth/me/stats"
  },
  {
    id: "logout",
    label: "Sign Out",
    iconName: "SignOut",
    description: "Sign out of your account",
    endpoint: "/api/v1/auth/logout"
  }
];

interface UserProfileDropdownProps {
  onSettingClick?: (settingId: string) => void;
  onProjectClick?: (projectId: string) => void;
  onSignOut?: () => void;
}

export function UserProfileDropdown({
  onSettingClick,
  onProjectClick,
  onSignOut
}: UserProfileDropdownProps) {
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        // Fetch user profile and stats in parallel
        const [user, stats] = await Promise.all([
          userApi.getCurrentUser(),
          userApi.getUserStats().catch(() => null), // Don't fail if stats unavailable
        ]);
        setCurrentUser(user);
        setUserStats(stats);
      } catch (error) {
        console.warn('Failed to fetch current user:', error);
      }
    };

    fetchUserData();
  }, []);

  useEffect(() => {
    const fetchProjects = async () => {
      if (!isOpen) return;
      
      setProjectsLoading(true);
      try {
        const response = await projectsApi.getProjects({ 
          size: 50, // Get more projects for the dropdown
          sort_by: "updated_at",
          sort_order: "desc"
        });
        setProjects(response.projects);
      } catch (error) {
        console.warn('Failed to fetch projects:', error);
        setProjects([]);
      } finally {
        setProjectsLoading(false);
      }
    };

    fetchProjects();
  }, [isOpen]);

  const handleSettingClick = async (settingId: string) => {
    if (settingId === 'logout') {
      // Handle logout directly
      await handleSignOut();
      return;
    }
    
    if (onSettingClick) {
      onSettingClick(settingId);
    } else {
      // Default behavior - navigate to settings page with section
      window.location.href = `/settings?section=${settingId}`;
    }
    setIsOpen(false);
  };

  const handleProjectClick = (projectId: string) => {
    if (onProjectClick) {
      onProjectClick(projectId);
    } else {
      // Default behavior - navigate to project
      const project = projects.find(p => p.id === projectId);
      const slug = project?.slug || projectId;
      window.location.href = `/projects/${slug}`;
    }
    setIsOpen(false);
  };

  const handleSignOut = async () => {
    if (onSignOut) {
      onSignOut();
    } else {
      // Default sign out behavior with backend integration
      try {
        await userApi.completeLogout();
        window.location.href = '/login?message=Logged out successfully';
      } catch (error) {
        console.error('Logout error:', error);
        // Fallback: clear tokens and redirect anyway
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login?message=Logged out locally';
      }
    }
    setIsOpen(false);
  };

  const getProjectAvatarFallback = (project: Project) => {
    return project.name
      .split(' ')
      .map(word => word[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="relative h-10 w-10 rounded-full">
          <Avatar className="h-9 w-9">
            <AvatarImage src={undefined} alt={currentUser?.name || 'User'} />
            <AvatarFallback>
              {currentUser?.name ? 
                currentUser.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() :
                'U'
              }
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-80 p-0">
        {/* User Profile Header */}
        <div className="p-4 border-b">
          <div className="flex items-center gap-3">
            <Avatar className="h-12 w-12">
              <AvatarImage src={undefined} alt={currentUser?.name || 'User'} />
              <AvatarFallback className="text-lg">
                {currentUser?.name ? 
                  currentUser.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() :
                  'U'
                }
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-foreground truncate">
                {currentUser?.name || 'User'}
              </div>
              <div className="text-sm text-muted-foreground truncate">
                {currentUser?.email || ''}
              </div>
              <div className="flex items-center gap-2 mt-1">
                {currentUser?.email_verified ? (
                  <Badge variant="secondary" className="text-xs px-1.5 py-0.5">
                    <Icon name="CheckCircle" size={10} className="mr-1" />
                    Verified
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-xs px-1.5 py-0.5">
                    <Icon name="Warning" size={10} className="mr-1" />
                    Unverified
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* User Settings Section */}
        <div className="p-3">
          <DropdownMenuLabel className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-0 pb-2">
            Account Settings
          </DropdownMenuLabel>
          <div className="space-y-1">
            {userSettingsSections.map((setting) => (
              <DropdownMenuItem
                key={setting.id}
                onClick={() => handleSettingClick(setting.id)}
                className="flex items-center gap-3 px-2 py-2 cursor-pointer rounded-md"
              >
                <Icon 
                  name={setting.iconName as any}
                  size={16} 
                  weight="regular"
                  className="text-muted-foreground"
                />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{setting.label}</div>
                  <div className="text-xs text-muted-foreground truncate">
                    {setting.description}
                  </div>
                </div>
              </DropdownMenuItem>
            ))}
          </div>
        </div>

        <DropdownMenuSeparator />

        {/* User Statistics Section */}
        {userStats && (
          <>
            <div className="px-3 py-2">
              <DropdownMenuLabel className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-0 pb-2">
                Quick Stats
              </DropdownMenuLabel>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="flex flex-col items-center space-y-1">
                  <div className="text-lg font-semibold text-foreground">
                    {userStats.projects_count}
                  </div>
                  <div className="text-xs text-muted-foreground">Projects</div>
                </div>
                <div className="flex flex-col items-center space-y-1">
                  <div className="text-lg font-semibold text-foreground">
                    {userStats.papers_count}
                  </div>
                  <div className="text-xs text-muted-foreground">Papers</div>
                </div>
                <div className="flex flex-col items-center space-y-1">
                  <div className="text-lg font-semibold text-foreground">
                    {userStats.interests_count}
                  </div>
                  <div className="text-xs text-muted-foreground">Interests</div>
                </div>
              </div>
            </div>
            <DropdownMenuSeparator />
          </>
        )}

        {/* Projects Section */}
        <div className="p-3">
          <DropdownMenuLabel className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-0 pb-2 flex items-center justify-between">
            <span>Your Projects</span>
            <Badge variant="secondary" className="text-xs">
              {projects.length}
            </Badge>
          </DropdownMenuLabel>
          
          <div className="h-48 overflow-y-auto">
            <div className="space-y-1 pr-2">
              {projectsLoading ? (
                <div className="flex items-center justify-center py-6">
                  <Icon name="CircleNotch" size={16} className="animate-spin text-muted-foreground" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading projects...</span>
                </div>
              ) : projects.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-6 text-center">
                  <Icon name="Folder" size={24} className="text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">No projects yet</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Create your first project to get started
                  </p>
                </div>
              ) : (
                projects.map((project) => (
                  <DropdownMenuItem
                    key={project.id}
                    onClick={() => handleProjectClick(project.id)}
                    className="flex items-center gap-3 px-2 py-2 cursor-pointer rounded-md"
                  >
                    <Avatar className="h-8 w-8 flex-shrink-0">
                      <AvatarImage src={undefined} />
                      <AvatarFallback className="text-xs font-medium">
                        {getProjectAvatarFallback(project)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">
                        {project.name}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Icon 
                            name={project.is_private ? "Lock" : "Globe"} 
                            size={10} 
                          />
                          <span>{project.is_private ? 'Private' : 'Public'}</span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {project.member_count} member{project.member_count !== 1 ? 's' : ''}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Badge variant="outline" className="text-xs px-1.5 py-0.5">
                        {project.current_user_role || 'Member'}
                      </Badge>
                    </div>
                  </DropdownMenuItem>
                ))
              )}
            </div>
          </div>
        </div>

        <DropdownMenuSeparator />

        {/* Footer Actions */}
        <div className="p-3 space-y-1">
          <DropdownMenuItem
            onClick={() => window.location.href = '/projects/new'}
            className="flex items-center gap-3 px-2 py-2 cursor-pointer rounded-md"
          >
            <Icon name="Plus" size={16} className="text-muted-foreground" />
            <span className="font-medium text-sm">Create New Project</span>
          </DropdownMenuItem>
          
          <DropdownMenuItem
            onClick={handleSignOut}
            className="flex items-center gap-3 px-2 py-2 cursor-pointer rounded-md text-destructive focus:text-destructive"
          >
            <Icon name="SignOut" size={16} />
            <span className="font-medium text-sm">Sign Out</span>
          </DropdownMenuItem>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default UserProfileDropdown; 