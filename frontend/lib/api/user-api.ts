/**
 * User API
 * 
 * Handles user-related API calls including current user profile
 */

export interface UserResponse {
  id: string;
  name: string;
  email: string;
  email_verified: boolean;
  interests: string[];
  intro: string;
  created_at: string;
  last_login?: string | null;
}

export interface UserProfileUpdate {
  name?: string;
  email?: string;
  interests?: string[];
  intro?: string;
}

export interface UserStats {
  user_id: string;
  created_at: string;
  last_login?: string | null;
  email_verified: boolean;
  interests_count: number;
  projects_count: number;
  papers_count: number;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export const userApi = {
  /**
   * Get authentication token
   */
  getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('accessToken') || sessionStorage.getItem('accessToken');
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
   * Get current user profile
   * Endpoint: GET /api/v1/auth/me
   */
  async getCurrentUser(): Promise<UserResponse> {
    const httpClient = (await import('./http-client')).default;
    
    // Use enhanced HTTP client with existing error extraction logic
    return await httpClient
      .withErrorExtractor(this.extractErrorMessage.bind(this))
      .get<UserResponse>('/api/v1/auth/me');
  },

  /**
   * Update current user profile
   * Endpoint: PUT /api/v1/auth/me
   */
  async updateCurrentUser(profileUpdate: UserProfileUpdate): Promise<{ success: boolean; message: string; user: UserResponse }> {
    const httpClient = (await import('./http-client')).default;
    
    return await httpClient
      .withErrorExtractor(this.extractErrorMessage.bind(this))
      .put<{ success: boolean; message: string; user: UserResponse }>('/api/v1/auth/me', profileUpdate);
  },

  /**
   * Get current user statistics
   * Endpoint: GET /api/v1/auth/me/stats
   */
  async getUserStats(): Promise<UserStats> {
    const httpClient = (await import('./http-client')).default;
    
    const data = await httpClient
      .withErrorExtractor(this.extractErrorMessage.bind(this))
      .get<{ stats: UserStats }>('/api/v1/auth/me/stats');
    return data.stats;
  },

  /**
   * Change user password
   * Endpoint: POST /api/v1/auth/me/change-password
   */
  async changePassword(passwordData: PasswordChangeRequest): Promise<{ success: boolean; message: string }> {
    const httpClient = (await import('./http-client')).default;
    
    return await httpClient
      .withErrorExtractor(this.extractErrorMessage.bind(this))
      .post<{ success: boolean; message: string }>('/api/v1/auth/me/change-password', passwordData);
  },

  /**
   * Delete current user account
   * Endpoint: DELETE /api/v1/auth/me
   */
  async deleteAccount(): Promise<{ success: boolean; message: string }> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Delete account JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Delete account API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to delete account (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Get public user profile by ID
   * Endpoint: GET /api/v1/auth/users/{user_id}
   */
  async getUserPublicProfile(userId: string): Promise<{
    id: string;
    name: string;
    interests: string[];
    intro: string;
    created_at: string;
  }> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/auth/users/${userId}`, {
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
      console.error('Get user public profile JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get user public profile API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch user public profile (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Logout user by invalidating the current session
   * Endpoint: POST /api/v1/auth/logout
   */
  async logout(): Promise<{ success: boolean; message: string }> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const token = this.getAuthToken();
    
    if (!token) {
      // If no token, consider logout successful (user not logged in)
      return { success: true, message: 'Already logged out' };
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json',
        },
      });

      let data: any;
      try {
        data = await response.json();
      } catch (error) {
        console.error('Logout JSON parse error:', error);
        // Even if parsing fails, we can still clear local tokens
        data = { success: true, message: 'Logged out successfully' };
      }

      if (!response.ok) {
        console.warn('Logout API error, but clearing local tokens anyway:', {
          status: response.status,
          statusText: response.statusText,
          data: data
        });
        // Even if backend logout fails, we should clear local tokens
        data = { success: true, message: 'Logged out locally' };
      }

      return data;
    } catch (error) {
      console.warn('Logout request failed, but clearing local tokens:', error);
      // Network errors shouldn't prevent local logout
      return { success: true, message: 'Logged out locally' };
    }
  },

  /**
   * Complete logout process - calls backend and clears local storage
   */
  async completeLogout(): Promise<void> {
    // First try to logout from backend
    await this.logout();
    
    // Always clear local tokens regardless of backend response
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    sessionStorage.removeItem('accessToken');
    sessionStorage.removeItem('refreshToken');
  },
}; 