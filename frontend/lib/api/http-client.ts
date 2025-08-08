/**
 * Centralized HTTP client with automatic token refresh
 * 
 * This module provides a fetch wrapper that automatically handles token refresh
 * when API calls receive 401 Unauthorized responses.
 */

import { authService } from '@/lib/services/auth-service';

interface ApiResponse<T = any> {
  ok: boolean;
  status: number;
  statusText: string;
  data?: T;
  error?: string;
}

interface RequestConfig extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
  skipAuth?: boolean;
  skipRefresh?: boolean;
  enableLogging?: boolean;
  errorExtractor?: (data: any, defaultMessage: string) => string;
}

class HttpClient {
  private static instance: HttpClient;
  private refreshPromise: Promise<boolean> | null = null;
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  static getInstance(): HttpClient {
    if (!HttpClient.instance) {
      HttpClient.instance = new HttpClient();
    }
    return HttpClient.instance;
  }

  /**
   * Default error message extractor (can be overridden per request)
   */
  private defaultExtractErrorMessage(data: any, defaultMessage: string): string {
    if (typeof data === 'string') return data;
    
    if (data?.detail) {
      if (typeof data.detail === 'string') return data.detail;
      if (Array.isArray(data.detail) && data.detail[0]?.msg) {
        return data.detail[0].msg;
      }
    }
    
    if (data?.message) return data.message;
    if (data?.error) return data.error;
    
    return defaultMessage;
  }

  /**
   * Enhanced error message extractor that matches existing API patterns
   */
  private extractErrorMessage(data: any, defaultMessage: string, customExtractor?: (data: any, defaultMessage: string) => string): string {
    if (customExtractor) {
      return customExtractor(data, defaultMessage);
    }

    // Enhanced extraction logic matching existing patterns
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
  }

  /**
   * Safely serialize data for logging to avoid reference issues
   */
  private safeLogData(data: any): any {
    if (!data) return 'No response data';
    
    try {
      return JSON.parse(JSON.stringify(data));
    } catch (error) {
      return `[Object: ${typeof data}]`;
    }
  }

  /**
   * Enhanced logging that preserves existing API logging patterns
   */
  private logError(context: string, response: Response, data: any): void {
    const logData = this.safeLogData(data);
    console.error(`${context} API error - Server error`);
    console.error(`Status: ${response.status} ${response.statusText}`);
    console.error('Response data:', JSON.stringify(logData, null, 2));
  }

  /**
   * Make HTTP request with automatic token refresh
   */
  async request<T = any>(
    endpoint: string,
    config: RequestConfig = {}
  ): Promise<T> {
    const { 
      skipAuth = false, 
      skipRefresh = false, 
      enableLogging = true,
      errorExtractor,
      ...requestConfig 
    } = config;

    // Build full URL
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;

    // Prepare headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...config.headers,
    };

    // Add auth token if not skipped
    if (!skipAuth) {
      const token = authService.getAccessToken();
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
    }

    const requestOptions: RequestInit = {
      ...requestConfig,
      headers,
    };

    try {
      // Make the request
      const response = await fetch(url, requestOptions);
      
      // Handle 401 Unauthorized - attempt token refresh
      if (response.status === 401 && !skipAuth && !skipRefresh) {
        const refreshSuccess = await this.handleTokenRefresh();
        
        if (refreshSuccess) {
          // Retry the original request with new token
          const newToken = authService.getAccessToken();
          if (newToken) {
            headers.Authorization = `Bearer ${newToken}`;
            const retryResponse = await fetch(url, { ...requestOptions, headers });
            return this.processResponse<T>(retryResponse, endpoint, enableLogging, errorExtractor);
          }
        }
        
        // If refresh failed or no new token, handle as error
        return this.processResponse<T>(response, endpoint, enableLogging, errorExtractor);
      }

      return this.processResponse<T>(response, endpoint, enableLogging, errorExtractor);
    } catch (error) {
      console.error('HTTP Client request failed:', error);
      throw new Error(error instanceof Error ? error.message : 'Network request failed');
    }
  }

  /**
   * Handle token refresh with deduplication
   */
  private async handleTokenRefresh(): Promise<boolean> {
    // If refresh is already in progress, wait for it
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    // Start new refresh
    this.refreshPromise = this.performTokenRefresh();
    
    try {
      const result = await this.refreshPromise;
      return result;
    } finally {
      // Clear the promise regardless of outcome
      this.refreshPromise = null;
    }
  }

  /**
   * Perform the actual token refresh
   */
  private async performTokenRefresh(): Promise<boolean> {
    try {
      console.log('Attempting token refresh...');
      const success = await authService.refreshAccessToken();
      
      if (success) {
        console.log('Token refresh successful');
        return true;
      } else {
        console.log('Token refresh failed - redirecting to login');
        // Redirect to login page
        if (typeof window !== 'undefined') {
          window.location.href = '/login?expired=true';
        }
        return false;
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      // Redirect to login page on error
      if (typeof window !== 'undefined') {
        window.location.href = '/login?expired=true';
      }
      return false;
    }
  }

  /**
   * Process fetch response and extract data with enhanced error handling
   */
  private async processResponse<T>(
    response: Response, 
    endpoint: string, 
    enableLogging: boolean = true,
    errorExtractor?: (data: any, defaultMessage: string) => string
  ): Promise<T> {
    let data: any;
    
    try {
      data = await response.json();
    } catch (error) {
      if (enableLogging) {
        console.error(`${endpoint} JSON parse error:`, error);
      }
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      if (enableLogging) {
        this.logError(endpoint, response, data);
      }
      
      const errorMessage = this.extractErrorMessage(
        data,
        `Request failed (${response.status}): ${response.statusText || 'Unknown error'}`,
        errorExtractor
      );
      throw new Error(errorMessage);
    }

    return data as T;
  }

  /**
   * Convenience methods for different HTTP verbs with full configuration support
   */
  async get<T = any>(endpoint: string, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'GET' });
  }

  async post<T = any>(endpoint: string, data?: any, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, {
      ...config,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T = any>(endpoint: string, data?: any, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, {
      ...config,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T = any>(endpoint: string, data?: any, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, {
      ...config,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T = any>(endpoint: string, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'DELETE' });
  }

  /**
   * Factory method to create API client with custom error extractor
   */
  withErrorExtractor(extractor: (data: any, defaultMessage: string) => string) {
    return {
      get: <T = any>(endpoint: string, config?: Omit<RequestConfig, 'errorExtractor'>) => 
        this.get<T>(endpoint, { ...config, errorExtractor: extractor }),
      post: <T = any>(endpoint: string, data?: any, config?: Omit<RequestConfig, 'errorExtractor'>) => 
        this.post<T>(endpoint, data, { ...config, errorExtractor: extractor }),
      put: <T = any>(endpoint: string, data?: any, config?: Omit<RequestConfig, 'errorExtractor'>) => 
        this.put<T>(endpoint, data, { ...config, errorExtractor: extractor }),
      patch: <T = any>(endpoint: string, data?: any, config?: Omit<RequestConfig, 'errorExtractor'>) => 
        this.patch<T>(endpoint, data, { ...config, errorExtractor: extractor }),
      delete: <T = any>(endpoint: string, config?: Omit<RequestConfig, 'errorExtractor'>) => 
        this.delete<T>(endpoint, { ...config, errorExtractor: extractor })
    };
  }
}

// Export singleton instance
export const httpClient = HttpClient.getInstance();
export default httpClient; 