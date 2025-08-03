// Projects configuration for scalable, production-ready project management
// All content can be easily customized for different deployments

export interface ProjectConfig {
  id: string;
  name: string;
  description?: string;
  status: ProjectStatus;
  createdAt: Date;
  updatedAt: Date;
  members: ProjectMember[];
  tags: string[];
  priority: ProjectPriority;
  visibility: ProjectVisibility;
}

export interface ProjectMember {
  id: string;
  name: string;
  email: string;
  role: MemberRole;
  avatar?: string;
}

export type ProjectStatus = 'active' | 'paused' | 'completed' | 'archived';
export type ProjectPriority = 'low' | 'medium' | 'high' | 'urgent';
export type ProjectVisibility = 'private' | 'team' | 'public';
export type MemberRole = 'owner' | 'admin' | 'member' | 'viewer';

export interface ProjectsPageConfig {
  title: string;
  description: string;
  navTitle?: string;
  emptyState: {
    title: string;
    description: string;
    actionText: string;
    icon: string;
  };
  actions: {
    create: {
      text: string;
      icon: string;
    };
    search: {
      placeholder: string;
    };
    filter: {
      enabled: boolean;
      options: FilterOption[];
    };
    sort: {
      enabled: boolean;
      options: SortOption[];
    };
  };
  table: {
    columns: TableColumn[];
  };
}

export interface FilterOption {
  id: string;
  label: string;
  value: string;
}

export interface SortOption {
  id: string;
  label: string;
  value: string;
  direction: 'asc' | 'desc';
}

export interface TableColumn {
  id: string;
  label: string;
  sortable: boolean;
  width?: string;
}

// Main projects configuration
export const projectsConfig: ProjectsPageConfig = {
  title: "Projects",
  description: "Manage and organize your research projects",
  navTitle: "All Projects",
  
  emptyState: {
    title: "No projects yet",
    description: "Get started by creating your first project. You can organize your work and collaborate with others.",
    actionText: "Create your first project",
    icon: "FolderOpen"
  },

  actions: {
    create: {
      text: "New Project",
      icon: "Plus"
    },
    search: {
      placeholder: "Search projects..."
    },
    filter: {
      enabled: true,
      options: [
        { id: "all", label: "All Projects", value: "all" },
        { id: "active", label: "Active", value: "active" },
        { id: "paused", label: "Paused", value: "paused" },
        { id: "completed", label: "Completed", value: "completed" },
        { id: "archived", label: "Archived", value: "archived" }
      ]
    },
    sort: {
      enabled: true,
      options: [
        { id: "updated", label: "Last Updated", value: "updatedAt", direction: "desc" },
        { id: "created", label: "Date Created", value: "createdAt", direction: "desc" },
        { id: "name", label: "Name (A-Z)", value: "name", direction: "asc" },
        { id: "priority", label: "Priority", value: "priority", direction: "desc" }
      ]
    }
  },

  table: {
    columns: [
      { id: "name", label: "Project", sortable: true, width: "300px" },
      { id: "status", label: "Status", sortable: true, width: "120px" },
      { id: "members", label: "Members", sortable: false, width: "150px" },
      { id: "priority", label: "Priority", sortable: true, width: "100px" },
      { id: "updated", label: "Last Updated", sortable: true, width: "150px" },
      { id: "actions", label: "", sortable: false, width: "60px" }
    ]
  }
};

// AI Features configuration
export interface AIFeatureConfig {
  id: string;
  name: string;
  description: string;
  category: AICategory;
  icon: string;
  status: AIFeatureStatus;
  isNew?: boolean;
  isPopular?: boolean;
}

export type AICategory = 'writing' | 'research' | 'analysis' | 'collaboration' | 'productivity';
export type AIFeatureStatus = 'available' | 'beta' | 'coming-soon' | 'experimental';

export interface AIPageConfig {
  title: string;
  description: string;
  features: AIFeatureConfig[];
  chat: {
    placeholder: string;
    sendButton: string;
    clearButton: string;
  };
  quickActions: {
    enabled: boolean;
    actions: QuickAction[];
  };
}

export interface QuickAction {
  id: string;
  text: string;
  description: string;
  icon: string;
}

export const aiConfig: AIPageConfig = {
  title: "ResXiv AI",
  description: "Powerful AI tools to enhance your research workflow",
  
  features: [
    {
      id: "research-assistant",
      name: "Research Assistant",
      description: "Get help with literature reviews, paper analysis, and research insights",
      category: "research",
      icon: "BookOpen",
      status: "available",
      isPopular: true
    },
    {
      id: "writing-helper",
      name: "Academic Writing",
      description: "Improve your academic writing with AI-powered suggestions",
      category: "writing",
      icon: "PenTool",
      status: "available"
    },
    {
      id: "data-analysis",
      name: "Data Analysis",
      description: "Analyze datasets and generate insights with AI assistance",
      category: "analysis",
      icon: "BarChart3",
      status: "beta",
      isNew: true
    },
    {
      id: "citation-manager",
      name: "Smart Citations",
      description: "Automatically format and manage your citations",
      category: "productivity",
      icon: "Quote",
      status: "available"
    },
    {
      id: "collaboration-hub",
      name: "Team Collaboration",
      description: "Facilitate team research with AI-powered project coordination",
      category: "collaboration",
      icon: "Users",
      status: "coming-soon"
    },
    {
      id: "methodology-advisor",
      name: "Methodology Advisor",
      description: "Get guidance on research methodologies and experimental design",
      category: "research",
      icon: "Lightbulb",
      status: "experimental"
    }
  ],

  chat: {
    placeholder: "Ask me anything about your research...",
    sendButton: "Send",
    clearButton: "Clear conversation"
  },

  quickActions: {
    enabled: true,
    actions: [
      {
        id: "summarize-paper",
        text: "Summarize this paper",
        description: "Get a concise summary of academic papers",
        icon: "FileText"
      },
      {
        id: "generate-outline",
        text: "Generate research outline",
        description: "Create structured outlines for your research",
        icon: "List"
      },
      {
        id: "find-references",
        text: "Find relevant papers",
        description: "Discover related research and citations",
        icon: "Search"
      },
      {
        id: "improve-writing",
        text: "Improve my writing",
        description: "Get suggestions to enhance academic writing",
        icon: "Edit"
      }
    ]
  }
};

// Helper functions
export const getProjectsByStatus = (projects: ProjectConfig[], status: ProjectStatus) => {
  return projects.filter(project => project.status === status);
};

export const getProjectsByMember = (projects: ProjectConfig[], memberId: string) => {
  return projects.filter(project => 
    project.members.some(member => member.id === memberId)
  );
};

export const sortProjects = (projects: ProjectConfig[], sortBy: string, direction: 'asc' | 'desc') => {
  return [...projects].sort((a, b) => {
    let aValue: any = a[sortBy as keyof ProjectConfig];
    let bValue: any = b[sortBy as keyof ProjectConfig];
    
    if (sortBy === 'updatedAt' || sortBy === 'createdAt') {
      aValue = new Date(aValue).getTime();
      bValue = new Date(bValue).getTime();
    }
    
    if (direction === 'asc') {
      return aValue > bValue ? 1 : -1;
    } else {
      return aValue < bValue ? 1 : -1;
    }
  });
};

export const filterAIFeatures = (features: AIFeatureConfig[], category?: AICategory) => {
  if (!category || category === 'all' as any) {
    return features;
  }
  return features.filter(feature => feature.category === category);
}; 