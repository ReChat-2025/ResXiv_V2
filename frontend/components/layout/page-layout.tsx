"use client";

import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Navbar } from "@/components/navigation/navbar";
import { layoutConstants } from "@/lib/design-system";
import { projectsApi } from "@/lib/api/projects-api";
import { userApi } from "@/lib/api/user-api";

// Types
interface Notification {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  type: 'info' | 'warning' | 'success' | 'error';
}

interface UserAvatar {
  id: string;
  src?: string;
  fallback: string;
  alt?: string;
}

interface Project {
  id: string;
  name: string;
  avatar?: string;
  avatarFallback: string;
}

interface PageLayoutProps {
  children: React.ReactNode;
  currentProject?: Project;
  showProjectSelector?: boolean;
  userAvatars?: UserAvatar[];
  notifications?: Notification[];
  onNotificationClick?: (notificationId: string) => void;
  onProjectChange?: (projectId: string) => void;
  className?: string;
  contentClassName?: string;
  showNavbar?: boolean;
}

export function PageLayout({
  children,
  currentProject,
  showProjectSelector = true,
  userAvatars: propUserAvatars,
  notifications: propNotifications,
  onNotificationClick,
  onProjectChange,
  className,
  contentClassName,
  showNavbar = true,
}: PageLayoutProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [userAvatars, setUserAvatars] = useState<UserAvatar[]>(propUserAvatars || []);
  const [notifications, setNotifications] = useState<Notification[]>(propNotifications || []);
  const [isLoadingUser, setIsLoadingUser] = useState(true);

  // Fetch projects for the dropdown
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const response = await projectsApi.getProjects({ size: 10 });
        const transformedProjects = response.projects.map(p => ({
          id: p.id,
          name: p.name,
          avatarFallback: p.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase(),
        }));
        setProjects(transformedProjects);
      } catch (error) {
        console.error('Failed to fetch projects for navbar:', error);
        // Keep empty array as fallback
      }
    };

    if (showProjectSelector) {
      fetchProjects();
    }
  }, [showProjectSelector]);

  // Fetch user data for avatar if not provided via props
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        setIsLoadingUser(true);
        const user = await userApi.getCurrentUser();
        
        // Set user avatar if not provided via props
        if (!propUserAvatars || propUserAvatars.length === 0) {
          setUserAvatars([{
            id: user.id,
            fallback: user.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase(),
            alt: user.name,
          }]);
        }

        // Set mock notifications if not provided via props (since backend may not be running)
        if (!propNotifications || propNotifications.length === 0) {
          setNotifications([
            {
              id: "1",
              title: "Project Updated",
              message: `Project ${currentProject?.name || 'ResXiv'} has been updated`,
              timestamp: "2 min ago",
              read: false,
              type: "info"
            },
            {
              id: "2", 
              title: "New Collaboration",
              message: "A team member has joined your project",
              timestamp: "1 hour ago",
              read: false,
              type: "success"
            },
            {
              id: "3",
              title: "Task Reminder",
              message: "You have pending tasks to review",
              timestamp: "2 hours ago", 
              read: true,
              type: "warning"
            }
          ]);
        }
      } catch (error) {
        console.error('Failed to fetch user data:', error);
        // Use fallback avatar if API fails
        if (!propUserAvatars || propUserAvatars.length === 0) {
          setUserAvatars([{
            id: "fallback-user",
            fallback: "US",
            alt: "User",
          }]);
        }
      } finally {
        setIsLoadingUser(false);
      }
    };

    fetchUserData();
  }, [currentProject?.name, propUserAvatars, propNotifications]);

  const handleNotificationClick = (notificationId: string) => {
    // Mark notification as read
    setNotifications(prev => 
      prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
    );
    
    // Call the provided handler if available
    if (onNotificationClick) {
      onNotificationClick(notificationId);
    }
  };

  return (
    <div className={cn("min-h-screen bg-background", className)}>
      {/* Navigation */}
      {showNavbar && (
        <Navbar
          currentProject={currentProject}
          projects={projects}
          showProjectSelector={showProjectSelector}
          userAvatars={userAvatars}
          notifications={notifications}
          onNotificationClick={handleNotificationClick}
          onProjectChange={onProjectChange}
        />
      )}

      {/* Main Content */}
      <main 
        className={cn(
          "flex-1",
          showNavbar ? "h-[calc(100vh-3.5rem)]" : "h-screen",
          contentClassName
        )}
      >
        {children}
      </main>
    </div>
  );
}

