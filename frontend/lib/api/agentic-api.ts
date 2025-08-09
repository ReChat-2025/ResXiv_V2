/**
 * Agentic AI API
 * 
 * Handles ResXiv AI chat functionality with project context
 */

export interface AgenticMessage {
  message: string;
  context?: Record<string, any>;
  conversation_id?: string;
  preferences?: Record<string, string>;
}

export interface AgenticResponse {
  success: boolean;
  response: string;
  agent?: string | null;
  intent?: string | null;
  tool_calls: number;
  conversation_id: string;
  processing_time: number;
  timestamp: string;
  metadata?: Record<string, any> | null;
}

export interface ConversationHistoryMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
  metadata?: Record<string, any>;
}

// Backend message format (what we actually receive)
interface BackendMessage {
  message_id: string;
  content: string;
  sender_type: 'user' | 'agent';
  timestamp: string;
  metadata?: Record<string, any>;
}

// Transform backend message format to frontend format
const transformBackendMessage = (backendMsg: any): ConversationHistoryMessage => {
  // Primary role detection from sender_type
  let role: 'user' | 'assistant' = backendMsg.sender_type === 'agent' ? 'assistant' : 'user';
  
  // Get content for role detection
  const content = backendMsg.content || backendMsg.message || '';
  
  // Override for obvious AI greetings/responses (even when backend says user)
  if (backendMsg.sender_type === 'user' && (
    content.includes('How can I assist you today') ||
    content.includes('Hello! How can I') ||
    content.includes("I'm here to help") ||
    content.includes("Hey there! It sounds like") ||
    (content.includes('Hey there!') && content.length > 100)
  )) {
    role = 'assistant';
  }
  
  // Fallback: Content-based role detection for edge cases
  if (!backendMsg.sender_type) {
    // If sender_type is missing, try to detect from content patterns
    if (content.startsWith('###') || 
        content.includes('Based on') || 
        content.includes('I found') || 
        content.includes('Here are') || 
        content.includes('I can help') ||
        content.includes('How can I assist') ||
        content.includes('Hello! How can I') ||
        content.includes("I'm here to help") ||
        content.includes("Hey there!") ||
        content.includes("It sounds like") ||
        content.length > 200) {
      role = 'assistant';
    } else {
      role = 'user';
    }
  }
  
  const transformed = {
    id: backendMsg.message_id || backendMsg.id || `msg_${Date.now()}_${Math.random()}`,
    content: content,
    role: role,
    timestamp: backendMsg.timestamp || backendMsg.created_at || new Date().toISOString(),
    metadata: backendMsg.metadata
  };
  
  return transformed;
};

export interface ConversationHistory {
  success: boolean;
  conversation_id: string;
  messages: ConversationHistoryMessage[];
  total_messages: number;
  project_id?: string | null;
  has_more?: boolean;
  next_cursor?: string | null;
}

