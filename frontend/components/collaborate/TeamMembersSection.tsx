"use client";

import React from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";

interface TeamMember {
  id: string;
  name: string;
  avatar?: string;
  status: 'online' | 'offline' | 'away';
  role?: string;
}

interface TeamMembersSectionProps {
  members: TeamMember[];
  maxDisplay?: number;
  onAddMember?: () => void;
  showAddButton?: boolean;
}

export function TeamMembersSection({ 
  members, 
  maxDisplay = 3,
  onAddMember,
  showAddButton = true
}: TeamMembersSectionProps) {
  const displayMembers = members.slice(0, maxDisplay);
  const remainingCount = Math.max(0, members.length - maxDisplay);

  return (
    <div className="flex items-center gap-3">
      {/* Team Member Avatars */}
      <div className="flex -space-x-2">
        {displayMembers.map((member) => (
          <div key={member.id} className="relative">
            <Avatar className="h-10 w-10 border-2 border-white">
              <AvatarImage src={member.avatar} alt={member.name} />
              <AvatarFallback className="text-sm bg-gray-100">
                {member.name.split(' ').map(n => n[0]).join('')}
              </AvatarFallback>
            </Avatar>
            {member.status === 'online' && (
              <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 border-2 border-white rounded-full"></div>
            )}
          </div>
        ))}
        
        {/* Remaining Count */}
        {remainingCount > 0 && (
          <div className="h-10 w-10 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center">
            <span className="text-sm font-medium text-gray-600">+{remainingCount}</span>
          </div>
        )}
      </div>

      {/* Add Button */}
      {showAddButton && (
        <Button 
          variant="outline" 
          size="sm" 
          onClick={onAddMember}
          className="gap-2"
        >
          <Icon name="UserPlus" size={16} weight="regular" />
          Add
        </Button>
      )}
    </div>
  );
} 