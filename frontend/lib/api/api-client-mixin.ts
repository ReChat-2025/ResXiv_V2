/**
 * API Client Mixin - L6 Engineering Pattern
 * 
 * Provides composable enhancement for existing API clients to add:
 * - Automatic token refresh
 * - Enhanced error handling 
 * - Consistent logging
 * 
 * Usage: Extend existing APIs without breaking changes
 */

import type httpClient from './http-client';
type HttpClient = typeof httpClient;

interface ApiClient {
  getAuthToken(): string | null;
  extractErrorMessage(data: any, defaultMessage: string): string;
  safeLogData?(data: any): any;
}

interface EnhancedApiMethods {
  get<T>(endpoint: string, options?: { skipAuth?: boolean; skipRefresh?: boolean }): Promise<T>;
  post<T>(endpoint: string, data?: any, options?: { skipAuth?: boolean; skipRefresh?: boolean }): Promise<T>;
  put<T>(endpoint: string, data?: any, options?: { skipAuth?: boolean; skipRefresh?: boolean }): Promise<T>;
  patch<T>(endpoint: string, data?: any, options?: { skipAuth?: boolean; skipRefresh?: boolean }): Promise<T>;
  delete<T>(endpoint: string, options?: { skipAuth?: boolean; skipRefresh?: boolean }): Promise<T>;
}

/**
 * Mixin function that enhances existing API clients with HTTP client capabilities
 * 
 * Follows the Mixin Pattern - adds functionality without inheritance
 */
export function withHttpClientEnhancement<T extends ApiClient>(
  apiClient: T
): T & { enhanced: EnhancedApiMethods } {
  let httpClientPromise: Promise<HttpClient> | null = null;

  const getHttpClient = async (): Promise<HttpClient> => {
    if (!httpClientPromise) {
      httpClientPromise = import('./http-client').then(module => module.default);
    }
    return httpClientPromise;
  };

  const enhanced: EnhancedApiMethods = {
    async get<R>(endpoint: string, options: { skipAuth?: boolean; skipRefresh?: boolean } = {}): Promise<R> {
      const httpClient = await getHttpClient();
      return httpClient
        .withErrorExtractor(apiClient.extractErrorMessage.bind(apiClient))
        .get<R>(endpoint, options);
    },

    async post<R>(endpoint: string, data?: any, options: { skipAuth?: boolean; skipRefresh?: boolean } = {}): Promise<R> {
      const httpClient = await getHttpClient();
      return httpClient
        .withErrorExtractor(apiClient.extractErrorMessage.bind(apiClient))
        .post<R>(endpoint, data, options);
    },

    async put<R>(endpoint: string, data?: any, options: { skipAuth?: boolean; skipRefresh?: boolean } = {}): Promise<R> {
      const httpClient = await getHttpClient();
      return httpClient
        .withErrorExtractor(apiClient.extractErrorMessage.bind(apiClient))
        .put<R>(endpoint, data, options);
    },

    async patch<R>(endpoint: string, data?: any, options: { skipAuth?: boolean; skipRefresh?: boolean } = {}): Promise<R> {
      const httpClient = await getHttpClient();
      return httpClient
        .withErrorExtractor(apiClient.extractErrorMessage.bind(apiClient))
        .patch<R>(endpoint, data, options);
    },

    async delete<R>(endpoint: string, options: { skipAuth?: boolean; skipRefresh?: boolean } = {}): Promise<R> {
      const httpClient = await getHttpClient();
      return httpClient
        .withErrorExtractor(apiClient.extractErrorMessage.bind(apiClient))
        .delete<R>(endpoint, options);
    }
  };

  return Object.assign(apiClient, { enhanced });
}

/**
 * Decorator function for API methods to add automatic token refresh
 * 
 * Usage: @withTokenRefresh 
 * async someApiMethod() { ... }
 */
export function withTokenRefresh<T extends (...args: any[]) => Promise<any>>(
  originalMethod: T,
  context: ClassMethodDecoratorContext
): T {
  return (async function(this: any, ...args: any[]) {
    try {
      return await originalMethod.apply(this, args);
    } catch (error) {
      // If the error indicates token expiration, try refresh
      if (error instanceof Error && error.message.includes('401')) {
        const authService = (await import('../services/auth-service')).authService;
        const refreshSuccess = await authService.refreshAccessToken();
        
        if (refreshSuccess) {
          // Retry the original method
          return await originalMethod.apply(this, args);
        }
      }
      throw error;
    }
  }) as T;
}

/**
 * Factory for creating backward-compatible API clients
 * 
 * Preserves all existing functionality while adding enhancements
 */
export class ApiClientFactory {
  /**
   * Create enhanced API client that maintains backward compatibility
   */
  static enhance<T extends ApiClient>(apiClient: T): T & { enhanced: EnhancedApiMethods } {
    return withHttpClientEnhancement(apiClient);
  }

  /**
   * Create a bridge between old and new API patterns
   */
  static createLegacyBridge<T extends ApiClient>(apiClient: T) {
    const enhanced = this.enhance(apiClient);
    
    return {
      // Original API methods (unchanged)
      ...apiClient,
      
      // Enhanced methods (with token refresh)
      enhanced: enhanced.enhanced,
      
      // Convenience method to migrate gradually
      async migrateMethod<R>(
        methodName: string, 
        endpoint: string, 
        data?: any, 
        method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' = 'GET'
      ): Promise<R> {
        console.warn(`Method ${methodName} is using legacy implementation. Consider migrating to enhanced.${method.toLowerCase()}`);
        
        switch (method) {
          case 'GET':
            return enhanced.enhanced.get<R>(endpoint);
          case 'POST':
            return enhanced.enhanced.post<R>(endpoint, data);
          case 'PUT':
            return enhanced.enhanced.put<R>(endpoint, data);
          case 'PATCH':
            return enhanced.enhanced.patch<R>(endpoint, data);
          case 'DELETE':
            return enhanced.enhanced.delete<R>(endpoint);
          default:
            throw new Error(`Unsupported method: ${method}`);
        }
      }
    };
  }
}

export default ApiClientFactory; 