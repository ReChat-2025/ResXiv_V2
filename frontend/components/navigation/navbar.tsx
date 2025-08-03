"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { 
  NavigationIcon, 
  UIIcon, 
  StatusIcon,
  Icon 
} from "@/components/ui/icon";
import { layoutConstants, designSystem } from "@/lib/design-system";

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
  slug?: string;
  avatar?: string;
  avatarFallback: string;
}

interface NavbarProps {
  currentProject?: Project;
  projects?: Project[];
  showProjectSelector?: boolean;
  userAvatars?: UserAvatar[];
  notifications?: Notification[];
  onNotificationClick?: (notificationId: string) => void;
  onProjectChange?: (projectId: string) => void;
  className?: string;
}

// Navigation items configuration - removed tasks and journals
const getNavigationItems = (currentProject?: Project) => {
  const baseItems = [
    {
      id: "home",
      label: "Home", 
      icon: "home" as const,
    },
    {
      id: "papers",
      label: "Papers",
      icon: "papers" as const,
    },
    {
      id: "collaborate",
      label: "Collaborate", 
      icon: "collaborate" as const,
    },
    {
      id: "settings",
      label: "Settings",
      icon: "settings" as const,
    },
  ];

  // If we have a current project, make routes project-specific
  if (currentProject) {
    const projectSlug = currentProject.slug || currentProject.id; // Use slug if available, fallback to ID
    return baseItems.map(item => ({
      ...item,
      href: item.id === "home" 
        ? `/projects/${projectSlug}`
        : `/projects/${projectSlug}/${item.id}`
    }));
  }

  // Fallback to global routes if no project context
  return baseItems.map(item => ({
    ...item,
    href: `/${item.id}`
  }));
};

// Projects will be fetched from API via props

export function Navbar({
  currentProject,
  projects = [],
  showProjectSelector = false,
  userAvatars = [],
  notifications = [],
  onNotificationClick,
  onProjectChange,
  className,
}: NavbarProps) {
  const pathname = usePathname();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProjectDropdown, setShowProjectDropdown] = useState(false);

  const unreadCount = notifications.filter(n => !n.read).length;

  const handleNotificationClick = (notificationId: string) => {
    if (onNotificationClick) {
      onNotificationClick(notificationId);
    }
    setShowNotifications(false);
  };

  const handleProjectSelect = (projectId: string) => {
    if (onProjectChange) {
      onProjectChange(projectId);
    }
    setShowProjectDropdown(false);
  };

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <StatusIcon variant="success" size={16} />;
      case 'warning':
        return <StatusIcon variant="warning" size={16} />;
      case 'error':
        return <StatusIcon variant="error" size={16} />;
      default:
        return <StatusIcon variant="info" size={16} />;
    }
  };

  return (
    <header 
      className={cn(
        "sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-blur]:bg-background/60",
        className
      )}
      style={{ height: layoutConstants.navbar.height }}
    >
      <div className="flex h-full items-center px-6">
        {/* Left Section - Project Selector */}
        <div className="flex items-center gap-3 min-w-0 w-64">
          {showProjectSelector && currentProject ? (
            <DropdownMenu open={showProjectDropdown} onOpenChange={setShowProjectDropdown}>
              <DropdownMenuTrigger asChild>
                <Button 
                  variant="outline" 
                  className="h-9 px-3 gap-2 justify-start min-w-0"
                >
                  <Avatar className="h-6 w-6">
                    <AvatarImage src={currentProject.avatar} />
                    <AvatarFallback className="text-xs font-medium">
                      {currentProject.avatarFallback}
                    </AvatarFallback>
                  </Avatar>
                  <span className="truncate text-sm font-medium">
                    {currentProject.name}
                  </span>
                  <UIIcon variant="chevronDown" size={16} className="ml-auto" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-64">
                {projects.map((project) => (
                  <DropdownMenuItem
                    key={project.id}
                    onClick={() => handleProjectSelect(project.id)}
                    className="flex items-center gap-3"
                  >
                    <Avatar className="h-6 w-6">
                      <AvatarImage src={project.avatar} />
                      <AvatarFallback className="text-xs font-medium">
                        {project.avatarFallback}
                      </AvatarFallback>
                    </Avatar>
                    <span className="truncate">{project.name}</span>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link href="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center">
                <span className="text-primary-foreground text-sm font-bold">R</span>
              </div>
              <span className="font-bold text-lg">ResXiv</span>
            </Link>
          )}
        </div>

        {/* Center Section - Navigation */}
        <div className="flex-1 flex justify-center">
          <nav className="flex items-center gap-1">
            {getNavigationItems(currentProject).map((item) => {
              const isActive = pathname === item.href;
              
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent"
                  )}
                >
                  <NavigationIcon 
                    variant={item.icon} 
                    size={16} 
                    weight={isActive ? "fill" : "regular"}
                  />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Section - Notifications and User */}
        <div className="flex items-center justify-end space-x-3 min-w-0 w-64">
          {/* Notifications */}
          <DropdownMenu open={showNotifications} onOpenChange={setShowNotifications}>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="outline" 
                size="icon" 
                className="relative h-9 w-9 rounded-full"
              >
                <UIIcon variant="bell" size={16} />
                {unreadCount > 0 && (
                  <Badge 
                    variant="destructive" 
                    className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center"
                  >
                    <span className="text-xs font-medium">
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <div className="flex items-center justify-between p-3 border-b">
                <h4 className="font-medium">Notifications</h4>
                {unreadCount > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {unreadCount} new
                  </Badge>
                )}
              </div>
              <div className="max-h-64 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-4 text-center text-muted-foreground">
                    <UIIcon variant="bell" size={16} className="mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No notifications</p>
                  </div>
                ) : (
                  notifications.map((notification) => (
                    <DropdownMenuItem
                      key={notification.id}
                      onClick={() => handleNotificationClick(notification.id)}
                      className="flex items-start gap-3 p-3 cursor-pointer"
                    >
                      <div className="mt-0.5">
                        {getNotificationIcon(notification.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium truncate">
                            {notification.title}
                          </p>
                          <span className="text-xs text-muted-foreground flex-shrink-0">
                            {notification.timestamp}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {notification.message}
                        </p>
                        {!notification.read && (
                          <div className="w-2 h-2 bg-primary rounded-full mt-2" />
                        )}
                      </div>
                    </DropdownMenuItem>
                  ))
                )}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* User Avatars */}
          {userAvatars.length > 0 && (
            <div className="flex items-center gap-2">
              {userAvatars.map((avatar) => (
                <Avatar key={avatar.id} className="h-8 w-8">
                  <AvatarImage src={avatar.src} alt={avatar.alt} />
                  <AvatarFallback className="text-xs font-medium">
                    {avatar.fallback}
                  </AvatarFallback>
                </Avatar>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Navbar; 