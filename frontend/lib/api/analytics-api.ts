/**
 * Analytics API
 * 
 * Handles all analytics-related API calls including project analytics,
 * collaboration metrics, and insights generation.
 */

// Analytics-related types based on backend API schemas
export interface ProjectAnalyticsParams {
  project_id: string;
  date_from?: string; // YYYY-MM-DD format
  date_to?: string; // YYYY-MM-DD format
}

export interface ProjectAnalyticsResponse {
  project_id: string;
  total_papers: number;
  total_collaborators: number;
  activity_timeline: Array<{
    date: string;
    papers_added: number;
    conversations: number;
    uploads: number;
  }>;
  top_keywords: Array<{
    keyword: string;
    frequency: number;
  }>;
  collaboration_network: Array<{
    user_id: string;
    user_name: string;
    interactions: number;
    papers_contributed: number;
  }>;
  paper_categories: Array<{
    category: string;
    count: number;
  }>;
}

export interface CollaborationAnalyticsResponse {
  project_id: string;
  total_conversations: number;
  active_collaborators: number;
  collaboration_score: number;
  interaction_patterns: Array<{
    user_id: string;
    message_count: number;
    last_activity: string;
  }>;
}

// Graph analytics types
export interface GraphNode {
  id: string;
  title: string;
  authors: string[];
  cluster_id?: number;
  x?: number;
  y?: number;
  size?: number;
  color?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  similarity: number;
}

export interface GraphAnalyticsResponse {
  success: boolean;
  project_id: string;
  basic_metrics: {
    node_count: number;
    edge_count: number;
    density: number;
    clustering_coefficient: number;
  };
  topology_analysis: {
    centrality_measures: Record<string, number>;
    community_structure: Record<string, any>;
    graph_diameter: number;
    average_path_length: number;
  };
  clustering_summary: Record<string, any>;
  recommendations: string[];
}

export interface GraphVisualizationResponse {
  success: boolean;
  project_id: string;
  layout: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  config: {
    node_size_range: [number, number];
    edge_width_range: [number, number];
    color_scheme: string;
    layout_algorithm: string;
  };
  legends: {
    clusters: Record<string, string>;
    node_sizes: string;
    edge_widths: string;
  };
}

export interface GraphClustersResponse {
  success: boolean;
  project_id: string;
  algorithm: string;
  clusters: Array<{
    cluster_id: number;
    paper_ids: string[];
    centroid_paper: string;
    cluster_size: number;
    avg_similarity: number;
  }>;
  quality_metrics: {
    silhouette_score: number;
    inertia: number;
    n_clusters: number;
  };
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';

class AnalyticsApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = API_BASE_URL;
  }

  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    // Align with other API clients that store the JWT under 'accessToken'
    // Fallback to 'authToken' for backward compatibility
    return (
      localStorage.getItem('accessToken') ||
      localStorage.getItem('authToken')
    );
  }

  private extractErrorMessage(data: any, defaultMessage: string): string {
    if (data && typeof data === 'object') {
      // Handle validation errors
      if (data.detail && Array.isArray(data.detail)) {
        return data.detail.map((error: any) => {
          if (error.msg) return error.msg;
          if (error.message) return error.message;
          return JSON.stringify(error);
        }).join(', ');
      }
      
      // Handle other error formats
      if (data.message) return data.message;
      if (data.error) return data.error;
      if (data.detail && typeof data.detail === 'string') return data.detail;
      
      // Try to extract any string value from error object
      for (const key of ['errors', 'error_description', 'description']) {
        if (data[key] && typeof data[key] === 'string') {
          return data[key];
        }
      }
    }
    
    return defaultMessage;
  }

  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
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

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Analytics API JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Analytics API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Analytics API error (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  }

  /**
   * Get project analytics data
   */
  async getProjectAnalytics(params: ProjectAnalyticsParams): Promise<ProjectAnalyticsResponse> {
    const searchParams = new URLSearchParams();
    
    if (params.date_from) searchParams.append('date_from', params.date_from);
    if (params.date_to) searchParams.append('date_to', params.date_to);

    const endpoint = `/api/v1/analytics/project/${params.project_id}/analytics?${searchParams.toString()}`;
    return this.makeRequest<ProjectAnalyticsResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get collaboration analytics for a project
   */
  async getCollaborationAnalytics(project_id: string): Promise<CollaborationAnalyticsResponse> {
    const endpoint = `/api/v1/analytics/project/${project_id}/collaboration`;
    return this.makeRequest<CollaborationAnalyticsResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get graph analytics for a project
   */
  async getGraphAnalytics(project_id: string): Promise<GraphAnalyticsResponse> {
    const endpoint = `/api/v1/graphs/projects/${project_id}/graph/analytics`;
    return this.makeRequest<GraphAnalyticsResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get graph visualization data for a project
   */
  async getGraphVisualization(
    project_id: string, 
    layout: string = 'force_directed',
    include_embeddings: boolean = false
  ): Promise<GraphVisualizationResponse> {
    const searchParams = new URLSearchParams();
    searchParams.append('layout', layout);
    searchParams.append('include_embeddings', include_embeddings.toString());
    
    const endpoint = `/api/v1/graphs/projects/${project_id}/graph/visualization?${searchParams.toString()}`;
    return this.makeRequest<GraphVisualizationResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Get graph clusters for a project
   */
  async getGraphClusters(
    project_id: string,
    algorithm: string = 'best'
  ): Promise<GraphClustersResponse> {
    const searchParams = new URLSearchParams();
    searchParams.append('algorithm', algorithm);
    
    const endpoint = `/api/v1/graphs/projects/${project_id}/graph/clusters?${searchParams.toString()}`;
    return this.makeRequest<GraphClustersResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Regenerate graph with new papers (forced refresh)
   */
  async regenerateGraph(project_id: string): Promise<{ success: boolean; message: string }> {
    const endpoint = `/api/v1/graphs/projects/${project_id}/graph/regenerate`;
    return this.makeRequest<{ success: boolean; message: string }>(endpoint, {
      method: 'PUT',
    });
  }
}

export const analyticsApi = new AnalyticsApiClient();
export default analyticsApi; 