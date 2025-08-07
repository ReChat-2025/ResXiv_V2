"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Bell } from "lucide-react";
import { UserProfileDropdown } from "./user-profile-dropdown";

// Types
interface Notification {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  type: 'info' | 'warning' | 'success' | 'error';
}

interface SimpleNavbarProps {
  notifications?: Notification[];
  onNotificationClick?: (notification: Notification) => void;
  onSettingClick?: (settingId: string) => void;
  onProjectClick?: (projectId: string) => void;
}

export function SimpleNavbar({ 
  notifications = [], 
  onNotificationClick,
  onSettingClick,
  onProjectClick
}: SimpleNavbarProps) {

  const unreadNotifications = notifications.filter(n => !n.read);

  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-6">
        <div className="flex h-16 items-center justify-between">
          {/* Left - Logo */}
          <div className="flex items-center">
            <div 
              className="flex items-center space-x-2 cursor-pointer hover:opacity-80 transition-opacity"
              onClick={() => window.location.href = '/projects'}
            >
              <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-bold text-sm">R</span>
              </div>
              <span className="text-xl font-bold text-foreground">ResXiv</span>
            </div>
          </div>

          {/* Right - Notifications and User Avatar */}
          <div className="flex items-center space-x-4">
            {/* Notifications */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="relative">
                  <Bell className="h-5 w-5" />
                  {unreadNotifications.length > 0 && (
                    <Badge 
                      variant="destructive" 
                      className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
                    >
                      {unreadNotifications.length}
                    </Badge>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-80">
                {notifications.length > 0 ? (
                  notifications.slice(0, 5).map((notification) => (
                    <DropdownMenuItem
                      key={notification.id}
                      className="cursor-pointer"
                      onClick={() => onNotificationClick?.(notification)}
                    >
                      <div className="flex flex-col gap-1 w-full">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-sm">{notification.title}</span>
                          {!notification.read && (
                            <Badge variant="secondary" className="h-2 w-2 rounded-full p-0" />
                          )}
                        </div>
                        <span className="text-xs text-muted-foreground">{notification.message}</span>
                        <span className="text-xs text-muted-foreground">{notification.timestamp}</span>
                      </div>
                    </DropdownMenuItem>
                  ))
                ) : (
                  <DropdownMenuItem disabled>
                    <span className="text-sm text-muted-foreground">No notifications</span>
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* User Profile Dropdown */}
            <UserProfileDropdown 
              onSettingClick={onSettingClick}
              onProjectClick={onProjectClick}
            />
          </div>
        </div>
      </div>
    </nav>
  );
} 