// Specialized layout components for different page types
interface SidebarLayoutProps extends PageLayoutProps {
  sidebar: React.ReactNode;
  sidebarWidth?: string;
  sidebarCollapsed?: boolean;
  onSidebarToggle?: () => void;
}

export function SidebarLayout({
  children,
  sidebar,
  sidebarWidth = "16rem",
  sidebarCollapsed = false,
  onSidebarToggle,
  ...pageLayoutProps
}: SidebarLayoutProps) {
  return (
    <PageLayout {...pageLayoutProps}>
      <div className="flex h-full overflow-hidden">
        {/* Sidebar */}
        <aside 
          className={cn(
            "border-r bg-card transition-all duration-300 ease-in-out",
            sidebarCollapsed ? "w-16" : `w-[${sidebarWidth}]`
          )}
        >
          {sidebar}
        </aside>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {children}
        </div>
      </div>
    </PageLayout>
  );
}

interface ThreeColumnLayoutProps extends PageLayoutProps {
  leftSidebar?: React.ReactNode;
  rightSidebar?: React.ReactNode;
  leftSidebarWidth?: string;
  rightSidebarWidth?: string;
  leftSidebarCollapsed?: boolean;
  rightSidebarCollapsed?: boolean;
  onLeftSidebarToggle?: () => void;
  onRightSidebarToggle?: () => void;
}

export function ThreeColumnLayout({
  children,
  leftSidebar,
  rightSidebar,
  leftSidebarWidth = "16rem",
  rightSidebarWidth = "20rem",
  leftSidebarCollapsed = false,
  rightSidebarCollapsed = false,
  onLeftSidebarToggle,
  onRightSidebarToggle,
  ...pageLayoutProps
}: ThreeColumnLayoutProps) {
  return (
    <PageLayout {...pageLayoutProps}>
      <div className="flex h-full overflow-hidden">
        {/* Left Sidebar */}
        {leftSidebar && (
          <aside 
            className={cn(
              "border-r bg-card transition-all duration-300 ease-in-out",
              leftSidebarCollapsed ? "w-16" : `w-[${leftSidebarWidth}]`
            )}
          >
            {leftSidebar}
          </aside>
        )}

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {children}
        </div>

        {/* Right Sidebar */}
        {rightSidebar && (
          <aside 
            className={cn(
              "border-l bg-card transition-all duration-300 ease-in-out",
              rightSidebarCollapsed ? "w-16" : `w-[${rightSidebarWidth}]`
            )}
          >
            {rightSidebar}
          </aside>
        )}
      </div>
    </PageLayout>
  );
}

// Content wrapper for consistent padding and max-width
interface ContentWrapperProps {
  children: React.ReactNode;
  className?: string;
  maxWidth?: string;
  padding?: 'sm' | 'md' | 'lg' | 'xl';
}

export function ContentWrapper({
  children,
  className,
  maxWidth = layoutConstants.content.maxWidth,
  padding = 'lg',
}: ContentWrapperProps) {
  const paddingClasses = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
    xl: 'p-12',
  };

  return (
    <div 
      className={cn(
        "mx-auto w-full",
        paddingClasses[padding],
        className
      )}
      style={{ maxWidth }}
    >
      {children}
    </div>
  );
}

// Empty state component for consistent empty states
interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn(
      "flex flex-col items-center justify-center py-16 px-4 text-center",
      className
    )}>
      {icon && (
        <div className="mb-4 text-muted-foreground">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-foreground mb-2">
        {title}
      </h3>
      {description && (
        <p className="text-muted-foreground mb-6 max-w-sm">
          {description}
        </p>
      )}
      {action && (
        <div className="flex items-center gap-2">
          {action}
        </div>
      )}
    </div>
  );
}

export default PageLayout; 