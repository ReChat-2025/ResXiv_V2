// Journals page configuration for scalable, production-ready journal management
// All content can be easily customized for different deployments

export interface Journal {
  id: string;
  title: string;
  content: string;
  author: string;
  authorId: string;
  createdAt: Date;
  updatedAt: Date;
  status: JournalStatus;
  visibility: JournalVisibility;
  tags: string[];
  paperCount?: number;
}

export type JournalStatus = 'draft' | 'published' | 'archived';
export type JournalVisibility = 'private' | 'shared' | 'public';
export type JournalSortBy = 'created' | 'updated' | 'title' | 'author';
export type SortOrder = 'asc' | 'desc';

export interface JournalsPageConfig {
  title: string;
  subtitle: string;
  createButtonText: string;
  searchPlaceholder: string;
  sortOptions: {
    id: JournalSortBy;
    label: string;
  }[];
  filterOptions: {
    id: string;
    label: string;
    value: JournalStatus | JournalVisibility | 'all';
  }[];
  emptyState: {
    title: string;
    description: string;
    actionText: string;
  };
}

export interface SidebarConfig {
  title: string;
  teamSection: {
    showCount: boolean;
    maxVisibleAvatars: number;
    addButtonText: string;
  };
  menuItems: {
    id: string;
    label: string;
    icon: string;
    badge?: {
      text: string;
      variant: 'default' | 'secondary' | 'destructive' | 'outline';
    };
    active?: boolean;
    href?: string;
  }[];
  showCalendar?: boolean;
}

// Main journals page configuration
export const journalsConfig: JournalsPageConfig = {
  title: "All Journals",
  subtitle: "papers",
  createButtonText: "Create",
  searchPlaceholder: "Search journals...",
  
  sortOptions: [
    { id: "updated", label: "Last Updated" },
    { id: "created", label: "Date Created" },
    { id: "title", label: "Title" },
    { id: "author", label: "Author" }
  ],

  filterOptions: [
    { id: "all", label: "All Journals", value: "all" },
    { id: "private", label: "Private", value: "private" },
    { id: "shared", label: "Shared", value: "shared" },
    { id: "public", label: "Public", value: "public" },
    { id: "draft", label: "Draft", value: "draft" },
    { id: "published", label: "Published", value: "published" }
  ],

  emptyState: {
    title: "No journals yet",
    description: "Create your first journal to start documenting your research",
    actionText: "Create Journal"
  }
};

// Sidebar configuration for journals page
export const journalsSidebarConfig: SidebarConfig = {
  title: "Collaborate",
  
  teamSection: {
    showCount: true,
    maxVisibleAvatars: 3,
    addButtonText: "Add"
  },

  menuItems: [
    {
      id: "chat",
      label: "Chat",
      icon: "MessageCircle",
      active: false,
      href: "/collaborate"
    },
    {
      id: "journals",
      label: "Journals",
      icon: "BookOpen",
      active: true,
      href: "/journals"
    },
    {
      id: "tasks",
      label: "Tasks", 
      icon: "CheckSquare",
      active: false,
      href: "/tasks"
    }
  ],

  showCalendar: true
};

// Navigation items for journals page
export const journalsNavItems = [
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
    active: false
  },
  {
    id: "settings",
    label: "Settings",
    href: "/settings",
    active: false
  }
];

// Helper functions
export const formatJournalTime = (date: Date) => {
  const now = new Date();
  const diffInMs = now.getTime() - date.getTime();
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));
  
  if (diffInDays === 0) {
    return `Today, ${date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })}`;
  } else if (diffInDays === 1) {
    return `Yesterday, ${date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })}`;
  } else if (diffInDays < 7) {
    return `${diffInDays} days ago`;
  } else {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  }
};

export const getJournalsByStatus = (journals: Journal[], status: JournalStatus) => {
  return journals.filter(journal => journal.status === status);
};

export const getJournalsByVisibility = (journals: Journal[], visibility: JournalVisibility) => {
  return journals.filter(journal => journal.visibility === visibility);
};

export const searchJournals = (journals: Journal[], query: string) => {
  const lowercaseQuery = query.toLowerCase();
  return journals.filter(journal =>
    journal.title.toLowerCase().includes(lowercaseQuery) ||
    journal.content.toLowerCase().includes(lowercaseQuery) ||
    journal.author.toLowerCase().includes(lowercaseQuery) ||
    journal.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery))
  );
};

export const sortJournals = (journals: Journal[], sortBy: JournalSortBy, order: SortOrder = 'desc') => {
  return [...journals].sort((a, b) => {
    let aValue: any;
    let bValue: any;

    switch (sortBy) {
      case 'created':
        aValue = a.createdAt.getTime();
        bValue = b.createdAt.getTime();
        break;
      case 'updated':
        aValue = a.updatedAt.getTime();
        bValue = b.updatedAt.getTime();
        break;
      case 'title':
        aValue = a.title.toLowerCase();
        bValue = b.title.toLowerCase();
        break;
      case 'author':
        aValue = a.author.toLowerCase();
        bValue = b.author.toLowerCase();
        break;
      default:
        return 0;
    }

    if (order === 'asc') {
      return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
    } else {
      return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
    }
  });
};

export const getJournalPreview = (content: string, maxLength: number = 120) => {
  return content.length > maxLength ? `${content.substring(0, maxLength)}...` : content;
};

export const getVisibilityIcon = (visibility: JournalVisibility) => {
  switch (visibility) {
    case 'private':
      return '🔒';
    case 'shared':
      return '👥';
    case 'public':
      return '🌐';
    default:
      return '🔒';
  }
};

export const getJournalCount = (journals: Journal[]) => {
  return journals.length;
}; 