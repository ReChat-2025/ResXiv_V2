/**
 * Draft API Client
 * 
 * Handles all draft-related API calls including LaTeX projects, files, branches, 
 * and compilation functionality for the collaborative LaTeX editor.
 */

// Draft-related types based on backend API schemas
export interface LaTeXProjectCreate {
  template: 'article' | 'report' | 'book' | 'beamer';
  name: string;
}

export interface LaTeXProjectResponse {
  success: boolean;
  latex_project: {
    id: string;
    name: string;
    template: string;
    created_at: string;
    created_by: string;
  };
  branch?: {
    id: string;
    name: string;
    description: string;
  };
  files_created: string[];
  message: string;
}

export interface LaTeXFileStructure {
  success: boolean;
  files: LaTeXFile[];
  structure: FileTreeNode[];
  last_modified?: string;
  total_files: number;
}

export interface LaTeXFile {
  path: string;
  name: string;
  type: 'file' | 'directory';
  content?: string;
  size?: number;
  last_modified: string;
  is_editable: boolean;
}

export interface FileTreeNode {
  path: string;
  name: string;
  type: 'file' | 'directory';
  children?: FileTreeNode[];
  metadata?: {
    size?: number;
    last_modified: string;
    is_editable: boolean;
  };
}

export interface LaTeXFileContent {
  success: boolean;
  content: string;
  file_path: string;
  last_modified: string;
  size: number;
  is_editable: boolean;
}

export interface LaTeXFileUpdate {
  content: string;
  message?: string;
}

