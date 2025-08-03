// Collaborate page configuration for scalable, production-ready team collaboration
// All content can be easily customized for different deployments

export interface TeamMember {
  id: string;
  name: string;
  avatar?: string;
  fallback: string;
  status: 'online' | 'offline' | 'away';
  role?: string;
}

export interface Message {
  id: string;
  senderId: string;
  senderName: string;
  senderAvatar?: string;
  content: string;
  timestamp: Date;
  type: 'text' | 'file' | 'image';
  edited?: boolean;
}

export interface SidebarMenuItem {
  id: string;
  label: string;
  icon: string;
  badge?: {
    text: string;
    variant: 'default' | 'secondary' | 'destructive' | 'outline';
  };
  active?: boolean;
}

export interface CalendarDay {
  date: number;
  isCurrentMonth: boolean;
  isToday?: boolean;
  hasEvents?: boolean;
}

export interface CollaboratePageConfig {
  title: string;
  teamSection: {
    showCount: boolean;
    maxVisibleAvatars: number;
    addButtonText: string;
  };
  sidebar: {
    menuItems: SidebarMenuItem[];
  };
  chat: {
    tabs: {
      id: string;
      label: string;
      active?: boolean;
    }[];
    inputPlaceholder: string;
    actions: {
      id: string;
      icon: string;
      label: string;
    }[];
  };
  calendar: {
    currentMonth: string;
    currentYear: number;
  };
}

// Main collaborate page configuration
export const collaborateConfig: CollaboratePageConfig = {
  title: "Collaborate",
  
  teamSection: {
    showCount: true,
    maxVisibleAvatars: 3,
    addButtonText: "Add"
  },

  sidebar: {
    menuItems: [
      {
        id: "messages",
        label: "Messages",
        icon: "MessageCircle",
        badge: {
          text: "200 Updates",
          variant: "secondary"
        },
        active: true
      },
      {
        id: "journals",
        label: "Journals",
        icon: "BookOpen",
        active: false
      },
      {
        id: "tasks",
        label: "Tasks", 
        icon: "CheckSquare",
        active: false
      }
    ]
  },

  chat: {
    tabs: [
      {
        id: "messages",
        label: "Messages",
        active: true
      },
      {
        id: "media",
        label: "Media",
        active: false
      }
    ],
    inputPlaceholder: "Write a message...",
    actions: [
      {
        id: "attachment",
        icon: "Paperclip",
        label: "Attach file"
      },
      {
        id: "emoji", 
        icon: "Smile",
        label: "Add emoji"
      }
    ]
  },

  calendar: {
    currentMonth: "June",
    currentYear: 2024
  }
};

// Navigation items for collaborate page
export const collaborateNavItems = [
  {
    id: "home",
    label: "Home",
    href: "/home",
    active: false
  },
  {
    id: "papers",
    label: "Papers",
    href: "/papers",
    active: false
  },
  {
    id: "draft",
    label: "Draft",
    href: "/draft",
    active: false
  },
  {
    id: "collaborate",
    label: "Collaborate",
    href: "/collaborate",
    active: true
  },
  {
    id: "settings",
    label: "Settings",
    href: "/settings",
    active: false
  }
];

// Helper functions
export const formatMessageTime = (date: Date) => {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
};

export const getTeamMemberCount = (members: TeamMember[]) => {
  return members.length;
};

export const getVisibleMembers = (members: TeamMember[], maxVisible: number) => {
  return members.slice(0, maxVisible);
};

export const getHiddenMemberCount = (members: TeamMember[], maxVisible: number) => {
  return Math.max(0, members.length - maxVisible);
};

export const generateCalendarDays = (month: number, year: number): CalendarDay[] => {
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
      hasEvents: false // Will be populated from API
    });
  }
  
  return days;
};

export const getMessagesByDate = (messages: Message[], date: Date) => {
  return messages.filter(message => 
    message.timestamp.toDateString() === date.toDateString()
  );
}; 