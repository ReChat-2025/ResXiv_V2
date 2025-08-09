/**
 * Papers API
 * 
 * Handles all paper-related API calls for projects including CRUD operations,
 * file uploads, search, and paper management.
 */

// Backend Response Types (matching the actual API schema)
export interface PaperResponse {
  id: string;
  title: string;
  date_added: string;
  last_modified: string;
  pdf_path?: string | null;
  bib_path?: string | null;
  xml_path?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  checksum?: string | null;
  private_uploaded: boolean;
  authors: string[];
  keywords: string[];
  arxiv_id?: string | null;
  doi?: string | null;
  abstract?: string | null;
  safe_title?: string | null;
  created_at: string;
  updated_at: string;
  diagnostics?: any | null;
}

export interface PapersListResponse {
  papers: PaperResponse[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export interface SearchPapersResponse {
  papers: PaperResponse[];
  total: number;
  query: string;
  search_type: string;
}

export interface PaperReference {
  title: string;
  authors: string[];
  year: string;
  journal: string;
  booktitle: string;
  doi: string;
  eprint: string;
  entry_type: string;
  citation_key: string;
}

export interface PaperReferencesResponse {
  success: boolean;
  references: PaperReference[];
  count: number;
  project_id?: string;
  paper_id?: string;
}

// Request Types
export interface GetPapersParams {
  project_id: string;
  page?: number;
  size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: string;
}

export interface SearchPapersParams {
  project_id: string;
  query?: string;
  limit?: number;
  search_type?: 'semantic' | 'keyword' | 'hybrid';
}

export interface UploadPaperParams {
  project_id: string;
  file: File;
  title?: string;
  process_with_grobid?: boolean;
  run_diagnostics?: boolean;
  private_uploaded?: boolean;
}

export interface UpdatePaperParams {
  project_id: string;
  paper_id: string;
  title?: string;
  authors?: string[];
  keywords?: string[];
  abstract?: string;
}

import { API_BASE_URL } from '@/lib/config/api-config';

// HTTP client with error handling
class PapersApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = API_BASE_URL;
  }

