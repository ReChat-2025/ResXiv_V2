/**
 * API Configuration
 * Centralized configuration for all API endpoints
 */

// Simple fix: Sanitize the environment variable to remove trailing /api
const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';


// Use the sanitized URL
export const API_BASE_URL = rawApiUrl;

// Export for legacy compatibility
export const getApiBaseUrl = () => API_BASE_URL;

// API endpoints configuration
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    REFRESH: '/api/v1/auth/refresh', 
    REGISTER: '/api/v1/auth/register',
    VERIFY_EMAIL: '/api/v1/auth/verify-email',
    RESEND_VERIFICATION: '/api/v1/auth/resend-verification',
    FORGOT_PASSWORD: '/api/v1/auth/forgot-password',
    RESET_PASSWORD: '/api/v1/auth/reset-password',
    CHANGE_PASSWORD: '/api/v1/auth/me/change-password',
    VERIFY_TOKEN: '/api/v1/auth/verify',
    LOGOUT: '/api/v1/auth/logout',
  },
  PROJECTS: {
    BASE: '/api/v1/projects',
    MEMBERS: (projectId: string) => `/api/v1/projects/${projectId}/members`,
  },
  HEALTH: '/api/v1/health',
} as const; 