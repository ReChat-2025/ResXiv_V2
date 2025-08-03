/**
 * Tasks API
 * 
 * Handles all task-related API calls including CRUD operations,
 * task lists, and task analytics for projects.
 */

// Task-related types based on backend API schemas
export interface TaskCreate {
  title: string;
  description?: string | null;
  status?: 'todo' | 'in_progress' | 'review' | 'done' | 'cancelled';
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  due_date?: string | null;
  start_date?: string | null;
  estimated_hours?: number | null;
  actual_hours?: number | null;
  progress?: number;
  position?: number;
  is_milestone?: boolean;
  assigned_to?: string | null;
  task_list_id?: string | null;
  parent_task_id?: string | null;
}

export interface TaskUpdate {
  title?: string | null;
  description?: string | null;
  status?: 'todo' | 'in_progress' | 'review' | 'done' | 'cancelled' | null;
  priority?: 'low' | 'medium' | 'high' | 'urgent' | null;
  due_date?: string | null;
  start_date?: string | null;
  estimated_hours?: number | null;
  actual_hours?: number | null;
  progress?: number | null;
  position?: number | null;
  is_milestone?: boolean | null;
  assigned_to?: string | null;
  task_list_id?: string | null;
  parent_task_id?: string | null;
}

export interface TaskResponse {
  id: string;
  title: string;
  description: string | null;
  status: 'todo' | 'in_progress' | 'review' | 'done' | 'cancelled';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  due_date: string | null;
  start_date: string | null;
  estimated_hours: number | null;
  actual_hours: number | null;
  progress: number;
  position: number;
  is_milestone: boolean;
  assigned_to: string | null;
  task_list_id: string | null;
  parent_task_id: string | null;
  project_id: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TaskListCreate {
  name: string;
  description?: string | null;
  color?: string | null;
  position?: number | null;
}

export interface TaskListUpdate {
  name?: string | null;
  description?: string | null;
  color?: string | null;
  position?: number | null;
}

export interface TaskListResponse {
  id: string;
  name: string;
  description: string | null;
  color: string | null;
  position: number | null;
  project_id: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListWithTasks {
  id: string;
  name: string;
  description: string | null;
  color: string | null;
  position: number | null;
  project_id: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  tasks: TaskResponse[];
}

export interface TasksQueryParams {
  page?: number;
  size?: number;
  search?: string;
  status?: 'todo' | 'in_progress' | 'review' | 'done' | 'cancelled';
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  assigned_to?: string;
  task_list_id?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface TaskListResponse {
  tasks: TaskResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const tasksApi = {
  /**
   * Get authentication token
   */
  getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('accessToken');
  },

  /**
   * Extract error message from API response
   */
  extractErrorMessage(data: any, defaultMessage: string): string {
    if (data && typeof data === 'object') {
      if (typeof data.detail === 'string') return data.detail;
      if (typeof data.message === 'string') return data.message;
      if (typeof data.error === 'string') return data.error;
      
      if (data.detail && typeof data.detail === 'object') {
        if (data.detail.message && typeof data.detail.message === 'string') {
          return data.detail.message;
        }
        if (data.detail.error && typeof data.detail.error === 'string') {
          return data.detail.error;
        }
      }
      
      if (Array.isArray(data.detail)) {
        return data.detail.map((err: any) => err.msg || err).join(', ');
      }
    }
    
    return defaultMessage;
  },

  /**
   * Get project tasks with optional filtering and pagination
   */
  async getTasks(projectId: string, params: TasksQueryParams = {}): Promise<TaskListResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.size) searchParams.set('size', params.size.toString());
    if (params.search) searchParams.set('search', params.search);
    if (params.status) searchParams.set('status', params.status);
    if (params.priority) searchParams.set('priority', params.priority);
    if (params.assigned_to) searchParams.set('assigned_to', params.assigned_to);
    if (params.task_list_id) searchParams.set('task_list_id', params.task_list_id);
    if (params.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params.sort_order) searchParams.set('sort_order', params.sort_order);

    const url = `${API_BASE_URL}/api/v1/projects/${projectId}/tasks/?${searchParams.toString()}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Get tasks JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get tasks API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch tasks (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Create a new task
   */
  async createTask(projectId: string, taskData: TaskCreate): Promise<TaskResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/tasks/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(taskData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Create task JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Create task API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to create task (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Get a specific task by ID
   */
  async getTask(projectId: string, taskId: string): Promise<TaskResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/tasks/${taskId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Get task JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get task API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch task (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Update a task
   */
  async updateTask(projectId: string, taskId: string, taskData: TaskUpdate): Promise<TaskResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/tasks/${taskId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(taskData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Update task JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Update task API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to update task (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Delete a task
   */
  async deleteTask(projectId: string, taskId: string): Promise<void> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/tasks/${taskId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      let data: any = null;
      try {
        data = await response.json();
      } catch (error) {
        // Response might not have JSON body for delete
      }

      console.error('Delete task API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to delete task (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }
  },

  /**
   * Get task lists for a project
   */
  async getTaskLists(projectId: string): Promise<TaskListResponse[]> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/tasks/lists`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Get task lists JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get task lists API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch task lists (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Create a new task list
   */
  async createTaskList(projectId: string, taskListData: TaskListCreate): Promise<TaskListResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/tasks/lists`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(taskListData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Create task list JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Create task list API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to create task list (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Update a task list
   */
  async updateTaskList(projectId: string, listId: string, taskListData: TaskListUpdate): Promise<TaskListResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/tasks/lists/${listId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(taskListData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Update task list JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Update task list API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to update task list (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Delete a task list
   */
  async deleteTaskList(projectId: string, listId: string): Promise<void> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/tasks/lists/${listId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      let data: any = null;
      try {
        data = await response.json();
      } catch (error) {
        // Response might not have JSON body for delete
      }

      console.error('Delete task list API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to delete task list (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }
  },

  /**
   * Get task analytics for a project
   */
  async getTaskAnalytics(projectId: string): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/tasks/analytics`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Get task analytics JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get task analytics API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch task analytics (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },
}; 