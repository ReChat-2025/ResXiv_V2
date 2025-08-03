import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { useMemo } from 'react';

interface Notification {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  type: 'info' | 'success' | 'warning' | 'error';
}

interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  initials?: string;
}

interface Project {
  id: string;
  name: string;
  description?: string;
  createdAt: Date;
  updatedAt: Date;
}

interface AppState {
  // User state
  user: User | null;
  isAuthenticated: boolean;
  
  // Project state
  currentProject: Project | null;
  projects: Project[];
  
  // Notifications
  notifications: Notification[];
  unreadNotificationCount: number;
  
  // UI state
  theme: 'light' | 'dark' | 'system';
  sidebarCollapsed: boolean;
  
  // Loading states
  isInitializing: boolean;
  isLoading: boolean;
  
  // Actions
  setUser: (user: User | null) => void;
  setAuthenticated: (auth: boolean) => void;
  setCurrentProject: (project: Project | null) => void;
  setProjects: (projects: Project[]) => void;
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  removeNotification: (id: string) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSidebar: () => void;
  setLoading: (loading: boolean) => void;
  setInitializing: (initializing: boolean) => void;
  updateProject: (id: string, updates: Partial<Project>) => void;
  addProject: (project: Project) => void;
  removeProject: (id: string) => void;
}

export const useAppStore = create<AppState>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    user: null,
    isAuthenticated: false,
    currentProject: null,
    projects: [],
    notifications: [],
    unreadNotificationCount: 0,
    theme: 'light',
    sidebarCollapsed: false,
    isInitializing: true,
    isLoading: false,

    // Actions
    setUser: (user) => {
      set({ user });
    },

    setAuthenticated: (auth) => {
      set({ isAuthenticated: auth });
    },

    setCurrentProject: (project) => {
      set({ currentProject: project });
    },

    setProjects: (projects) => {
      set({ projects });
    },

    addNotification: (notification) => {
      const id = `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const newNotification = { ...notification, id };
      
      set((state) => ({
        notifications: [newNotification, ...state.notifications],
        unreadNotificationCount: state.unreadNotificationCount + 1
      }));
    },

    markNotificationRead: (id) => {
      set((state) => {
        const notifications = state.notifications.map(notif =>
          notif.id === id ? { ...notif, read: true } : notif
        );
        const unreadCount = notifications.filter(n => !n.read).length;
        
        return {
          notifications,
          unreadNotificationCount: unreadCount
        };
      });
    },

    markAllNotificationsRead: () => {
      set((state) => ({
        notifications: state.notifications.map(notif => ({ ...notif, read: true })),
        unreadNotificationCount: 0
      }));
    },

    removeNotification: (id) => {
      set((state) => {
        const notifications = state.notifications.filter(notif => notif.id !== id);
        const unreadCount = notifications.filter(n => !n.read).length;
        
        return {
          notifications,
          unreadNotificationCount: unreadCount
        };
      });
    },

    setTheme: (theme) => {
      set({ theme });
      
      // Apply theme to document
      if (typeof window !== 'undefined') {
        const root = window.document.documentElement;
        root.classList.remove('light', 'dark');
        
        if (theme === 'system') {
          const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
          root.classList.add(systemTheme);
        } else {
          root.classList.add(theme);
        }
      }
    },

    toggleSidebar: () => {
      set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }));
    },

    setLoading: (loading) => {
      set({ isLoading: loading });
    },

    setInitializing: (initializing) => {
      set({ isInitializing: initializing });
    },

    updateProject: (id, updates) => {
      set((state) => ({
        projects: state.projects.map(project =>
          project.id === id ? { ...project, ...updates } : project
        ),
        currentProject: state.currentProject?.id === id 
          ? { ...state.currentProject, ...updates }
          : state.currentProject
      }));
    },

    addProject: (project) => {
      set((state) => ({
        projects: [...state.projects, project]
      }));
    },

    removeProject: (id) => {
      set((state) => ({
        projects: state.projects.filter(p => p.id !== id),
        currentProject: state.currentProject?.id === id ? null : state.currentProject
      }));
    }
  }))
);

// Selector hooks for better performance
export const useUser = () => useAppStore(state => state.user);
// Auth hooks with memoization
export const useIsAuthenticated = () => useAppStore(state => state.isAuthenticated);
export const useSetAuthenticated = () => useAppStore(state => state.setAuthenticated);

export const useAuth = () => {
  const isAuthenticated = useIsAuthenticated();
  const setAuthenticated = useSetAuthenticated();
  
  return useMemo(() => ({
    isAuthenticated,
    setAuthenticated
  }), [isAuthenticated, setAuthenticated]);
};
export const useCurrentProject = () => useAppStore(state => state.currentProject);

// Individual notification selectors to avoid infinite loops
export const useNotificationsData = () => useAppStore(state => state.notifications);
export const useNotificationsCount = () => useAppStore(state => state.unreadNotificationCount);
export const useAddNotification = () => useAppStore(state => state.addNotification);
export const useMarkNotificationRead = () => useAppStore(state => state.markNotificationRead);
export const useMarkAllNotificationsRead = () => useAppStore(state => state.markAllNotificationsRead);
export const useRemoveNotification = () => useAppStore(state => state.removeNotification);

// Combined hook for backward compatibility with memoization
export const useNotifications = () => {
  const notifications = useNotificationsData();
  const unreadCount = useNotificationsCount();
  const addNotification = useAddNotification();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const remove = useRemoveNotification();
  
  return useMemo(() => ({
    notifications,
    unreadCount,
    addNotification,
    markRead,
    markAllRead,
    remove
  }), [notifications, unreadCount, addNotification, markRead, markAllRead, remove]);
};

// Theme hooks with memoization
export const useCurrentTheme = () => useAppStore(state => state.theme);
export const useSetTheme = () => useAppStore(state => state.setTheme);

export const useTheme = () => {
  const theme = useCurrentTheme();
  const setTheme = useSetTheme();
  
  return useMemo(() => ({
    theme,
    setTheme
  }), [theme, setTheme]);
};

// App loading hooks with memoization
export const useIsLoading = () => useAppStore(state => state.isLoading);
export const useIsInitializing = () => useAppStore(state => state.isInitializing);
export const useSetLoading = () => useAppStore(state => state.setLoading);
export const useSetInitializing = () => useAppStore(state => state.setInitializing);

export const useAppLoading = () => {
  const isLoading = useIsLoading();
  const isInitializing = useIsInitializing();
  const setLoading = useSetLoading();
  const setInitializing = useSetInitializing();
  
  return useMemo(() => ({
    isLoading,
    isInitializing,
    setLoading,
    setInitializing
  }), [isLoading, isInitializing, setLoading, setInitializing]);
}; 