/**
 * Token Refresh Integration Demo - L6 Engineering Standards
 * 
 * This demonstrates the automatic token refresh system and shows
 * how to integrate it with existing APIs without breaking changes.
 */

import { userApi } from '../api/user-api';
import { projectsApi } from '../api/projects-api';
import { authService } from '../services/auth-service';
import { ApiClientFactory } from '../api/api-client-mixin';
import httpClient from '../api/http-client';

/**
 * Demo 1: Direct HTTP Client Usage (Recommended for new APIs)
 */
export async function demoDirectHttpClient() {
  console.log('=== Demo 1: Direct HTTP Client Usage ===');
  
  try {
    // This automatically handles token refresh on 401 responses
    const user = await httpClient.get('/api/v1/auth/me');
    console.log('✅ User data fetched with automatic token refresh:', user);
    
    const projects = await httpClient.get('/api/v1/projects/');
    console.log('✅ Projects fetched with automatic token refresh:', projects);
    
  } catch (error) {
    console.error('❌ Request failed:', error);
  }
}

/**
 * Demo 2: Enhanced Existing APIs (Backward Compatible)
 */
export async function demoEnhancedExistingApis() {
  console.log('=== Demo 2: Enhanced Existing APIs ===');
  
  try {
    // Using enhanced user API (preserves all existing functionality)
    const user = await userApi.getCurrentUser();
    console.log('✅ User fetched via enhanced API:', user);
    
    // Create project using enhanced projects API
    const newProject = await projectsApi.createProject({
      name: 'Test Project with Auto Refresh',
      description: 'This will automatically refresh tokens if needed',
      is_private: true
    });
    console.log('✅ Project created with enhanced API:', newProject);
    
  } catch (error) {
    console.error('❌ Enhanced API request failed:', error);
  }
}

/**
 * Demo 3: Mixin Pattern for Gradual Migration
 */
export async function demoMixinPattern() {
  console.log('=== Demo 3: Mixin Pattern for Gradual Migration ===');
  
  // Enhance existing API without modifying its code
  const enhancedProjectsApi = ApiClientFactory.enhance(projectsApi);
  
  try {
    // Use original API methods (unchanged)
    const authToken = enhancedProjectsApi.getAuthToken();
    console.log('✅ Original method still works:', !!authToken);
    
    // Use enhanced methods (with automatic token refresh)
    const projects = await enhancedProjectsApi.enhanced.get('/api/v1/projects/');
    console.log('✅ Enhanced method with auto-refresh:', projects);
    
  } catch (error) {
    console.error('❌ Mixin pattern request failed:', error);
  }
}

/**
 * Demo 4: Legacy Bridge for Smooth Migration
 */
export async function demoLegacyBridge() {
  console.log('=== Demo 4: Legacy Bridge Pattern ===');
  
  const bridgedApi = ApiClientFactory.createLegacyBridge(projectsApi);
  
  try {
    // All original functionality preserved
    const extractedError = bridgedApi.extractErrorMessage({ detail: 'Test error' }, 'Default');
    console.log('✅ Original error extraction works:', extractedError);
    
    // Enhanced methods available
    const projects = await bridgedApi.enhanced.get('/api/v1/projects/');
    console.log('✅ Enhanced bridge method works:', projects);
    
    // Migration helper (shows warnings to encourage upgrade)
    const stats = await bridgedApi.migrateMethod('getUserStats', '/api/v1/auth/me/stats', null, 'GET');
    console.log('✅ Migration helper works:', stats);
    
  } catch (error) {
    console.error('❌ Legacy bridge request failed:', error);
  }
}

/**
 * Demo 5: Token Refresh Flow Simulation
 */
export async function demoTokenRefreshFlow() {
  console.log('=== Demo 5: Token Refresh Flow Simulation ===');
  
  try {
    console.log('📄 Current token exists:', !!authService.getAccessToken());
    console.log('🔄 Refresh token exists:', !!authService.getRefreshToken());
    
    // Simulate making a request that might fail with 401
    console.log('🚀 Making request that might trigger token refresh...');
    const user = await httpClient.get('/api/v1/auth/me');
    console.log('✅ Request successful (token was valid or refreshed):', !!user);
    
    // Show how manual refresh works
    console.log('🔄 Manually triggering token refresh...');
    const refreshSuccess = await authService.refreshAccessToken();
    console.log('✅ Manual refresh result:', refreshSuccess);
    
  } catch (error) {
    console.error('❌ Token refresh flow failed:', error);
  }
}

/**
 * Demo 6: Error Handling Preservation
 */
