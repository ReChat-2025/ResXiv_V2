/**
 * Settings API
 * 
 * Handles settings-related API calls including user profile,
 * project settings, team management, and billing.
 * Based on actual backend API endpoints from localhost:8001/docs
 */

export interface UserProfileUpdate {
  name?: string;
  email?: string;
  interests?: string[];
  intro?: string;
}

export interface ProjectSettingsUpdate {
  name?: string;
  slug?: string;
  description?: string;
  repo_url?: string;
  is_private?: boolean;
}

export interface TeamInvitation {
  email: string;
  role: 'admin' | 'write' | 'read';
  permission?: string;
  message?: string;
  expires_in_days?: number;
}

export interface MemberAdd {
  user_id?: string;
  email?: string;
  role: 'admin' | 'write' | 'read';
  permission?: string;
  send_invitation?: boolean;
  message?: string;
}

export interface PendingInvite {
  id: string;
  email: string;
  role: string;
  status: 'pending' | 'accepted' | 'expired';
  invited_at: string;
  expires_at: string;
  invited_by: {
    id: string;
    name: string;
    email: string;
  };
}

export interface TeamMember {
  id: string;
  user: {
    id: string;
    name: string;
    email: string;
  };
  role: string;
  status: 'active' | 'pending' | 'inactive';
  joined_at: string;
  can_manage_members: boolean;
}

export interface ProjectResponse {
  id: string;
  name: string;
  slug?: string;
  description?: string;
  repo_url?: string;
  is_private: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
  member_count: number;
  paper_count: number;
}

export interface MemberResponse {
  id: string;
  user_id: string;
  user: {
    id: string;
    name: string;
    email: string;
  };
  role: string;
  permissions?: string[];
  added_at: string;
  is_owner: boolean;
  can_manage_members: boolean;
}

class SettingsApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
  }

  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return (
      localStorage.getItem('accessToken') ||
      localStorage.getItem('authToken')
    );
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getAuthToken();
    if (!token) {
      throw new Error('Authentication required');
    }

    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(this.extractErrorMessage(errorData, `Request failed with status ${response.status}`));
    }

    return response.json();
  }

  private extractErrorMessage(data: any, fallback: string): string {
    if (typeof data === 'string') return data;
    if (data?.detail) {
      if (typeof data.detail === 'string') return data.detail;
      if (Array.isArray(data.detail)) {
        return data.detail.map((err: any) => err.msg || err).join(', ');
      }
    }
    if (data?.error) return data.error;
    if (data?.message) return data.message;
    return fallback;
  }

  // User Profile Management (uses auth endpoints)
  async updateUserProfile(profileData: UserProfileUpdate): Promise<any> {
    return this.makeRequest(
      '/api/v1/auth/me',
      {
        method: 'PUT',
        body: JSON.stringify(profileData),
      }
    );
  }

  async getUserProfile(): Promise<any> {
    return this.makeRequest('/api/v1/auth/me');
  }

  // Project Settings Management
  async updateProjectSettings(projectId: string, settingsData: ProjectSettingsUpdate): Promise<ProjectResponse> {
    return this.makeRequest(
      `/api/v1/projects/${projectId}`,
      {
        method: 'PUT',
        body: JSON.stringify(settingsData),
      }
    );
  }

  async getProjectSettings(projectId: string): Promise<ProjectResponse> {
    return this.makeRequest(`/api/v1/projects/${projectId}`);
  }

  async deleteProject(projectId: string): Promise<void> {
    return this.makeRequest(
      `/api/v1/projects/${projectId}`,
      {
        method: 'DELETE',
      }
    );
  }

  // Team Management
  async getTeamMembers(projectId: string): Promise<MemberResponse[]> {
    return this.makeRequest(`/api/v1/projects/${projectId}/members`);
  }

  async addTeamMember(projectId: string, memberData: MemberAdd): Promise<any> {
    return this.makeRequest(
      `/api/v1/projects/${projectId}/members`,
      {
        method: 'POST',
        body: JSON.stringify(memberData),
      }
    );
  }

  async updateMemberRole(projectId: string, memberUserId: string, role: string, permission?: string): Promise<any> {
    return this.makeRequest(
      `/api/v1/projects/${projectId}/members/${memberUserId}`,
      {
        method: 'PUT',
        body: JSON.stringify({ role, permission }),
      }
    );
  }

  async removeTeamMember(projectId: string, memberUserId: string): Promise<any> {
    return this.makeRequest(
      `/api/v1/projects/${projectId}/members/${memberUserId}`,
      {
        method: 'DELETE',
      }
    );
  }

  // Invitation Management
  async createInvitation(projectId: string, invitation: TeamInvitation): Promise<any> {
    return this.makeRequest(
      `/api/v1/projects/${projectId}/invitations`,
      {
        method: 'POST',
        body: JSON.stringify(invitation),
      }
    );
  }

  async getProjectInvitations(projectId: string): Promise<any> {
    return this.makeRequest(`/api/v1/projects/${projectId}/invitations`);
  }

  async withdrawInvitation(projectId: string, invitationId: string): Promise<any> {
    return this.makeRequest(
      `/api/v1/projects/${projectId}/invitations/${invitationId}`,
      {
        method: 'DELETE',
      }
    );
  }

  async bulkInviteMembers(projectId: string, invitations: TeamInvitation[]): Promise<any> {
    return this.makeRequest(
      `/api/v1/projects/${projectId}/invitations/bulk`,
      {
        method: 'POST',
        body: JSON.stringify({ invitations }),
      }
    );
  }

  // Project Analytics and Stats
  async getProjectStats(projectId: string): Promise<any> {
    return this.makeRequest(`/api/v1/projects/${projectId}/stats`);
  }

  async getProjectActivity(projectId: string): Promise<any> {
    return this.makeRequest(`/api/v1/projects/${projectId}/activity`);
  }

  async getCollaborationStats(projectId: string): Promise<any> {
    return this.makeRequest(`/api/v1/analytics/project/${projectId}/collaboration`);
  }

  // Project Access Management
  async getProjectAccess(projectId: string): Promise<any> {
    return this.makeRequest(`/api/v1/projects/${projectId}/access`);
  }

  async updateProjectAccess(projectId: string, accessData: any): Promise<any> {
    return this.makeRequest(
      `/api/v1/projects/${projectId}/access`,
      {
        method: 'PUT',
        body: JSON.stringify(accessData),
      }
    );
  }

  // Project Health and Diagnostics
  async getProjectHealth(projectId: string): Promise<any> {
    return this.makeRequest(`/api/v1/projects/${projectId}/health`);
  }

  async getProjectDiagnostics(projectId: string): Promise<any> {
    return this.makeRequest(`/api/v1/projects/${projectId}/diagnostics`);
  }

  // Storage and File Management
  async getStorageUsage(projectId: string): Promise<any> {
    return this.makeRequest(`/api/v1/files/projects/${projectId}/storage/usage`);
  }

  async cleanupProjectStorage(projectId: string): Promise<any> {
    return this.makeRequest(
      `/api/v1/files/projects/${projectId}/storage/cleanup`,
      {
        method: 'POST',
      }
    );
  }

  // Password Management
  async changePassword(currentPassword: string, newPassword: string): Promise<any> {
    return this.makeRequest(
      '/api/v1/auth/me/change-password',
      {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      }
    );
  }

  // User Analytics
  async getUserEngagement(): Promise<any> {
    return this.makeRequest('/api/v1/analytics/user/engagement');
  }

  async getUserStats(): Promise<any> {
    return this.makeRequest('/api/v1/auth/me/stats');
  }

  // Project Link Generation
  async generateProjectInviteLink(projectId: string): Promise<string> {
    // Generate a shareable project link
    const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
    return `${baseUrl}/projects/${projectId}/join`;
  }

  // Help Resources (Mock implementations)
  async getHelpResources(): Promise<any[]> {
    return [
      {
        id: 'guide',
        name: 'Guide',
        url: 'https://docs.resxiv.com/guide',
        description: 'Complete user guide and tutorials'
      },
      {
        id: 'changelog',
        name: 'Changelog', 
        url: 'https://docs.resxiv.com/changelog',
        description: 'Latest updates and feature releases'
      },
      {
        id: 'blogs',
        name: 'Blogs',
        url: 'https://blog.resxiv.com',
        description: 'Latest news and insights'
      }
    ];
  }

  // Support (would need to be implemented in backend)
  async sendSupportMessage(message: string, subject?: string): Promise<any> {
    // This would need to be implemented in the backend
    console.log('Support message:', { message, subject });
    return { success: true, message: 'Support message sent' };
  }
}

export const settingsApi = new SettingsApiClient(); 