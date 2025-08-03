import { apiBase } from "./api-base";

export interface AgenticMessage {
  message: string;
  context?: Record<string, any>;
  conversation_id?: string;
}

export interface AgenticResponse {
  response: string;
  conversation_id: string;
  message_id: string;
  context?: Record<string, any>;
  suggestions?: string[];
}

export interface ConversationHistoryMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ConversationHistory {
  conversation_id: string;
  messages: ConversationHistoryMessage[];
  total_messages: number;
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

export const agenticApi = {
  /**
   * Process a message through the agentic system
   */
  async processMessage(projectId: string, message: AgenticMessage): Promise<AgenticResponse> {
    const response = await apiBase.post(`/api/v1/agentic/${projectId}/process`, message);
    return response.data;
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
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    
    const url = `/api/v1/agentic/${projectId}/conversations/${conversationId}/history${params.toString() ? '?' + params.toString() : ''}`;
    const response = await apiBase.get(url);
    return response.data;
  },

  /**
   * Archive a conversation
   */
  async archiveConversation(projectId: string, conversationId: string): Promise<void> {
    await apiBase.post(`/api/v1/agentic/${projectId}/conversations/${conversationId}/archive`);
  },

  /**
   * Get available agentic capabilities for a project
   */
  async getCapabilities(projectId: string): Promise<AgenticCapabilities> {
    const response = await apiBase.get(`/api/v1/agentic/${projectId}/capabilities`);
    return response.data;
  },
}; 