// Tasks page configuration for scalable, production-ready task management
// All content can be easily customized for different deployments

export interface Task {
  id: string;
  name: string;
  status: TaskStatus;
  assignees: TaskAssignee[];
  dueDate: Date;
  timeRange?: {
    start: string;
    end: string;
  };
  description?: string;
  priority: TaskPriority;
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
}

export interface TaskAssignee {
  id: string;
  name: string;
  avatar?: string;
  fallback: string;
  email?: string;
}

export type TaskStatus = 'not_started' | 'in_progress' | 'done' | 'cancelled';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';
export type TaskSortBy = 'name' | 'status' | 'due_date' | 'assignee' | 'priority';
export type SortOrder = 'asc' | 'desc';

export interface TaskStatusConfig {
  id: TaskStatus;
  label: string;
  icon: string;
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  color: string;
}

export interface TasksPageConfig {
  title: string;
  createButtonText: string;
  sortOptions: {
    id: TaskSortBy;
    label: string;
  }[];
  filterOptions: {
    id: string;
    label: string;
    value: TaskStatus | 'all';
  }[];
  tableColumns: {
    id: string;
    label: string;
    sortable?: boolean;
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

// Main tasks page configuration
export const tasksConfig: TasksPageConfig = {
  title: "Tasks",
  createButtonText: "Create",
  
  sortOptions: [
    { id: "due_date", label: "Due Date" },
    { id: "name", label: "Task Name" },
    { id: "status", label: "Status" },
    { id: "assignee", label: "Assignee" },
    { id: "priority", label: "Priority" }
  ],

  filterOptions: [
    { id: "all", label: "All Tasks", value: "all" },
    { id: "not_started", label: "Not Started", value: "not_started" },
    { id: "in_progress", label: "In Progress", value: "in_progress" },
    { id: "done", label: "Done", value: "done" },
    { id: "cancelled", label: "Cancelled", value: "cancelled" }
  ],

  tableColumns: [
    { id: "name", label: "Task Name", sortable: true },
    { id: "status", label: "Status", sortable: true },
    { id: "assignee", label: "Assignee", sortable: true },
    { id: "due_date", label: "Due date", sortable: true },
    { id: "time", label: "Time", sortable: false }
  ],

  emptyState: {
    title: "No tasks yet",
    description: "Create your first task to start organizing your work",
    actionText: "Create Task"
  }
};

// Task status configurations
export const taskStatusConfigs: Record<TaskStatus, TaskStatusConfig> = {
  not_started: {
    id: "not_started",
    label: "Not Started",
    icon: "Circle",
    variant: "outline",
    color: "text-muted-foreground"
  },
  in_progress: {
    id: "in_progress",
    label: "In Progress",
    icon: "Zap",
    variant: "secondary",
    color: "text-orange-600"
  },
  done: {
    id: "done",
    label: "Done",
    icon: "Check",
    variant: "default",
    color: "text-green-600"
  },
  cancelled: {
    id: "cancelled",
    label: "Cancelled",
    icon: "X",
    variant: "destructive",
    color: "text-red-600"
  }
};

// Sidebar configuration for tasks page
export const tasksSidebarConfig: SidebarConfig = {
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
      active: false,
      href: "/journals"
    },
    {
      id: "tasks",
      label: "Tasks", 
      icon: "CheckSquare",
      active: true,
      href: "/tasks"
    }
  ],

  showCalendar: true
};

// Navigation items for tasks page
export const tasksNavItems = [
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
export const formatTaskDate = (date: Date) => {
  return date.toLocaleDateString('en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
};

export const formatTaskTime = (timeRange?: { start: string; end: string }) => {
  if (!timeRange) return "-";
  return `${timeRange.start} - ${timeRange.end}`;
};

export const getTasksByStatus = (tasks: Task[], status: TaskStatus) => {
  return tasks.filter(task => task.status === status);
};

export const searchTasks = (tasks: Task[], query: string) => {
  const lowercaseQuery = query.toLowerCase();
  return tasks.filter(task =>
    task.name.toLowerCase().includes(lowercaseQuery) ||
    task.description?.toLowerCase().includes(lowercaseQuery) ||
    task.assignees.some(assignee => 
      assignee.name.toLowerCase().includes(lowercaseQuery)
    ) ||
    task.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery))
  );
};

export const sortTasks = (tasks: Task[], sortBy: TaskSortBy, order: SortOrder = 'asc') => {
  return [...tasks].sort((a, b) => {
    let aValue: any;
    let bValue: any;

    switch (sortBy) {
      case 'name':
        aValue = a.name.toLowerCase();
        bValue = b.name.toLowerCase();
        break;
      case 'status':
        aValue = a.status;
        bValue = b.status;
        break;
      case 'due_date':
        aValue = a.dueDate.getTime();
        bValue = b.dueDate.getTime();
        break;
      case 'assignee':
        aValue = a.assignees[0]?.name.toLowerCase() || '';
        bValue = b.assignees[0]?.name.toLowerCase() || '';
        break;
      case 'priority':
        aValue = a.priority;
        bValue = b.priority;
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

export const getVisibleAssignees = (assignees: TaskAssignee[], maxVisible: number) => {
  return assignees.slice(0, maxVisible);
};

export const getHiddenAssigneeCount = (assignees: TaskAssignee[], maxVisible: number) => {
  return Math.max(0, assignees.length - maxVisible);
};

export const getTaskCount = (tasks: Task[]) => {
  return tasks.length;
};

export const getTaskCountByStatus = (tasks: Task[], status: TaskStatus) => {
  return tasks.filter(task => task.status === status).length;
}; 