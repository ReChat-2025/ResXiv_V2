// Global App Configuration
// This file centralizes all configuration to eliminate hardcoding

export interface AppConfig {
  app: {
    name: string;
    version: string;
    description: string;
    defaultProject: string;
  };
  theme: {
    primaryColor: string;
    secondaryColor: string;
    backgroundColor: string;
    textColor: string;
  };
  layout: {
    sidebarWidth: string;
    headerHeight: string;
    maxContentWidth: string;
  };
  features: {
    enableNotifications: boolean;
    enableDarkMode: boolean;
    enableTeamCollaboration: boolean;
    maxTeamMembers: number;
    maxVisibleAvatars: number;
  };
  navigation: {
    primaryRoutes: NavigationRoute[];
    secondaryRoutes: NavigationRoute[];
  };
  ui: {
    animations: {
      duration: string;
      easing: string;
    };
    spacing: {
      xs: string;
      sm: string;
      md: string;
      lg: string;
      xl: string;
    };
    borderRadius: string;
  };
}

export interface NavigationRoute {
  id: string;
  label: string;
  href: string;
  icon: string;
  badge?: {
    text: string;
    variant: 'default' | 'secondary' | 'destructive' | 'outline';
    color?: string;
  };
  enabled: boolean;
  requiresAuth: boolean;
}

export interface TeamMember {
  id: string;
  name: string;
  email?: string;
  avatar?: string;
  status: 'online' | 'offline' | 'away' | 'busy';
  role: string;
  joinedAt?: string;
  lastActive?: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'archived' | 'draft';
  createdAt: string;
  updatedAt: string;
  teamMembers: string[]; // Array of team member IDs
  settings: {
    isPublic: boolean;
    allowInvites: boolean;
    enableNotifications: boolean;
  };
}

// Main App Configuration
export const appConfig: AppConfig = {
  app: {
    name: "ResXiv",
    version: "2.0.0",
    description: "Research Collaboration Platform",
    defaultProject: "PhD Research Thesis"
  },
  theme: {
    primaryColor: "hsl(35, 35%, 25%)",
    secondaryColor: "hsl(40, 20%, 90%)",
    backgroundColor: "hsl(45, 15%, 97%)",
    textColor: "hsl(30, 15%, 15%)"
  },
  layout: {
    sidebarWidth: "20rem",
    headerHeight: "4rem",
    maxContentWidth: "8xl"
  },
  features: {
    enableNotifications: true,
    enableDarkMode: true,
    enableTeamCollaboration: true,
    maxTeamMembers: 50,
    maxVisibleAvatars: 3
  },
  navigation: {
    primaryRoutes: [
      {
        id: "messages",
        label: "Messages",
        href: "/collaborate",
        icon: "ChatCircle",
        badge: {
          text: "200 Updates",
          variant: "secondary"
        },
        enabled: true,
        requiresAuth: true
      },
      {
        id: "journals",
        label: "Journals",
        href: "/journals",
        icon: "BookOpen",
        enabled: true,
        requiresAuth: true
      },
      {
        id: "tasks",
        label: "Tasks",
        href: "/tasks",
        icon: "CheckSquare",
        enabled: true,
        requiresAuth: true
      }
    ],
    secondaryRoutes: [
      {
        id: "papers",
        label: "Papers",
        href: "/papers",
        icon: "FileText",
        enabled: true,
        requiresAuth: true
      },
      {
        id: "projects",
        label: "Projects",
        href: "/projects",
        icon: "Folder",
        enabled: true,
        requiresAuth: true
      },
      {
        id: "settings",
        label: "Settings",
        href: "/settings",
        icon: "Settings",
        enabled: true,
        requiresAuth: true
      }
    ]
  },
  ui: {
    animations: {
      duration: "300ms",
      easing: "ease-in-out"
    },
    spacing: {
      xs: "0.5rem",
      sm: "1rem",
      md: "1.5rem",
      lg: "2rem",
      xl: "3rem"
    },
    borderRadius: "0.5rem"
  }
};

