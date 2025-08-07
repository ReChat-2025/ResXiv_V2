/**
 * Journals API
 * 
 * Handles all journal-related API calls including CRUD operations,
 * collaborators, versions, and journal metadata for projects.
 */

// Journal-related types based on backend API schemas
export interface JournalCreate {
  title: string;
  content?: string;
  is_public?: boolean;
  status?: 'draft' | 'published' | 'archived';
  metadata?: any;
  tags?: string[] | null;
}

export interface JournalUpdate {
  title?: string | null;
  content?: string | null;
  description?: string | null;
  is_public?: boolean | null;
  status?: 'draft' | 'published' | 'archived' | null;
  tags?: string[] | null;
}

export interface JournalResponse {
  id: string;
  title: string;
  content: string;
  is_public: boolean;
  status: string;
  metadata?: any;
  project_id?: string; // Made optional to handle backend inconsistency
  created_by?: string; // Made optional to handle backend inconsistency
  version?: number; // Made optional to handle backend inconsistency
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  creator_name?: string | null;
  project_name?: string | null;
  collaborator_count?: number; // Made optional for safety
  version_count?: number; // Made optional for safety
  can_edit?: boolean; // Made optional for safety
  can_admin?: boolean; // Made optional for safety
  tags?: string[]; // Made optional for safety
}

export interface JournalCollaborator {
  id: string;
  user: {
    id: string;
    name: string;
    email: string;
  };
  permission: 'read' | 'write' | 'admin';
  added_at: string;
  added_by: string;
}

export interface JournalCollaboratorAdd {
  user_id?: string;
  email?: string;
  permission: 'read' | 'write' | 'admin';
}

export interface JournalVersion {
  version: number;
  title: string;
  content: string | null;
  created_at: string;
  created_by: string;
  changes_summary: string | null;
  word_count: number;
}

export interface JournalsQueryParams {
  page?: number;
  per_page?: number;
  query?: string;
  journal_status?: string;
  is_public?: boolean;
  created_by?: string;
  tags?: string;
}

// Backend response format (actual API response)
interface JournalListBackendResponse {
  journals: JournalResponse[];
  total_count: number;
  page_offset: number;
  page_size: number;
}

// Frontend expected format (for component compatibility)
export interface JournalListResponse {
  journals: JournalResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export const journalsApi = {
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
      // Handle authentication errors specifically
      if (data.error === 'authentication_failed' || data.message?.includes('authentication')) {
        return 'Authentication failed. Please sign in again.';
      }
      
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
   * Get project journals with optional filtering and pagination
   */
  async getJournals(projectId: string, params: JournalsQueryParams = {}): Promise<JournalListResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    

    
    if (!projectId || projectId.trim() === '') {
      throw new Error('Project ID is required');
    }
    
    // Validate UUID format
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(projectId)) {
      throw new Error('Invalid project ID format. Project ID must be a valid UUID.');
    }
    
