/**
 * Projects API
 * 
 * Handles all project-related API calls including CRUD operations,
 * member management, and project metadata.
 */

// Project-related types based on backend API schemas
export interface ProjectCreate {
  name: string;
  slug?: string | null;
  description?: string | null;
  repo_url?: string | null;
  access_model?: 'role_based' | 'permission_based';
  is_private?: boolean;
}

export interface Project {
  id: string;
  name: string;
  slug: string | null;
  description: string | null;
  repo_url: string | null;
  is_private: boolean;
  access_model: 'role_based' | 'permission_based';
  created_by: string;
  creator: UserBasicInfo;
  created_at: string;
  updated_at: string;
  members: MemberResponse[];
  pending_invitations: InvitationResponse[];
  current_user_role: string | null;
  current_user_permission: string | null;
  current_user_can_read: boolean;
  current_user_can_write: boolean;
  current_user_can_admin: boolean;
  current_user_is_owner: boolean;
  member_count: number;
  paper_count: number;
  task_count: number;
}

export interface UserBasicInfo {
  id: string;
  name: string;
  email: string;
}

export interface MemberResponse {
  id: string;
  user: UserBasicInfo;
  role: string;
  permission: string | null;
  added_at: string;
  is_owner: boolean;
  can_manage_members: boolean;
}

export interface InvitationResponse {
  id: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ProjectsQueryParams {
  page?: number;
  size?: number;
  search?: string;
  role?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export const projectsApi = {
  /**
   * Safely serialize data for logging to avoid reference issues
   */
  safeLogData(data: any): any {
    if (!data) return 'No response data';
    
    try {
      return JSON.parse(JSON.stringify(data));
    } catch (error) {
      return `[Object: ${typeof data}]`;
    }
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
   * Get authentication token
   */
  getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('accessToken') || sessionStorage.getItem('accessToken');
  },

  /**
   * Create a new project
   */
  async createProject(projectData: ProjectCreate): Promise<Project> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(projectData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Create project JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Create project API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to create project (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Get user's projects with optional filtering and pagination
   */
  async getProjects(params: ProjectsQueryParams = {}): Promise<ProjectListResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.size) searchParams.set('size', params.size.toString());
    if (params.search) searchParams.set('search', params.search);
    if (params.role) searchParams.set('role', params.role);
    if (params.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params.sort_order) searchParams.set('sort_order', params.sort_order);

    const url = `${API_BASE_URL}/api/v1/projects/?${searchParams.toString()}`;

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
      console.error('Get projects JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get projects API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch projects (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Get a specific project by ID
   */
  async getProject(projectId: string): Promise<Project> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}`, {
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
      console.error('Get project JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get project API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch project (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Update a project
   */
  async updateProject(projectId: string, projectData: Partial<ProjectCreate>): Promise<Project> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(projectData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Update project JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Update project API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to update project (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Delete a project
   */
  async deleteProject(projectId: string): Promise<void> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}`, {
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

      console.error('Delete project API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to delete project (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }
  },

  /**
   * Get project statistics
   */
  async getProjectStats(projectId: string): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    if (!token) {
      throw new Error('No authentication token found');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/stats`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = this.extractErrorMessage(
        errorData, 
        `Failed to fetch project stats (${response.status}): ${response.statusText}`
      );
      throw new Error(errorMessage);
    }

    return response.json();
  },

  /**
   * Get project activity
   */
  async getProjectActivity(projectId: string, params: { limit?: number; offset?: number; activity_type?: string; } = {}): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    if (!token) {
      throw new Error('No authentication token found');
    }

    const queryParams = new URLSearchParams();
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.offset) queryParams.append('offset', params.offset.toString());
    if (params.activity_type) queryParams.append('activity_type', params.activity_type);

    const url = `${API_BASE_URL}/api/v1/projects/${projectId}/activity${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = this.extractErrorMessage(
        errorData, 
        `Failed to fetch project activity (${response.status}): ${response.statusText}`
      );
      throw new Error(errorMessage);
    }

    return response.json();
  },
}; 