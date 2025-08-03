/**
 * Project Members API
 * 
 * Handles project member management operations
 */

export interface UserBasicInfo {
  id: string;
  name: string;
  email: string;
}

export interface ProjectMember {
  id: string;
  user: UserBasicInfo;
  role: 'owner' | 'admin' | 'write' | 'read';
  permission?: string;
  added_at: string;
  is_owner: boolean;
  can_manage_members: boolean;
}

export interface MemberAdd {
  user_id?: string;
  email?: string;
  role: 'owner' | 'admin' | 'write' | 'read';
  permission?: string;
  send_invitation?: boolean;
  message?: string;
}

export interface MemberUpdate {
  role?: 'owner' | 'admin' | 'write' | 'read';
  permission?: string;
}

export interface MembersResponse {
  success: boolean;
  data: ProjectMember[];
  message?: string;
}

export interface MemberResponse {
  success: boolean;
  data?: ProjectMember;
  member?: ProjectMember;
  message?: string;
  error?: string;
}

class MembersApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
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

    const data = await response.json().catch(() => {
      throw new Error('Invalid server response');
    });

    if (!response.ok) {
      throw new Error(this.extractErrorMessage(data, 'Request failed'));
    }

    return data;
  }

  private extractErrorMessage(data: any, fallback: string): string {
    if (typeof data === 'string') return data;
    if (data?.detail) return data.detail;
    if (data?.error) return data.error;
    if (data?.message) return data.message;
    return fallback;
  }

  async getProjectMembers(projectId: string): Promise<ProjectMember[]> {
    const response = await this.makeRequest<ProjectMember[]>(
      `/api/v1/projects/${projectId}/members`
    );
    return response;
  }

  async addProjectMember(projectId: string, memberData: MemberAdd): Promise<MemberResponse> {
    return this.makeRequest<MemberResponse>(
      `/api/v1/projects/${projectId}/members`,
      {
        method: 'POST',
        body: JSON.stringify(memberData),
      }
    );
  }

  async updateProjectMember(
    projectId: string, 
    memberUserId: string, 
    memberData: MemberUpdate
  ): Promise<MemberResponse> {
    return this.makeRequest<MemberResponse>(
      `/api/v1/projects/${projectId}/members/${memberUserId}`,
      {
        method: 'PUT',
        body: JSON.stringify(memberData),
      }
    );
  }

  async removeProjectMember(projectId: string, memberUserId: string): Promise<MemberResponse> {
    return this.makeRequest<MemberResponse>(
      `/api/v1/projects/${projectId}/members/${memberUserId}`,
      {
        method: 'DELETE',
      }
    );
  }
}

export const membersApi = new MembersApiClient();
