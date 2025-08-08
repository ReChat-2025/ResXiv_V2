/**
 * API Configuration
 * 
 * Centralized configuration for all API clients
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  // Core endpoints
  PROJECTS: '/api/v1/projects',
  PAPERS: '/api/v1/projects',
  ANALYTICS: '/api/v1/analytics',
  AGENTIC: '/api/v1/agentic',
  
  // Auth
  AUTH: '/api/v1/auth',
  
  // Files
  FILES: '/api/v1/files',
  
  // Journals
  JOURNALS: '/api/v1/journals',
  
  // Tasks
  TASKS: '/api/v1/projects',
  
  // Conversations
  CONVERSATIONS: '/api/v1/conversations',
} as const; 

export default {
  API_BASE_URL,
  API_ENDPOINTS,
}; 