  /**
   * Get authentication token
   */
  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('accessToken') || sessionStorage.getItem('accessToken');
  }

  /**
   * Extract error message from API response
   */
  private extractErrorMessage(data: any, defaultMessage: string): string {
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
   * Make authenticated API request
   */
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
        ...options.headers,
      },
    });

    // Get response text first to handle both JSON and non-JSON responses
    const responseText = await response.text();

    let data: any;
    try {
      data = JSON.parse(responseText);
    } catch (error) {
      console.error('Papers API JSON parse error:', error);
      console.error('Response status:', response.status, response.statusText);
      console.error('Response URL:', response.url);
      console.error('Response body (first 500 chars):', responseText.substring(0, 500));
      
      throw new Error(`Server returned invalid response (${response.status}). Expected JSON but got: ${responseText.substring(0, 100)}...`);
    }

    if (!response.ok) {
      // Special-case 413 (Payload Too Large)
      if (response.status === 413) {
        throw new Error('Upload failed: file is too large for the server limit. Please try a smaller PDF or ask the admin to increase the upload size.');
      }
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Papers API error (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  }

  /**
   * Get papers for a project
   */
  async getPapers(params: GetPapersParams): Promise<PapersListResponse> {
    const searchParams = new URLSearchParams();
    
    if (params.page) searchParams.append('page', params.page.toString());
    if (params.size) searchParams.append('size', params.size.toString());
    if (params.search) searchParams.append('search', params.search);
    if (params.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params.sort_order) searchParams.append('sort_order', params.sort_order);

    const endpoint = `/api/v1/projects/${params.project_id}/papers?${searchParams.toString()}`;
    return this.makeRequest<PapersListResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get a specific paper
   */
  async getPaper(project_id: string, paper_id: string): Promise<PaperResponse> {
    const endpoint = `/api/v1/projects/${project_id}/papers/${paper_id}`;
    return this.makeRequest<PaperResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Search papers within a project
   */
  async searchPapers(params: SearchPapersParams): Promise<SearchPapersResponse> {
    const searchParams = new URLSearchParams();
    
    if (params.query) searchParams.append('query', params.query);
    if (params.limit) searchParams.append('limit', params.limit.toString());
    if (params.search_type) searchParams.append('search_type', params.search_type);

    const endpoint = `/api/v1/projects/${params.project_id}/papers/search?${searchParams.toString()}`;
    return this.makeRequest<SearchPapersResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Upload a paper file
   */
  async uploadPaper(params: UploadPaperParams): Promise<PaperResponse> {
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    console.log('Uploading paper to project:', params.project_id);
    console.log('File details:', { name: params.file.name, size: params.file.size, type: params.file.type });

    const formData = new FormData();
    formData.append('file', params.file);
    
    if (params.title) formData.append('title', params.title);
    if (params.process_with_grobid !== undefined) {
      formData.append('process_with_grobid', params.process_with_grobid.toString());
    }
    if (params.run_diagnostics !== undefined) {
      formData.append('run_diagnostics', params.run_diagnostics.toString());
    }
    if (params.private_uploaded !== undefined) {
      formData.append('private_uploaded', params.private_uploaded.toString());
    }

    const endpoint = `/api/v1/projects/${params.project_id}/upload`;
    console.log('Upload endpoint:', `${this.baseURL}${endpoint}`);
    
    return this.makeRequest<PaperResponse>(endpoint, {
      method: 'POST',
      body: formData,
      headers: {
        'Authorization': `Bearer ${token}`,
        // Don't set Content-Type for FormData - browser will set it with boundary
      },
    });
  }

  /**
   * Update a paper
   */
  async updatePaper(params: UpdatePaperParams): Promise<PaperResponse> {
    const endpoint = `/api/v1/projects/${params.project_id}/papers/${params.paper_id}`;
    
    const updateData: any = {};
    if (params.title !== undefined) updateData.title = params.title;
    if (params.authors !== undefined) updateData.authors = params.authors;
    if (params.keywords !== undefined) updateData.keywords = params.keywords;
    if (params.abstract !== undefined) updateData.abstract = params.abstract;

    return this.makeRequest<PaperResponse>(endpoint, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updateData),
    });
  }

  /**
   * Delete a paper
   */
  async deletePaper(project_id: string, paper_id: string): Promise<void> {
    const endpoint = `/api/v1/projects/${project_id}/papers/${paper_id}`;
    await this.makeRequest<void>(endpoint, {
      method: 'DELETE',
    });
  }

  /**
   * Download a paper
   */
  async downloadPaper(project_id: string, paper_id: string): Promise<Blob> {
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const endpoint = `/api/v1/projects/${project_id}/papers/${paper_id}/download`;
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to download paper: ${response.statusText}`);
    }

    return response.blob();
  }

  /**
   * Get paper diagnostics
   */
  async getPaperDiagnostics(project_id: string, paper_id: string): Promise<any> {
    const endpoint = `/api/v1/projects/${project_id}/papers/${paper_id}/diagnostics`;
    return this.makeRequest<any>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get paper references (parsed from BibTeX)
   */
  async getPaperReferences(project_id: string, paper_id: string): Promise<PaperReferencesResponse> {
    const endpoint = `/api/v1/projects/${project_id}/papers/${paper_id}/references`;
    return this.makeRequest<PaperReferencesResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get papers analytics for a project
   */
  async getPapersAnalytics(project_id: string): Promise<any> {
    const endpoint = `/api/v1/projects/${project_id}/papers/analytics`;
    return this.makeRequest<any>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Import paper from URL or DOI
   */
  async importPaper(source: string): Promise<any> {
    const endpoint = `/api/v1/papers/import`;
    return this.makeRequest<any>(endpoint, {
      method: 'POST',
      body: JSON.stringify({ source }),
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
}

// Export singleton instance
export const papersApi = new PapersApiClient();

// Legacy export for backward compatibility
export default papersApi; 