    if (!token) {
      throw new Error('Authentication required. Please sign in again.');
    }

    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.per_page) searchParams.set('per_page', params.per_page.toString());
    if (params.query) searchParams.set('query', params.query);
    if (params.journal_status) searchParams.set('journal_status', params.journal_status);
    if (params.is_public !== undefined) searchParams.set('is_public', params.is_public.toString());
    if (params.created_by) searchParams.set('created_by', params.created_by);
    if (params.tags) searchParams.set('tags', params.tags);

    const url = `${API_BASE_URL}/api/v1/journals/projects/${projectId}/journals?${searchParams.toString()}`;

    const response = await fetch(url, {
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
      console.error('Get journals JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get journals API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Request URL:', url);
      console.error('Token present:', !!token);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      // Handle specific error cases
      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }
      
      if (response.status === 404) {
        throw new Error('Project not found or you do not have access to it.');
      }
      
      if (response.status === 403) {
        throw new Error('Access denied. You do not have permission to view journals for this project.');
      }
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to list journals (${response.status})`
      );
      
      throw new Error(errorMessage);
    }

    // Transform backend response to frontend expected format
    console.log('Raw backend response:', JSON.stringify(data, null, 2));
    
    const backendResponse = data as any as JournalListBackendResponse;
    
    // Normalize each journal in the list to handle missing fields
    const normalizedJournals = (backendResponse.journals || []).map((journal: any): JournalResponse => ({
      ...journal,
      project_id: journal.project_id || 'unknown',
      created_by: journal.created_by || 'unknown',
      version: journal.version || 1,
      collaborator_count: journal.collaborator_count || 0,
      version_count: journal.version_count || 1,
      can_edit: journal.can_edit !== undefined ? journal.can_edit : true,
      can_admin: journal.can_admin !== undefined ? journal.can_admin : false,
      tags: journal.tags || []
    }));
    
    const transformedResponse: JournalListResponse = {
      journals: normalizedJournals,
      total: backendResponse.total_count || 0,
      page: (backendResponse.page_offset || 0) + 1, // Convert 0-based offset to 1-based page
      per_page: backendResponse.page_size || 20,
      total_pages: Math.ceil((backendResponse.total_count || 0) / (backendResponse.page_size || 20))
    };
    
    console.log('Transformed response:', JSON.stringify(transformedResponse, null, 2));
    
    return transformedResponse;
  },

  /**
   * Create a new journal
   */
  async createJournal(projectId: string, journalData: JournalCreate): Promise<JournalResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required. Please sign in again.');
    }

    if (!projectId || projectId.trim() === '') {
      throw new Error('Project ID is required');
    }

    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(projectId)) {
      throw new Error('Invalid project ID format. Project ID must be a valid UUID.');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/projects/${projectId}/journals`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(journalData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Create journal JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Create journal API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Request URL:', `${API_BASE_URL}/api/v1/journals/projects/${projectId}/journals`);
      console.error('Request payload:', JSON.stringify(journalData, null, 2));
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      // Handle specific error cases
      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }
      
      if (response.status === 403) {
        throw new Error('Access denied. You do not have permission to create journals in this project.');
      }
      
      if (response.status === 404) {
        throw new Error('Project not found or you do not have access to it.');
      }
      
      if (response.status === 422) {
        throw new Error('Invalid journal data. Please check all required fields.');
      }
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to create journal (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    console.log('Create journal successful:', JSON.stringify(data, null, 2));
    
    // Transform and normalize the response to handle missing fields
    const normalizedResponse: JournalResponse = {
      ...data,
      project_id: data.project_id || projectId, // Use the projectId from the request if missing
      created_by: data.created_by || 'unknown', // Provide fallback
      version: data.version || 1, // Default to version 1
      collaborator_count: data.collaborator_count || 0,
      version_count: data.version_count || 1,
      can_edit: data.can_edit !== undefined ? data.can_edit : true,
      can_admin: data.can_admin !== undefined ? data.can_admin : false,
      tags: data.tags || []
    };
    
    return normalizedResponse;
  },

  /**
   * Get a specific journal by ID
   */
  async getJournal(journalId: string): Promise<JournalResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/journals/${journalId}`, {
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
      console.error('Get journal JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get journal API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch journal (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    console.log('Get journal successful:', JSON.stringify(data, null, 2));
    
    // Transform and normalize the response to handle missing fields
    const normalizedResponse: JournalResponse = {
      ...data,
      project_id: data.project_id || 'unknown',
      created_by: data.created_by || 'unknown',
      version: data.version || 1,
      collaborator_count: data.collaborator_count || 0,
      version_count: data.version_count || 1,
      can_edit: data.can_edit !== undefined ? data.can_edit : true,
      can_admin: data.can_admin !== undefined ? data.can_admin : false,
      tags: data.tags || []
    };
    
    return normalizedResponse;
  },

  /**
   * Update a journal
   */
  async updateJournal(journalId: string, journalData: JournalUpdate): Promise<JournalResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/journals/${journalId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(journalData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Update journal JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Update journal API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to update journal (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Delete a journal
   */
  async deleteJournal(journalId: string): Promise<void> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/journals/${journalId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      let data: any = null;
      try {
        data = await response.json();
      } catch (error) {
        // Response might not have JSON body for delete
      }

      console.error('Delete journal API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to delete journal (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }
  },

  /**
   * Get journal collaborators
   */
  async getJournalCollaborators(journalId: string): Promise<JournalCollaborator[]> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/journals/${journalId}/collaborators`, {
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
      console.error('Get journal collaborators JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get journal collaborators API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch journal collaborators (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Add a journal collaborator
   */
  async addJournalCollaborator(journalId: string, collaboratorData: JournalCollaboratorAdd): Promise<JournalCollaborator> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/journals/${journalId}/collaborators`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(collaboratorData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Add journal collaborator JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Add journal collaborator API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to add journal collaborator (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Remove a journal collaborator
   */
  async removeJournalCollaborator(journalId: string, collaboratorId: string): Promise<void> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/journals/${journalId}/collaborators/${collaboratorId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      let data: any = null;
      try {
        data = await response.json();
      } catch (error) {
        // Response might not have JSON body for delete
      }

      console.error('Remove journal collaborator API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to remove journal collaborator (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }
  },

  /**
   * Get journal versions
   */
  async getJournalVersions(journalId: string): Promise<JournalVersion[]> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/journals/${journalId}/versions`, {
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
      console.error('Get journal versions JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get journal versions API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch journal versions (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Get a specific journal version
   */
  async getJournalVersion(journalId: string, version: number): Promise<JournalVersion> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/journals/${journalId}/versions/${version}`, {
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
      console.error('Get journal version JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get journal version API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch journal version (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Get public journals
   */
  async getPublicJournals(params: JournalsQueryParams = {}): Promise<JournalListResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();

    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.per_page) searchParams.set('per_page', params.per_page.toString());
    if (params.query) searchParams.set('query', params.query);
    if (params.tags) searchParams.set('tags', params.tags);

    const url = `${API_BASE_URL}/api/v1/journals/journals/public?${searchParams.toString()}`;

    const headers: HeadersInit = {
      'Accept': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: 'GET',
      headers,
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Get public journals JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get public journals API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch public journals (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Bulk operations on journals
   */
  async bulkJournalOperation(operation: 'delete' | 'update', journalIds: string[], data?: any): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/journals/journals/bulk`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        operation,
        journal_ids: journalIds,
        data,
      }),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch (error) {
      console.error('Bulk journal operation JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Bulk journal operation API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(responseData, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        responseData, 
        `Failed to perform bulk journal operation (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return responseData;
  },

  /**
   * Get a specific journal by ID within a project context
   * This ensures the journal belongs to the specified project
   */
  async getProjectJournal(projectId: string, journalId: string): Promise<JournalResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    console.log('Fetching journal within project context:', { projectId, journalId });

    // First, get all journals for the project to verify this journal belongs to it
    try {
      const projectJournals = await this.getJournals(projectId);
      const journal = projectJournals.journals.find(j => j.id === journalId);
      
      if (!journal) {
        throw new Error('Journal not found in this project or access denied');
      }
      
      console.log('Journal found in project, fetching full details...');
      
      // Now get the full journal details
      return await this.getJournal(journalId);
    } catch (error) {
      console.error('Error in getProjectJournal:', error);
      
      if (error instanceof Error) {
        if (error.message.includes('Journal not found in this project')) {
          throw error; // Re-throw our custom error
        }
        // For other errors, provide more context
        throw new Error(`Failed to access journal in project: ${error.message}`);
      }
      
      throw new Error('Failed to access journal in project');
    }
  },
}; 