// Mock Team Members Data
export const mockTeamMembers: TeamMember[] = [
  {
    id: "1",
    name: "John Smith",
    email: "john.smith@university.edu",
    status: "online",
    role: "Research Lead",
    joinedAt: "2024-01-15",
    lastActive: new Date().toISOString()
  },
  {
    id: "2", 
    name: "Sarah Johnson",
    email: "sarah.johnson@university.edu",
    status: "online",
    role: "Data Scientist",
    joinedAt: "2024-01-20",
    lastActive: new Date(Date.now() - 300000).toISOString() // 5 minutes ago
  },
  {
    id: "3",
    name: "Mike Chen",
    email: "mike.chen@university.edu",
    status: "away",
    role: "Developer",
    joinedAt: "2024-02-01",
    lastActive: new Date(Date.now() - 1800000).toISOString() // 30 minutes ago
  },
  {
    id: "4",
    name: "Alice Brown",
    email: "alice.brown@university.edu", 
    status: "busy",
    role: "Research Assistant",
    joinedAt: "2024-02-10",
    lastActive: new Date(Date.now() - 3600000).toISOString() // 1 hour ago
  },
  {
    id: "5",
    name: "David Wilson",
    email: "david.wilson@university.edu",
    status: "offline",
    role: "Statistical Analyst",
    joinedAt: "2024-02-15",
    lastActive: new Date(Date.now() - 86400000).toISOString() // 1 day ago
  },
  // Generate additional mock members for demonstration
  ...Array.from({ length: 30 }, (_, i) => ({
    id: `member-${i + 6}`,
    name: `Team Member ${i + 6}`,
    email: `member${i + 6}@university.edu`,
    status: 'offline' as const,
    role: 'Collaborator',
    joinedAt: `2024-03-${String(i + 1).padStart(2, '0')}`,
    lastActive: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString()
  }))
];

// Mock Projects Data
export const mockProjects: Project[] = [
  {
    id: "1",
    name: "PhD Research Thesis",
    description: "Advanced research in machine learning applications",
    status: "active",
    createdAt: "2024-01-01",
    updatedAt: new Date().toISOString(),
    teamMembers: ["1", "2", "3", "4", "5"],
    settings: {
      isPublic: false,
      allowInvites: true,
      enableNotifications: true
    }
  },
  {
    id: "2",
    name: "Data Analysis Project",
    description: "Statistical analysis of research data",
    status: "active",
    createdAt: "2024-02-01",
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    teamMembers: ["2", "4", "5"],
    settings: {
      isPublic: true,
      allowInvites: true,
      enableNotifications: true
    }
  }
];

// Utility functions
export const getTeamMemberById = (id: string): TeamMember | undefined => {
  return mockTeamMembers.find(member => member.id === id);
};

export const getProjectById = (id: string): Project | undefined => {
  return mockProjects.find(project => project.id === id);
};

export const getNavigationRouteById = (id: string): NavigationRoute | undefined => {
  return [...appConfig.navigation.primaryRoutes, ...appConfig.navigation.secondaryRoutes]
    .find(route => route.id === id);
};

export const getActiveTeamMembers = (): TeamMember[] => {
  return mockTeamMembers.filter(member => member.status !== 'offline');
};

export const getTeamMembersByProject = (projectId: string): TeamMember[] => {
  const project = getProjectById(projectId);
  if (!project) return [];
  
  return project.teamMembers
    .map(memberId => getTeamMemberById(memberId))
    .filter((member): member is TeamMember => member !== undefined);
};

// Theme utility functions
export const getThemeColors = () => ({
  primary: appConfig.theme.primaryColor,
  secondary: appConfig.theme.secondaryColor,
  background: appConfig.theme.backgroundColor,
  text: appConfig.theme.textColor
});

export const getLayoutConfig = () => appConfig.layout;
export const getFeatureConfig = () => appConfig.features;
export const getUIConfig = () => appConfig.ui; 