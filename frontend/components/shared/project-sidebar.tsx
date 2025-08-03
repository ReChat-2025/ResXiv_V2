"use client";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  ChevronLeft,
  ChevronRight,
  MessageCircle,
  BookOpen,
  CheckSquare,
  UserPlus
} from "lucide-react";

interface TeamMember {
  id: string;
  name: string;
  avatar?: string;
  fallback: string;
  status: 'online' | 'offline' | 'away';
  role?: string;
}

interface SidebarMenuItem {
  id: string;
  label: string;
  icon: string;
  badge?: {
    text: string;
    variant: 'default' | 'secondary' | 'destructive' | 'outline';
  };
  href: string;
}

interface CalendarDay {
  date: number;
  isCurrentMonth: boolean;
  isToday?: boolean;
  hasEvents?: boolean;
}

interface ProjectSidebarConfig {
  title: string;
  teamSection: {
    showCount: boolean;
    maxVisibleAvatars: number;
    addButtonText: string;
  };
  menuItems: SidebarMenuItem[];
  showCalendar?: boolean;
}

interface ProjectSidebarProps {
  config: ProjectSidebarConfig;
  teamMembers?: TeamMember[];
  currentMonth?: number;
  currentYear?: number;
}

export function ProjectSidebar({
  config,
  teamMembers = [],
  currentMonth = 5, // June (0-indexed)
  currentYear = 2024
}: ProjectSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [calendarMonth, setCalendarMonth] = useState(currentMonth);
  const [calendarYear, setCalendarYear] = useState(currentYear);

  // Icon mapping
  const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
    MessageCircle,
    BookOpen,
    CheckSquare,
    UserPlus,
  };

  // Calendar utilities
  const generateCalendarDays = (month: number, year: number): CalendarDay[] => {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    const days: CalendarDay[] = [];
    const today = new Date();
    
    for (let i = 0; i < 42; i++) {
      const currentDate = new Date(startDate);
      currentDate.setDate(startDate.getDate() + i);
      
      days.push({
        date: currentDate.getDate(),
        isCurrentMonth: currentDate.getMonth() === month,
        isToday: currentDate.toDateString() === today.toDateString(),
        hasEvents: false
      });
    }
    
    return days;
  };

  const getVisibleMembers = (members: TeamMember[], maxVisible: number) => {
    return members.slice(0, maxVisible);
  };

  const getHiddenMemberCount = (members: TeamMember[], maxVisible: number) => {
    return Math.max(0, members.length - maxVisible);
  };

  // Calendar data
  const calendarDays = generateCalendarDays(calendarMonth, calendarYear);
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const dayNames = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

  // Navigation for calendar
  const navigateMonth = (direction: 'prev' | 'next') => {
    if (direction === 'prev') {
      if (calendarMonth === 0) {
        setCalendarMonth(11);
        setCalendarYear(calendarYear - 1);
      } else {
        setCalendarMonth(calendarMonth - 1);
      }
    } else {
      if (calendarMonth === 11) {
        setCalendarMonth(0);
        setCalendarYear(calendarYear + 1);
      } else {
        setCalendarMonth(calendarMonth + 1);
      }
    }
  };

  // Handle menu item click
  const handleMenuItemClick = (href: string) => {
    router.push(href);
  };

  // Handle add team member
  const handleAddTeamMember = () => {
    console.log("Add team member");
  };

  return (
    <aside className="w-80 border-r bg-background flex flex-col h-full">
      {/* Sidebar header */}
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold mb-4">{config.title}</h2>
        
        {/* Team members */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            {teamMembers.length > 0 ? (
              <>
                <div className="flex -space-x-2">
                  {getVisibleMembers(teamMembers, config.teamSection.maxVisibleAvatars).map((member) => (
                    <Avatar key={member.id} className="h-8 w-8 border-2 border-background">
                      {member.avatar && <AvatarImage src={member.avatar} />}
                      <AvatarFallback className="text-xs">{member.fallback}</AvatarFallback>
                    </Avatar>
                  ))}
                  {getHiddenMemberCount(teamMembers, config.teamSection.maxVisibleAvatars) > 0 && (
                    <div className="h-8 w-8 rounded-full bg-muted border-2 border-background flex items-center justify-center">
                      <span className="text-xs font-medium">
                        +{getHiddenMemberCount(teamMembers, config.teamSection.maxVisibleAvatars)}
                      </span>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex -space-x-2">
                <Avatar className="h-8 w-8 border-2 border-background">
                  <AvatarFallback className="text-xs">M</AvatarFallback>
                </Avatar>
                <Avatar className="h-8 w-8 border-2 border-background">
                  <AvatarFallback className="text-xs">A</AvatarFallback>
                </Avatar>
                <Avatar className="h-8 w-8 border-2 border-background">
                  <AvatarFallback className="text-xs">J</AvatarFallback>
                </Avatar>
                <div className="h-8 w-8 rounded-full bg-muted border-2 border-background flex items-center justify-center">
                  <span className="text-xs font-medium">+30</span>
                </div>
              </div>
            )}
          </div>
          <Button 
            size="sm" 
            className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2"
            onClick={handleAddTeamMember}
          >
            <UserPlus className="h-4 w-4" />
            {config.teamSection.addButtonText}
          </Button>
        </div>

        {/* Menu items */}
        <div className="space-y-2">
          {config.menuItems.map((item) => {
            const IconComponent = iconMap[item.icon];
            const isActive = pathname === item.href;
            
            return (
              <Button
                key={item.id}
                variant={isActive ? "secondary" : "ghost"}
                className="w-full justify-start gap-2 h-auto p-3"
                onClick={() => handleMenuItemClick(item.href)}
              >
                <div className="flex items-center gap-2 flex-1">
                  {IconComponent && <IconComponent className="h-4 w-4" />}
                  <span>{item.label}</span>
                  {item.badge && (
                    <Badge variant={item.badge.variant} className="ml-auto text-xs">
                      {item.badge.text}
                    </Badge>
                  )}
                </div>
              </Button>
            );
          })}
        </div>
      </div>

      {/* Calendar */}
      {config.showCalendar !== false && (
        <div className="p-4 flex-1">
          <div className="space-y-4">
            {/* Calendar header */}
            <div className="flex items-center justify-between">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigateMonth('prev')}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="font-medium">
                {monthNames[calendarMonth]} {calendarYear}
              </span>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigateMonth('next')}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            {/* Calendar grid */}
            <div className="grid grid-cols-7 gap-1">
              {/* Day headers */}
              {dayNames.map((day) => (
                <div key={day} className="text-center text-xs font-medium text-muted-foreground p-2">
                  {day}
                </div>
              ))}
              
              {/* Calendar days */}
              {calendarDays.map((day, index) => (
                <Button
                  key={index}
                  variant={day.isToday ? "default" : "ghost"}
                  size="sm"
                  className={`h-8 w-8 p-0 text-xs ${
                    !day.isCurrentMonth ? "text-muted-foreground/50" : ""
                  }`}
                >
                  {day.date}
                </Button>
              ))}
            </div>
          </div>
        </div>
      )}
    </aside>
  );
} 