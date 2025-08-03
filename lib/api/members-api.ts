/**
 * Members API
 * 
 * Handles all project member-related API calls including member management,
 * invitations, and permissions for collaboration.
 */

// Member-related types based on backend API schemas
export interface MemberAdd {
  user_id?: string | null;
  email?: string | null;
  role?: 'read' | 'write' | 'admin';
  permission?: string | null;
  send_invitation?: boolean;
  message?: string | null;
}

export interface MemberResponse {
  id: string;
  user: {
    id: string;
    name: string;
    email: string;
  };
  role: 'read' | 'write' | 'admin';
  permission: string | null;
  added_at: string;
  is_owner: boolean;
  can_manage_members: boolean;
}

export const membersApi = {
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
    }
    
    return defaultMessage;
  },

  /**
   * Get project members
   */
  async getProjectMembers(projectId: string): Promise<MemberResponse[]> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/members`, {
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
        `Failed to fetch project members (${response.status}): ${response.statusText}`
      );
      throw new Error(errorMessage);
    }

    return response.json();
  },

  /**
   * Add member to project
   */
  async addProjectMember(projectId: string, memberData: MemberAdd): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/members`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(memberData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = this.extractErrorMessage(
        errorData, 
        `Failed to add project member (${response.status}): ${response.statusText}`
      );
      throw new Error(errorMessage);
    }

    return response.json();
  },
}; 