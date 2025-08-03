"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Icon } from "@/components/ui/icon";
import { CalendarWidget } from "./CalendarWidget";
import { appConfig, type TeamMember } from "@/lib/config/app-config";

interface CollaborateSidebarProps {
  teamMembers?: TeamMember[];
  onAddMember?: () => void;
  maxDisplayMembers?: number;
  title?: string;
  showCalendar?: boolean;
  className?: string;
  isLoading?: boolean;
  selectedSection?: string;
  onSectionChange?: (section: string) => void;
}

export function CollaborateSidebar({
  teamMembers = [],
  onAddMember,
  maxDisplayMembers,
  title,
  showCalendar = true,
  className = "",
  isLoading = false,
  selectedSection = 'messages',
  onSectionChange
}: CollaborateSidebarProps) {

  // Get configuration values
  const config = appConfig;
  const maxDisplay = maxDisplayMembers ?? config.features.maxVisibleAvatars;
  const sidebarTitle = title ?? "Collaborate";
  
  // Calculate display members
  const displayMembers = teamMembers.slice(0, maxDisplay);
  const remainingCount = Math.max(0, teamMembers.length - maxDisplay);

  const handleAddMember = () => {
    onAddMember?.();
  };

  const handleSectionClick = (section: string) => {
    onSectionChange?.(section);
  };

  const getStatusDotColor = (status: TeamMember['status']) => {
    const statusColors = {
      online: "bg-green-500",
      away: "bg-yellow-500", 
      busy: "bg-red-500",
      offline: "bg-muted-foreground/30"
    };
    return statusColors[status] || statusColors.offline;
  };

  // Navigation options
  const navigationOptions = [
    { id: 'messages', label: 'Messages', icon: 'ChatCircle' },
    { id: 'tasks', label: 'Tasks', icon: 'CheckSquare' },
    { id: 'journals', label: 'Journals', icon: 'Book' }
  ];

  return (
    <aside className={`w-80 bg-card border-r border-border flex flex-col ${className}`}>
      {/* Header Section */}
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-semibold text-foreground mb-4">{sidebarTitle}</h1>
        
        {/* Team Members and Add Button */}
        <div className="flex items-center justify-between gap-3">
          {/* Team Members Avatars */}
          <div className="flex -space-x-2">
            {isLoading ? (
              <div className="h-10 w-10 rounded-full bg-muted animate-pulse"></div>
            ) : displayMembers.length > 0 ? (
              <>
                {displayMembers.map((member) => (
                  <div key={member.id} className="relative">
                    <Avatar className="h-10 w-10 border-2 border-card">
                      <AvatarImage src={member.avatar} alt={member.name} />
                      <AvatarFallback className="text-sm bg-muted font-medium text-muted-foreground">
                        {member.name.split(' ').map(n => n[0]).join('').toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    {/* Status indicator */}
                    <div 
                      className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-card ${getStatusDotColor(member.status)}`}
                      title={`${member.status.charAt(0).toUpperCase() + member.status.slice(1)}`}
                    />
                  </div>
                ))}
                {remainingCount > 0 && (
                  <div className="h-10 w-10 rounded-full bg-muted border-2 border-card flex items-center justify-center">
                    <span className="text-sm font-medium text-muted-foreground">{remainingCount}</span>
                  </div>
                )}
              </>
            ) : (
              <div className="h-10 w-10 rounded-full bg-muted border-2 border-card flex items-center justify-center">
                <span className="text-xs text-muted-foreground">No members</span>
              </div>
            )}
          </div>

          {/* Add Button */}
          <Button 
            onClick={handleAddMember}
            className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2 rounded-lg h-10 px-6 flex-shrink-0"
            disabled={isLoading}
          >
            <Icon name="UserPlus" size={16} weight="regular" />
            Add
          </Button>
        </div>
      </div>

      {/* Navigation Section */}
      <div className="p-6 space-y-2 border-b border-border">
        {navigationOptions.map((option) => (
          <button
            key={option.id}
            onClick={() => handleSectionClick(option.id)}
            className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all duration-200 text-left ${
              selectedSection === option.id
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground'
            }`}
          >
            <Icon 
              name={option.icon as any} 
              size={20} 
              weight="regular" 
              className={selectedSection === option.id ? 'text-primary-foreground' : 'text-muted-foreground'}
            />
            <span className="flex-1 font-medium">{option.label}</span>
          </button>
        ))}
      </div>

      {/* Calendar Widget */}
      {showCalendar && (
        <div className="flex-1 p-6 pt-0">
          <CalendarWidget 
            currentMonth={5} // June (0-indexed)
            currentYear={2024}
            onDateSelect={(date) => console.log('Date selected:', date)}
          />
        </div>
      )}
    </aside>
  );
} 