export interface ProjectConversationResponse {
  conversation_id: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface AgenticCapability {
  name: string;
  description: string;
  category: string;
  enabled: boolean;
}

export interface AgenticCapabilities {
  capabilities: AgenticCapability[];
  project_id: string;
}

export interface ConversationResponse {
  id: string;
  type: string;
  entity: string | null;
  is_group: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  participant_count: number | null;
  unread_count: number | null;
  last_message: string | null;
}

export interface ConversationList {
  conversations: ConversationResponse[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaperChatRequest {
  paper_id: string;
  message: string;
  conversation_id?: string | null;
}

export interface DropChatResponse {
  success: boolean;
  response: string;
  conversation_id: string;
  processing_time: number;
  timestamp: string;
  metadata?: Record<string, any> | null;
}

// Add new interfaces for project conversations
export interface ProjectConversationsResponse {
  success: boolean;
  conversations: ConversationResponse[];
  pagination: {
    current_page: number;
    total_pages: number;
    total_conversations: number;
    conversations_per_page: number;
    has_next: boolean;
    has_prev: boolean;
  };
  project_id: string;
  filters: {
    conversation_type: string | null;
  };
}

export const agenticApi = {
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
   * Process a message through the agentic system
   */
  async processMessage(projectId: string, message: AgenticMessage): Promise<AgenticResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/agentic/${projectId}/process`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(message),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Agentic API JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Agentic API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to process message (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Get conversation history for a project
   */
  async getConversationHistory(
    projectId: string, 
    conversationId: string,
    limit?: number,
    offset?: number
  ): Promise<ConversationHistory> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    
    const url = `${API_BASE_URL}/api/v1/agentic/${projectId}/conversations/${conversationId}/history${params.toString() ? '?' + params.toString() : ''}`;

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
      console.error('Get conversation history JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch conversation history (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    // Transform backend messages to frontend format
    const filtered = (data.messages || []).filter((m: any) => {
      // Hide system messages and stored PDF context messages from UI
      if (!m) return false;
      const isSystem = (m.message_type && m.message_type.toLowerCase() === 'system');
      const isDropContext = Boolean(m.metadata && (m.metadata.drop_pdf_context === true));
      return !(isSystem || isDropContext);
    });
    const transformedMessages = filtered.map(transformBackendMessage);
    
    // Sort messages by timestamp to ensure chronological order
    transformedMessages.sort((a: ConversationHistoryMessage, b: ConversationHistoryMessage) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    
    return {
      ...data,
      messages: transformedMessages
    };
  },

  /**
   * Get or create project's main conversation
   */
  async getProjectConversation(projectId: string): Promise<ProjectConversationResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/projects/${projectId}/conversation`, {
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
      console.error('Get project conversation JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch project conversation (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Get conversations list for the user
   */
  async getConversations(
    page: number = 1,
    size: number = 20,
    conversation_type?: string
  ): Promise<ConversationList> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
    });
    
    if (conversation_type) {
      params.append('conversation_type', conversation_type);
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/?${params.toString()}`, {
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
      console.error('Get conversations JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch conversations (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Archive a conversation
   */
  async archiveConversation(projectId: string, conversationId: string): Promise<void> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/agentic/${projectId}/conversations/${conversationId}/archive`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      let data: any;
      try {
        data = await response.json();
      } catch (error) {
        console.error('Archive conversation JSON parse error:', error);
        throw new Error('Server returned invalid response. Please check if the backend is running.');
      }

      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to archive conversation (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }
  },

  /**
   * Get available agentic capabilities for a project
   */
  async getCapabilities(projectId: string): Promise<AgenticCapabilities> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/agentic/${projectId}/capabilities`, {
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
      console.error('Get capabilities JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch capabilities (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Chat with a specific paper PDF
   */
  async paperChat(projectId: string, payload: PaperChatRequest): Promise<AgenticResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    if (!token) throw new Error('Authentication required');

    const response = await fetch(`${API_BASE_URL}/api/v1/agentic/${projectId}/paper_chat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json().catch(() => {
      throw new Error('Invalid server response');
    });

    if (!response.ok) {
      throw new Error(this.extractErrorMessage(data, 'Paper chat failed'));
    }

    return data;
  },

  /**
   * Simple AI chat for project context
   */
  async simpleChat(projectId: string, payload: AgenticMessage): Promise<AgenticResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    if (!token) throw new Error('Authentication required');

    const response = await fetch(`${API_BASE_URL}/api/v1/agentic/${projectId}/simple_chat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json().catch(() => {
      throw new Error('Invalid server response');
    });

    if (!response.ok) {
      throw new Error(this.extractErrorMessage(data, 'Simple chat failed'));
    }

    return data;
  },

  /**
   * Chat with a dropped PDF file
   */
  async dropChat(
    projectId: string, 
    file: File | null, 
    message: string, 
    conversationId?: string
  ): Promise<DropChatResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    formData.append('message', message);
    if (conversationId) {
      formData.append('conversation_id', conversationId);
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/agentic/${projectId}/drop_chat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Drop chat JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to process PDF chat (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  async getProjectConversations(
    projectId: string,
    page: number = 1,
    size: number = 20,
    conversation_type?: string
  ): Promise<ProjectConversationsResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
    });
    
    if (conversation_type) {
      params.append('conversation_type', conversation_type);
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/projects/${projectId}?${params.toString()}`, {
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
      console.error('Get project conversations JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch project conversations (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },
};