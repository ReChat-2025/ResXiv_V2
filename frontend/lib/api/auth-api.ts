/* Authentication API wrapper */

// Define minimal request/response types to satisfy strict TypeScript settings
export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginSuccess {
  success: boolean;
  tokens: Tokens;
  user: {
    id: string;
    name: string;
    email: string;
    email_verified: boolean;
    role?: string;
  };
  message?: string;
}

export const authApi = {
  /**
   * Safely serialize data for logging to avoid reference issues
   */
  safeLogData(data: any): any {
    if (!data) return 'No response data';
    
    try {
      return JSON.parse(JSON.stringify(data));
    } catch (error) {
      // If JSON serialization fails, return a safe representation
      return `[Object: ${typeof data}]`;
    }
  },

  /**
   * Extract error message from API response
   */
  extractErrorMessage(data: any, defaultMessage: string): string {
    if (data && typeof data === 'object') {
      // Direct string properties
      if (typeof data.detail === 'string') return data.detail;
      if (typeof data.message === 'string') return data.message;
      if (typeof data.error === 'string') return data.error;
      
      // Nested error objects
      if (data.detail && typeof data.detail === 'object') {
        if (data.detail.message && typeof data.detail.message === 'string') {
          return data.detail.message;
        }
        if (data.detail.error && typeof data.detail.error === 'string') {
          return data.detail.error;
        }
      }
      
      // Array of errors (validation)
      if (Array.isArray(data.detail)) {
        return data.detail.map((err: any) => err.msg || err).join(', ');
      }
    }
    
    return defaultMessage;
  },

  /**
   * Check if an error is a user authentication error (not a server error)
   */
  isUserAuthError(data: any): boolean {
    if (!data || typeof data !== 'object') return false;
    
    const message = this.extractErrorMessage(data, '').toLowerCase();
    
    // Common user authentication error patterns
    const userErrorPatterns = [
      'invalid email or password',
      'invalid credentials',
      'authentication failed',
      'account not found',
      'incorrect password',
      'user not found',
      'authentication_error'
    ];
    
    return userErrorPatterns.some(pattern => message.includes(pattern));
  },

  /**
   * Authenticate a user against the backend
   * @param email Email address
   * @param password Password
   * @param remember_me Persist session across browser restarts
   */
  async login(
    email: string,
    password: string,
    remember_me = false
  ): Promise<LoginSuccess> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    const url = `${API_BASE_URL}/api/v1/auth/login`;
    const requestBody = { email, password, remember_me };
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    let data: Record<string, any>;
    try {
      data = (await response.json()) as Record<string, any>;
    } catch (error) {
      console.error('Login JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      // Check if this is a user authentication error vs server error
      if (this.isUserAuthError(data)) {
        console.error('Login API error - User authentication failed');
        console.error(`Status: ${response.status} ${response.statusText}`);
        console.error('Response data:', JSON.stringify(data, null, 2));
        // User authentication errors should be shown as user errors
        const errorMessage = this.extractErrorMessage(data, 'Invalid email or password');
        throw new Error(errorMessage);
      } else {
        console.error('Login API error - Server error');
        console.error(`Status: ${response.status} ${response.statusText}`);
        console.error('Response data:', JSON.stringify(data, null, 2));
        // Actual server errors
        const errorMessage = this.extractErrorMessage(
          data, 
          `Login failed (${response.status}): ${response.statusText || 'Unknown error'}`
        );
        throw new Error(errorMessage);
      }
    }

    return data as LoginSuccess;
  },

  /**
   * Refresh access token using refresh token
   */
  async refreshToken(refreshToken: string): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    let data: Record<string, any>;
    try {
      data = (await response.json()) as Record<string, any>;
    } catch (error) {
      console.error('Refresh token JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      // Create a deep copy of data for logging to avoid reference issues
      const logData = this.safeLogData(data);
      console.error('Refresh token API error:', {
        status: response.status,
        statusText: response.statusText,
        url: response.url,
        data: logData
      });
       
      const errorMessage = this.extractErrorMessage(
        data, 
        `Token refresh failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
       
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Register a new user account
   */
  async register(
    name: string,
    email: string,
    password: string,
    confirm_password: string,
    accepted_terms: boolean,
    interests: string[] = []
  ): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    const url = `${API_BASE_URL}/api/v1/auth/register`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name,
        email,
        password,
        confirm_password,
        accepted_terms,
        interests,
      }),
    });

    let data: Record<string, any>;
    try {
      data = (await response.json()) as Record<string, any>;
    } catch (error) {
      console.error('JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      // Create a deep copy of data for logging to avoid reference issues
      const logData = this.safeLogData(data);
      console.error('Registration API error:', {
        status: response.status,
        statusText: response.statusText,
        url: response.url,
        data: logData
      });
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Registration failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
       
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Verify email address using verification token
   */
  async verifyEmail(token: string): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    let data: Record<string, any>;
    try {
      data = (await response.json()) as Record<string, any>;
    } catch (error) {
      console.error('Email verification JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      // Extract error message from the nested structure
      let errorMessage = "Email verification failed";
      
      if (data && data.detail) {
        if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        } else if (typeof data.detail === 'object' && data.detail.message) {
          errorMessage = data.detail.message;
        } else if (typeof data.detail === 'object' && data.detail.error) {
          errorMessage = data.detail.error;
        }
      } else if (data && data.message) {
        errorMessage = data.message;
      }
      
      // Provide more user-friendly error messages
      if (errorMessage.includes('Invalid or expired')) {
        errorMessage = 'This verification link has expired or is invalid. Please request a new verification email.';
      } else if (errorMessage.includes('email verification failed')) {
        errorMessage = 'Email verification failed. The link may have expired or already been used.';
      }
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Resend verification email
   */
  async resendVerificationEmail(email: string): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    
    const url = `${API_BASE_URL}/api/v1/auth/resend-verification?email=${encodeURIComponent(email)}`;
    console.log('Calling resend verification API:', url);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
    });

    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries(response.headers.entries()));

    // Clone response to allow multiple reads
    const responseClone = response.clone();

    let data: Record<string, any>;
    try {
      data = (await response.json()) as Record<string, any>;
    } catch (error) {
      console.error('Resend verification JSON parse error:', error);
      
      // If JSON parsing fails, try to get response text for debugging
      const responseText = await responseClone.text().catch(() => 'Unable to read response');
      console.error('Response status:', response.status);
      console.error('Response text:', responseText);
      
      if (!response.ok) {
        throw new Error(`Server error (${response.status}): Unable to process response`);
      }
      
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      // Create a deep copy of data for logging to avoid reference issues
      const logData = this.safeLogData(data);
      console.error('Resend verification API error:', {
        status: response.status,
        statusText: response.statusText,
        url: response.url,
        data: logData
      });
       
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to resend verification email (${response.status}): ${response.statusText || 'Unknown error'}`
      );
       
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Request password reset email
   */
  async forgotPassword(email: string): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/forgot-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    let data: Record<string, any>;
    try {
      data = (await response.json()) as Record<string, any>;
    } catch (error) {
      console.error('Forgot password JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      // Use simple, reliable logging
      console.error('Forgot password API error - Backend service issue');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error(`URL: ${response.url}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
       
      const originalMessage = this.extractErrorMessage(data, '');
      
      // Provide user-friendly messages for common backend issues
      let errorMessage;
      if (originalMessage.includes('password reset request failed') || 
          originalMessage.includes('internal_error')) {
        errorMessage = 'The password reset service is temporarily unavailable. Please try again in a few minutes.';
      } else {
        errorMessage = this.extractErrorMessage(
          data, 
          `Password reset failed (${response.status}): ${response.statusText || 'Unknown error'}`
        );
      }
       
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Reset password using reset token
   */
  async resetPassword(token: string, newPassword: string, confirmNewPassword: string): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token,
        new_password: newPassword,
        confirm_new_password: confirmNewPassword,
      }),
    });

    let data: Record<string, any>;
    try {
      data = (await response.json()) as Record<string, any>;
    } catch (error) {
      console.error('Reset password JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      // Create a deep copy of data for logging to avoid reference issues
      const logData = this.safeLogData(data);
      console.error('Reset password API error:', {
        status: response.status,
        statusText: response.statusText,
        url: response.url,
        data: logData
      });
       
      const errorMessage = this.extractErrorMessage(
        data, 
        `Password reset failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
       
      throw new Error(errorMessage);
    }

    return data;
  },





  /**
   * Change user password (requires authentication)
   */
  async changePassword(
    currentPassword: string,
    newPassword: string,
    confirmNewPassword: string
  ): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = localStorage.getItem('accessToken');
    
    if (!token) {
      throw new Error('Authentication required');
    }
    
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/me/change-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_new_password: confirmNewPassword,
      }),
    });

    let data: Record<string, any>;
    try {
      data = (await response.json()) as Record<string, any>;
    } catch (error) {
      console.error('Change password JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      const logData = this.safeLogData(data);
      console.error('Change password API error:', {
        status: response.status,
        statusText: response.statusText,
        url: response.url,
        data: logData
      });
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Password change failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
       
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Verify access token
   */
  async verifyToken(): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = localStorage.getItem('accessToken');
    
    if (!token) {
      throw new Error('No token found');
    }
    
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/verify`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    let data: Record<string, any>;
    try {
      data = (await response.json()) as Record<string, any>;
    } catch (error) {
      console.error('Verify token JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      const logData = this.safeLogData(data);
      console.error('Verify token API error:', {
        status: response.status,
        statusText: response.statusText,
        url: response.url,
        data: logData
      });
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Token verification failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
       
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Logout user (optional backend call)
   */
  async logout(token?: string): Promise<void> {
    if (!token) return;
    
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    try {
      await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.warn('Logout API call failed:', error);
    }
  },
}; 