export async function demoErrorHandlingPreservation() {
  console.log('=== Demo 6: Error Handling Preservation ===');
  
  try {
    // Test that existing error extraction logic is preserved
    const testErrorData = {
      detail: {
        message: 'Custom error from backend'
      }
    };
    
    const extractedError = userApi.extractErrorMessage(testErrorData, 'Default message');
    console.log('✅ Error extraction preserved:', extractedError);
    
    // Test enhanced error handling
    const enhancedUserApi = ApiClientFactory.enhance(userApi);
    
    // This would use the same error extraction logic
    // but with automatic token refresh
    const user = await enhancedUserApi.enhanced.get('/api/v1/auth/me');
    console.log('✅ Enhanced error handling works:', !!user);
    
  } catch (error) {
    console.error('❌ Error handling test failed:', error);
    console.log('ℹ️  Error was properly extracted and thrown');
  }
}

/**
 * Demo 7: Configuration Options
 */
export async function demoConfigurationOptions() {
  console.log('=== Demo 7: Configuration Options ===');
  
  try {
    // Request without authentication
    const publicData = await httpClient.get('/api/v1/auth/health', { skipAuth: true });
    console.log('✅ Public request (no auth):', publicData);
    
    // Request without token refresh (for auth endpoints)
    const loginData = await httpClient.post('/api/v1/auth/login', {
      email: 'test@example.com',
      password: 'password'
    }, { skipAuth: true, skipRefresh: true });
    console.log('✅ Auth request (no refresh):', !!loginData);
    
    // Request with custom error handling
    const customExtractor = (data: any, defaultMessage: string) => {
      return `Custom: ${data?.detail || defaultMessage}`;
    };
    
    const customClient = httpClient.withErrorExtractor(customExtractor);
    const customResult = await customClient.get('/api/v1/auth/me');
    console.log('✅ Custom error extractor works:', !!customResult);
    
  } catch (error) {
    console.error('❌ Configuration options test failed:', error);
  }
}

/**
 * Run all demos
 */
export async function runAllDemos() {
  console.log('🚀 Starting Token Refresh Integration Demos...\n');
  
  const demos = [
    demoDirectHttpClient,
    demoEnhancedExistingApis,
    demoMixinPattern,
    demoLegacyBridge,
    demoTokenRefreshFlow,
    demoErrorHandlingPreservation,
    demoConfigurationOptions
  ];
  
  for (let i = 0; i < demos.length; i++) {
    try {
      await demos[i]();
      console.log(`✅ Demo ${i + 1} completed successfully\n`);
    } catch (error) {
      console.error(`❌ Demo ${i + 1} failed:`, error, '\n');
    }
  }
  
  console.log('🎉 All demos completed!');
}

/**
 * Integration Testing Helper
 */
export class TokenRefreshTester {
  static async testTokenExpiration() {
    console.log('🧪 Testing token expiration handling...');
    
    // This would simulate a 401 response
    try {
      const response = await httpClient.get('/api/v1/auth/verify');
      console.log('✅ Token is still valid:', response);
    } catch (error) {
      console.log('ℹ️  Token may be expired, refresh should trigger automatically');
    }
  }
  
  static async testRefreshTokenFlow() {
    console.log('🧪 Testing refresh token flow...');
    
    const hasRefreshToken = !!authService.getRefreshToken();
    console.log('📝 Has refresh token:', hasRefreshToken);
    
    if (hasRefreshToken) {
      const refreshResult = await authService.refreshAccessToken();
      console.log('🔄 Refresh result:', refreshResult);
    }
  }
  
  static async testApiCompatibility() {
    console.log('🧪 Testing API compatibility...');
    
    // Test that all existing API methods still work
    const apis = [userApi, projectsApi];
    
    for (const api of apis) {
      if (typeof api.getAuthToken === 'function') {
        const token = api.getAuthToken();
        console.log(`✅ ${api.constructor.name || 'API'} getAuthToken works:`, !!token);
      }
      
      if (typeof api.extractErrorMessage === 'function') {
        const error = api.extractErrorMessage({ detail: 'test' }, 'default');
        console.log(`✅ ${api.constructor.name || 'API'} extractErrorMessage works:`, error);
      }
    }
  }
}

export default {
  runAllDemos,
  demoDirectHttpClient,
  demoEnhancedExistingApis,
  demoMixinPattern,
  demoLegacyBridge,
  demoTokenRefreshFlow,
  demoErrorHandlingPreservation,
  demoConfigurationOptions,
  TokenRefreshTester
}; 