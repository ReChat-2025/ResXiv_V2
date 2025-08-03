import { authApi, type LoginSuccess } from '@/lib/api/auth-api';
import { useAppStore } from '@/lib/stores/app-store';

interface User {
  id: string;
  name: string;
  email: string;
  email_verified: boolean;
  role?: string;
}

const TOKEN_KEYS = {
  ACCESS: 'accessToken',
  REFRESH: 'refreshToken',
} as const;

class AuthService {
  private static instance: AuthService;

  static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  /**
   * Get token from storage (localStorage or sessionStorage)
   */
  private getToken(key: string): string | null {
    if (typeof window === 'undefined') return null;
    
    return localStorage.getItem(key) || sessionStorage.getItem(key);
  }

  /**
   * Store token in appropriate storage based on remember preference
   */
  private setToken(key: string, value: string, remember = false): void {
    if (typeof window === 'undefined') return;
    
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem(key, value);
  }

  /**
   * Remove token from both storages
   */
  private removeToken(key: string): void {
    if (typeof window === 'undefined') return;
    
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  }

  /**
   * Get current access token
   */
  getAccessToken(): string | null {
    return this.getToken(TOKEN_KEYS.ACCESS);
  }

  /**
   * Get current refresh token
   */
  getRefreshToken(): string | null {
    return this.getToken(TOKEN_KEYS.REFRESH);
  }

  /**
   * Check if user is authenticated (has valid token)
   */
  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }

  /**
   * Login user and update app state
   */
  async login(email: string, password: string, rememberMe = false): Promise<LoginSuccess> {
    const response = await authApi.login(email, password, rememberMe);
    
    // Store tokens
    this.setToken(TOKEN_KEYS.ACCESS, response.tokens.access_token, rememberMe);
    this.setToken(TOKEN_KEYS.REFRESH, response.tokens.refresh_token, rememberMe);
    
    // Update app state
    const { setUser, setAuthenticated } = useAppStore.getState();
    setUser(response.user);
    setAuthenticated(true);
    
    return response;
  }

  /**
   * Register new user
   */
  async register(
    name: string,
    email: string,
    password: string,
    confirmPassword: string,
    acceptedTerms: boolean,
    interests: string[] = []
  ): Promise<any> {
    return await authApi.register(name, email, password, confirmPassword, acceptedTerms, interests);
  }

  /**
   * Logout user and clear state
   */
  async logout(): Promise<void> {
    const token = this.getAccessToken();
    
    // Call backend logout if token exists
    if (token) {
      await authApi.logout(token);
    }
    
    // Clear tokens
    this.removeToken(TOKEN_KEYS.ACCESS);
    this.removeToken(TOKEN_KEYS.REFRESH);
    
    // Clear app state
    const { setUser, setAuthenticated } = useAppStore.getState();
    setUser(null);
    setAuthenticated(false);
  }

  /**
   * Initialize auth state from stored tokens
   */
  initializeAuth(): void {
    const accessToken = this.getAccessToken();
    const { setAuthenticated, setUser } = useAppStore.getState();
    
    if (accessToken) {
      // TODO: Validate token with backend and fetch user info
      // For now, just set authenticated state
      setAuthenticated(true);
    } else {
      setAuthenticated(false);
      setUser(null);
    }
  }

  /**
   * Update user information in app store
   */
  updateUser(user: User): void {
    const { setUser } = useAppStore.getState();
    setUser(user);
  }

  /**
   * Request password reset email
   */
  async requestPasswordReset(email: string): Promise<any> {
    return await authApi.forgotPassword(email);
  }

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string, confirmPassword: string): Promise<any> {
    const result = await authApi.resetPassword(token, newPassword, confirmPassword);
    
    // Clear any stored tokens since all sessions are invalidated
    this.logout();
    
    return result;
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshAccessToken(): Promise<boolean> {
    try {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await authApi.refreshToken(refreshToken);
      
      // Update stored tokens
      this.setToken(TOKEN_KEYS.ACCESS, response.access_token, false);
      this.setToken(TOKEN_KEYS.REFRESH, response.refresh_token, false);
      
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      // Clear tokens on refresh failure
      this.logout();
      return false;
    }
  }

  /**
   * Check if current user's email is verified
   */
  isEmailVerified(): boolean {
    const { user } = useAppStore.getState();
    return (user as any)?.emailVerified ?? false;
  }

  /**
   * Get authorization header for API requests
   */
  getAuthHeader(): Record<string, string> {
    const token = this.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}

export const authService = AuthService.getInstance();
export { type User }; 