// LaTeX Template Types
export interface LaTeXTemplate {
  id: string;
  name: string;
  description?: string;
  category: 'article' | 'report' | 'book' | 'beamer' | 'custom';
  tags?: string[];
  preview_url?: string;
  files: TemplateFile[];
  is_custom: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface TemplateFile {
  name: string;
  path: string;
  content: string;
  is_main: boolean;
}

export interface LaTeXTemplateCreate {
  name: string;
  description?: string;
  category: 'article' | 'report' | 'book' | 'beamer' | 'custom';
  tags?: string[];
  files: TemplateFile[];
}

export interface LaTeXTemplatesResponse {
  templates: LaTeXTemplate[];
}

// File Management Types
export interface ProjectFile {
  id: string;
  filename: string;
  original_filename: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  uploaded_by: string;
  uploaded_at: string;
  folder?: string;
  description?: string;
  tags?: string[];
  is_public: boolean;
  download_count: number;
}

export interface ProjectFilesResponse {
  files: ProjectFile[];
  total: number;
  page: number;
  size: number;
}

export interface FileTreeResponse {
  tree: FileTreeStructure;
  total_files: number;
  total_size: number;
}

export interface FileTreeStructure {
  name: string;
  type: 'file' | 'folder';
  path: string;
  size?: number;
  children?: FileTreeStructure[];
  file_count?: number;
}

export interface StorageUsageResponse {
  total_size: number;
  file_count: number;
  by_type: Record<string, { size: number; count: number }>;
  by_folder: Record<string, { size: number; count: number }>;
  by_user: Record<string, { size: number; count: number }>;
  quota_used_percentage: number;
}

export interface BulkOperationResponse {
  success: boolean;
  processed: number;
  successful: number;
  failed: number;
  errors: string[];
  results: any[];
}

export interface BranchCreate {
  name: string;
  description?: string;
  source_branch_id?: string;
  is_protected?: boolean;
}

export interface BranchResponse {
  id: string;
  name: string;
  description?: string;
  project_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  is_protected: boolean;
  is_active: boolean;
  file_count: number;
  last_commit?: string;
  permissions?: {
    can_read: boolean;
    can_write: boolean;
    can_delete: boolean;
  };
}

export interface BranchListResponse {
  branches: BranchResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface CompilationRequest {
  main_file?: string;
  output_format?: 'pdf' | 'dvi' | 'ps';
  engine?: 'pdflatex' | 'xelatex' | 'lualatex' | 'latex';
}

export interface CompilationResponse {
  success: boolean;
  compilation_id: string;
  status: 'started' | 'running' | 'completed' | 'failed';
  estimated_time?: string;
  message: string;
}

export interface CompilationStatus {
  success: boolean;
  compilation: {
    id: string;
    status: 'started' | 'running' | 'completed' | 'failed';
    created_at: string;
    completed_at?: string;
    main_file: string;
    output_format: string;
    engine: string;
    logs?: string[];
    errors?: string[];
    warnings?: string[];
    output_files?: string[];
    pdf_url?: string;
    progress?: number;
  };
}

export interface CompilationHistoryResponse {
  compilations: CompilationStatus['compilation'][];
  total: number;
  page: number;
  size: number;
}

// Branch File Types
export interface BranchFileCreate {
  file_name: string;
  file_path?: string;
  file_type?: string;
  content?: string;
  encoding?: string;
}

export interface BranchFile {
  id: string;
  file_name: string;
  file_path: string;
  file_type: string;
  content?: string;
  file_size: number;
  encoding: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  last_modified_by?: string;
}

import { API_BASE_URL } from '@/lib/config/api-config';

// HTTP client with error handling
class DraftApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = API_BASE_URL;
  }

  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    const token = localStorage.getItem('accessToken') || sessionStorage.getItem('accessToken');
    return token;
  }

  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getAuthToken();
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
    }

    return response.json();
  }

  // ================================
  // LATEX TEMPLATE OPERATIONS
  // ================================

  /**
   * Get available LaTeX templates
   */
  async getLaTeXTemplates(
    category?: string,
    search?: string
  ): Promise<LaTeXTemplatesResponse> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (search) params.append('search', search);

    const endpoint = `/api/v1/latex/latex/templates?${params.toString()}`;
    return this.makeRequest<LaTeXTemplatesResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get specific LaTeX template details
   */
  async getLaTeXTemplate(templateId: string): Promise<{ success: boolean; template: LaTeXTemplate }> {
    const endpoint = `/api/v1/latex/latex/templates/${templateId}`;
    return this.makeRequest<{ success: boolean; template: LaTeXTemplate }>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Create custom LaTeX template
   */
  async createLaTeXTemplate(data: LaTeXTemplateCreate): Promise<{ success: boolean; template: LaTeXTemplate }> {
    const endpoint = `/api/v1/latex/latex/templates`;
    return this.makeRequest<{ success: boolean; template: LaTeXTemplate }>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Update custom LaTeX template
   */
  async updateLaTeXTemplate(
    templateId: string,
    data: Partial<LaTeXTemplateCreate>
  ): Promise<{ success: boolean; template: LaTeXTemplate }> {
    const endpoint = `/api/v1/latex/latex/templates/${templateId}`;
    return this.makeRequest<{ success: boolean; template: LaTeXTemplate }>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * Delete custom LaTeX template
   */
  async deleteLaTeXTemplate(templateId: string): Promise<{ success: boolean; message: string }> {
    const endpoint = `/api/v1/latex/latex/templates/${templateId}`;
    return this.makeRequest<{ success: boolean; message: string }>(endpoint, {
      method: 'DELETE',
    });
  }

  // ================================
  // LATEX PROJECT OPERATIONS
  // ================================

  /**
   * Create a new LaTeX project
   */
  async createLaTeXProject(projectId: string, data: LaTeXProjectCreate): Promise<LaTeXProjectResponse> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex/create?template=${data.template}&name=${encodeURIComponent(data.name)}`;
    return this.makeRequest<LaTeXProjectResponse>(endpoint, {
      method: 'POST',
    });
  }

  /**
   * Get list of LaTeX projects for a project
   */
  async getLaTeXProjects(projectId: string): Promise<{ success: boolean; latex_projects?: any[]; total_count?: number; error?: string }> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex`;
    return this.makeRequest<{ success: boolean; latex_projects?: any[]; total_count?: number; error?: string }>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Delete a LaTeX project
   */
  async deleteLaTeXProject(projectId: string, latexId: string): Promise<{ success: boolean; message: string }> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}`;
    return this.makeRequest<{ success: boolean; message: string }>(endpoint, {
      method: 'DELETE',
    });
  }

  // ================================
  // LATEX FILE OPERATIONS
  // ================================

  /**
   * Get file structure for a LaTeX project
   */
  async getLaTeXFiles(projectId: string, latexId: string): Promise<LaTeXFileStructure> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/files`;
    return this.makeRequest<LaTeXFileStructure>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get content of a specific file
   */
  async getLaTeXFileContent(projectId: string, latexId: string, filePath: string): Promise<LaTeXFileContent> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/files/${encodeURIComponent(filePath)}`;
    return this.makeRequest<LaTeXFileContent>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Update content of a specific file
   */
  async updateLaTeXFile(
    projectId: string, 
    latexId: string, 
    filePath: string, 
    data: LaTeXFileUpdate
  ): Promise<{ success: boolean; message: string }> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/files/${encodeURIComponent(filePath)}`;
    return this.makeRequest<{ success: boolean; message: string }>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * Create a new file using LaTeX files endpoint (PUT for file creation/update)
   */
  async createLaTeXFile(
    projectId: string, 
    latexId: string, 
    filePath: string, 
    content: string = ''
  ): Promise<{ success: boolean; message: string }> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/files/${encodeURIComponent(filePath)}`;
    
    // Use FormData as the backend expects Form parameters
    const formData = new FormData();
    formData.append('content', content);
    formData.append('commit_message', `Create ${filePath}`);
    
    return this.makeRequest<{ success: boolean; message: string }>(endpoint, {
      method: 'PUT',
      body: formData,
    });
  }

  /**
   * Delete a file
   */
  async deleteLaTeXFile(
    projectId: string, 
    latexId: string, 
    filePath: string,
    commitMessage: string = `Delete ${filePath}`
  ): Promise<{ success: boolean; message: string }> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/files/${encodeURIComponent(filePath)}`;
    
    // Use FormData for commit message
    const formData = new FormData();
    formData.append('commit_message', commitMessage);
    
    return this.makeRequest<{ success: boolean; message: string }>(endpoint, {
      method: 'DELETE',
      body: formData,
    });
  }

  /**
   * Upload a file to LaTeX project
   */
  async uploadLaTeXFile(
    projectId: string, 
    latexId: string, 
    file: File, 
    filePath?: string,
    overwrite: boolean = false
  ): Promise<{ success: boolean; message: string; file_path: string }> {
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const formData = new FormData();
    formData.append('file', file);
    if (filePath) {
      formData.append('file_path', filePath);
    }
    formData.append('overwrite', overwrite.toString());

    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/files/upload`;
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
    }

    return response.json();
  }

  /**
   * Get LaTeX project preview
   */
  async getLaTeXPreview(
    projectId: string,
    latexId: string,
    page: number = 1,
    scale: number = 1.0
  ): Promise<Blob> {
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('scale', scale.toString());

    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/preview?${params.toString()}`;
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
    }

    return response.blob();
  }

  // ================================
  // GENERAL FILE OPERATIONS
  // ================================

  /**
   * Upload file to project (general files)
   */
  async uploadProjectFile(
    projectId: string,
    file: File,
    folder?: string,
    description?: string,
    tags?: string[]
  ): Promise<{ success: boolean; file: ProjectFile; message: string }> {
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const formData = new FormData();
    formData.append('file', file);
    if (folder) formData.append('folder', folder);
    if (description) formData.append('description', description);
    if (tags) formData.append('tags', JSON.stringify(tags));

    const endpoint = `/api/v1/files/projects/${projectId}/files/upload`;
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
    }

    return response.json();
  }

  /**
   * List project files
   */
  async getProjectFiles(
    projectId: string,
    folder?: string,
    fileType?: string,
    search?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<ProjectFilesResponse> {
    const params = new URLSearchParams();
    if (folder) params.append('folder', folder);
    if (fileType) params.append('file_type', fileType);
    if (search) params.append('search', search);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    const endpoint = `/api/v1/files/projects/${projectId}/files?${params.toString()}`;
    return this.makeRequest<ProjectFilesResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get project file tree structure
   */
  async getProjectFileTree(projectId: string): Promise<FileTreeResponse> {
    const endpoint = `/api/v1/files/projects/${projectId}/files/tree`;
    return this.makeRequest<FileTreeResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Download file
   */
  async downloadFile(fileId: string): Promise<Blob> {
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const endpoint = `/api/v1/files/files/${fileId}/download`;
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
    }

    return response.blob();
  }

  /**
   * Delete file
   */
  async deleteFile(fileId: string): Promise<{ success: boolean; message: string }> {
    const endpoint = `/api/v1/files/files/${fileId}`;
    return this.makeRequest<{ success: boolean; message: string }>(endpoint, {
      method: 'DELETE',
    });
  }

  /**
   * Update file metadata
   */
  async updateFileMetadata(
    fileId: string,
    metadata: { description?: string; tags?: string[]; folder?: string }
  ): Promise<{ success: boolean; file: ProjectFile }> {
    const endpoint = `/api/v1/files/files/${fileId}/metadata`;
    return this.makeRequest<{ success: boolean; file: ProjectFile }>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(metadata),
    });
  }

  /**
   * Get storage usage
   */
  async getStorageUsage(projectId: string): Promise<StorageUsageResponse> {
    const endpoint = `/api/v1/files/projects/${projectId}/storage/usage`;
    return this.makeRequest<StorageUsageResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Cleanup project storage
   */
  async cleanupProjectStorage(
    projectId: string,
    dryRun: boolean = false
  ): Promise<{ success: boolean; cleaned_files: number; freed_space: number; errors: string[] }> {
    const endpoint = `/api/v1/files/projects/${projectId}/storage/cleanup?dry_run=${dryRun}`;
    return this.makeRequest<{ success: boolean; cleaned_files: number; freed_space: number; errors: string[] }>(endpoint, {
      method: 'POST',
    });
  }

  /**
   * Bulk delete files
   */
  async bulkDeleteFiles(projectId: string, fileIds: string[]): Promise<BulkOperationResponse> {
    const endpoint = `/api/v1/files/projects/${projectId}/files/bulk/delete`;
    return this.makeRequest<BulkOperationResponse>(endpoint, {
      method: 'POST',
      body: JSON.stringify(fileIds),
    });
  }

  /**
   * Bulk move files
   */
  async bulkMoveFiles(
    projectId: string,
    fileIds: string[],
    targetFolder: string | null
  ): Promise<BulkOperationResponse> {
    const endpoint = `/api/v1/files/projects/${projectId}/files/bulk/move`;
    return this.makeRequest<BulkOperationResponse>(endpoint, {
      method: 'POST',
      body: JSON.stringify({
        file_ids: fileIds,
        target_folder: targetFolder,
      }),
    });
  }

  // ================================
  // BRANCH OPERATIONS (FIXED ENDPOINTS)
  // ================================

  /**
   * Get branches for a project
   */
  async getBranches(
    projectId: string, 
    page: number = 1, 
    size: number = 20, 
    includePermissions: boolean = false
  ): Promise<BranchListResponse> {
    const endpoint = `/api/v1/projects/${projectId}/branches/?page=${page}&size=${size}&include_permissions=${includePermissions}`;
    return this.makeRequest<BranchListResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Create a new branch
   */
  async createBranch(projectId: string, data: BranchCreate): Promise<{ success: boolean; branch: BranchResponse }> {
    const endpoint = `/api/v1/projects/${projectId}/branches/`;
    return this.makeRequest<{ success: boolean; branch: BranchResponse }>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Merge branches (placeholder for actual merge logic)
   */
  async mergeBranch(
    projectId: string,
    sourceBranchId: string,
    targetBranchId: string,
    mergeMessage: string = 'Merge branch'
  ): Promise<{ success: boolean; message: string }> {
    // This would typically be a POST to a merge endpoint
    // For now, returning a placeholder since the exact merge endpoint isn't implemented
    console.log('Merge operation:', { projectId, sourceBranchId, targetBranchId, mergeMessage });
    return { success: true, message: 'Merge operation would be implemented here' };
  }

  /**
   * Delete a branch
   */
  async deleteBranch(
    projectId: string,
    branchId: string
  ): Promise<{ success: boolean; message: string }> {
    // This would typically be a DELETE to branches endpoint
    // For now, returning a placeholder since the exact delete endpoint isn't implemented
    console.log('Delete branch operation:', { projectId, branchId });
    return { success: true, message: 'Branch deletion would be implemented here' };
  }



  /**
   * Update branch permissions
   */
  async updateBranchPermissions(
    projectId: string,
    branchId: string,
    permissionUpdates: Array<{
      user_id: string;
      permission_level: 'read' | 'write' | 'admin';
    }>
  ): Promise<{ success: boolean; message: string }> {
    const endpoint = `/api/v1/projects/${projectId}/branches/${branchId}/permissions`;
    return this.makeRequest<{ success: boolean; message: string }>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(permissionUpdates),
    });
  }

  /**
   * Get branch status
   */
  async getBranchStatus(projectId: string, branchId: string): Promise<{
    success: boolean;
    status: {
      ahead: number;
      behind: number;
      conflicts: any[];
      last_sync: string;
    };
  }> {
    const endpoint = `/api/v1/projects/${projectId}/branches/${branchId}/status`;
    return this.makeRequest<{
      success: boolean;
      status: {
        ahead: number;
        behind: number;
        conflicts: any[];
        last_sync: string;
      };
    }>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Compare branches
   */
  async compareBranches(
    projectId: string,
    sourceBranch: string,
    destinationBranch: string
  ): Promise<{
    success: boolean;
    comparison: {
      ahead: number;
      behind: number;
      changes: any[];
      conflicts: any[];
    };
  }> {
    const endpoint = `/api/v1/projects/${projectId}/branches/compare/${sourceBranch}/${destinationBranch}`;
    return this.makeRequest<{
      success: boolean;
      comparison: {
        ahead: number;
        behind: number;
        changes: any[];
        conflicts: any[];
      };
    }>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get branch files
   */
  async getBranchFiles(
    projectId: string,
    branchId: string,
    path?: string
  ): Promise<{
    success: boolean;
    files: Array<{
      id: string | null;
      file_name: string;
      file_path: string;
      file_type: string;
      file_size?: number;
      updated_at: string;
      created_by: any;
      last_modified_by: any;
      has_active_session: boolean;
    }>;
    total_count: number;
    branch_id: string;
    branch_name: string;
  }> {
    const params = new URLSearchParams();
    if (path) params.append('path', path);

    const endpoint = `/api/v1/projects/${projectId}/branches/${branchId}/files/?${params.toString()}`;
    return this.makeRequest<{
      success: boolean;
      files: Array<{
        id: string | null;
        file_name: string;
        file_path: string;
        file_type: string;
        file_size?: number;
        updated_at: string;
        created_by: any;
        last_modified_by: any;
        has_active_session: boolean;
      }>;
      total_count: number;
      branch_id: string;
      branch_name: string;
    }>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get branch commits
   */
  async getBranchCommits(
    projectId: string,
    branchName: string,
    page: number = 1,
    size: number = 20
  ): Promise<{
    success: boolean;
    commits: Array<{
      id: string;
      message: string;
      author: string;
      timestamp: string;
      changes: any[];
    }>;
    total: number;
    page: number;
    size: number;
  }> {
    const endpoint = `/api/v1/projects/${projectId}/branches/${branchName}/commits?page=${page}&size=${size}`;
    return this.makeRequest<{
      success: boolean;
      commits: Array<{
        id: string;
        message: string;
        author: string;
        timestamp: string;
        changes: any[];
      }>;
      total: number;
      page: number;
      size: number;
    }>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Create file in branch
   */
  async createBranchFile(
    projectId: string,
    branchId: string,
    fileData: BranchFileCreate
  ): Promise<{ success: boolean; file: BranchFile; message: string }> {
    const endpoint = `/api/v1/projects/${projectId}/branches/${branchId}/files/`;
    return this.makeRequest<{ success: boolean; file: BranchFile; message: string }>(endpoint, {
      method: 'POST',
      body: JSON.stringify(fileData),
    });
  }

  // ================================
  // COMPILATION OPERATIONS
  // ================================

  /**
   * Compile LaTeX project
   */
  async compileLaTeX(
    projectId: string, 
    latexId: string, 
    data: CompilationRequest = {}
  ): Promise<CompilationResponse> {
    const params = new URLSearchParams();
    if (data.main_file) params.append('main_file', data.main_file);
    if (data.output_format) params.append('output_format', data.output_format);
    if (data.engine) params.append('engine', data.engine);

    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/compile?${params.toString()}`;
    return this.makeRequest<CompilationResponse>(endpoint, {
      method: 'POST',
    });
  }

  /**
   * Get compilation status
   */
  async getCompilationStatus(
    projectId: string, 
    latexId: string, 
    compilationId: string
  ): Promise<CompilationStatus> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/compile/${compilationId}/status`;
    return this.makeRequest<CompilationStatus>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get compilation history
   */
  async getCompilationHistory(
    projectId: string,
    latexId: string,
    limit: number = 10
  ): Promise<CompilationHistoryResponse> {
    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/compile/history?limit=${limit}`;
    return this.makeRequest<CompilationHistoryResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Download compiled PDF
   */
  async downloadCompiledPDF(
    projectId: string, 
    latexId: string, 
    compilationId: string
  ): Promise<Blob> {
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const endpoint = `/api/v1/latex/projects/${projectId}/latex/${latexId}/compile/${compilationId}/download`;
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
    }

    return response.blob();
  }

  // ================================
  // HEALTH CHECK
  // ================================

  /**
   * Files system health check
   */
  async filesHealthCheck(): Promise<{ success: boolean; status: any }> {
    const endpoint = `/api/v1/files/files/health`;
    return this.makeRequest<{ success: boolean; status: any }>(endpoint, {
      method: 'GET',
    });
  }
}

// Singleton instance
export const draftApi = new DraftApiClient(); 