/**
 * Conversations API
 * 
 * Handles conversation-related API calls
 */

export interface ConversationResponse {
  id: string;
  type: string;
  entity?: string;
  is_group: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
  participant_count?: number;
  unread_count?: number;
  last_message?: string;
}

export interface ConversationListResponse {
  conversations: ConversationResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ConversationsQueryParams {
  page?: number;
  size?: number;
  conversation_type?: string;
}

export interface MessageResponse {
  id: string;
  content?: string;  // Frontend expects this
  message?: string;  // Backend may provide this instead
  message_type: 'text' | 'file' | 'image' | 'system';
  sender_id: string;
  sender_name?: string;  // Backend may not always provide this
  created_at: string;
  updated_at: string;
  parent_message_id?: string;
  metadata?: any;
}

export interface MessageCreate {
  content: string;
  message_type?: 'text' | 'file' | 'image' | 'system';
  parent_message_id?: string;
  metadata?: any;
}

export interface MessagesResponse {
  messages: MessageResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const conversationsApi = {
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
   * Get user conversations with optional filtering and pagination
   */
  async getConversations(params: ConversationsQueryParams = {}): Promise<ConversationListResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.size) searchParams.set('size', params.size.toString());
    if (params.conversation_type) searchParams.set('conversation_type', params.conversation_type);

    const url = `${API_BASE_URL}/api/v1/conversations/?${searchParams.toString()}`;

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
      console.error('Get conversations JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get conversations API error - Server error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to fetch conversations (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }

    return data;
  },

  /**
   * Get or create project's main conversation
   */
  async getProjectConversation(projectId: string): Promise<ConversationResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }
    
    // Validate project ID format (should be UUID)
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(projectId)) {
      console.error('Invalid project ID format:', projectId);
      throw new Error('Invalid project ID format - must be UUID');
    }
    
    const url = `${API_BASE_URL}/api/v1/conversations/projects/${projectId}/conversation`;

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
      console.error('Get project conversation JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get project conversation API error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      // Handle specific error cases
      if (response.status === 401) {
        throw new Error('Authentication failed - please log in again');
      } else if (response.status === 403) {
        throw new Error('Access denied - you do not have permission to access this project');
      } else if (response.status === 404) {
        throw new Error('Project not found');
      } else if (response.status === 422) {
        throw new Error('Invalid project ID format');
      }
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to get project conversation (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }


    
    // Backend returns wrapper: { success: true, conversation: {...}, created: boolean }
    // Extract the actual conversation object
    if (data && data.success && data.conversation) {
      console.log('Successfully extracted conversation:', data.conversation);
      
      // Check if conversation object has required fields
      if (!data.conversation.id) {
        console.error('Conversation object missing ID field:', data.conversation);
        console.error('This might be a backend serialization issue');
        throw new Error('Backend returned conversation without ID field - please contact support');
      }
      
      // Validate conversation object structure
      const requiredFields = ['id', 'type', 'is_group', 'created_at', 'updated_at'];
      const missingFields = requiredFields.filter(field => !(field in data.conversation));
      if (missingFields.length > 0) {
        console.error('Conversation missing required fields:', missingFields);
        console.error('Conversation object:', data.conversation);
        throw new Error(`Backend returned incomplete conversation object - missing: ${missingFields.join(', ')}`);
      }
      
      return data.conversation;
    } else if (data && data.success === false) {
      console.error('Backend API reported failure:', data);
      const errorMsg = data.message || data.error || 'Unknown backend error';
      throw new Error(`Backend error: ${errorMsg}`);
    } else if (data && data.conversation === null) {
      console.error('Backend returned null conversation');
      throw new Error('No conversation found for this project - it may need to be created first');
    } else {
      console.error('Invalid conversation response structure:', data);
      console.error('Expected structure: { success: true, conversation: {...}, created: boolean }');
      throw new Error('Invalid response structure from conversation API');
    }
  },

  /**
   * Get conversation messages with pagination
   */
  async getConversationMessages(
    conversationId: string, 
    params: { page?: number; size?: number; before_message_id?: string; after_message_id?: string } = {}
  ): Promise<MessagesResponse> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.size) searchParams.set('size', params.size.toString());
    if (params.before_message_id) searchParams.set('before_message_id', params.before_message_id);
    if (params.after_message_id) searchParams.set('after_message_id', params.after_message_id);

    const url = `${API_BASE_URL}/api/v1/conversations/${conversationId}/messages?${searchParams.toString()}`;

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
      console.error('Get messages JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Get messages API error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to get messages (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }


    
    // Backend returns wrapper: { success: true, messages: [...], pagination: {...} }
    // Extract the actual messages array and pagination info
    if (data && data.messages) {
      return {
        messages: data.messages,
        total: data.pagination?.total || 0,
        page: data.pagination?.page || 1,
        size: data.pagination?.size || 50,
        pages: data.pagination?.pages || 1
      };
    } else {
      console.error('Invalid messages response structure:', data);
      return {
        messages: [],
        total: 0,
        page: 1,
        size: 50,
        pages: 1
      };
    }
  },

  /**
   * Send a message to a conversation
   */
  async sendMessage(conversationId: string, messageData: MessageCreate): Promise<any> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const url = `${API_BASE_URL}/api/v1/conversations/${conversationId}/messages`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(messageData),
    });

    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      console.error('Send message JSON parse error:', error);
      throw new Error('Server returned invalid response. Please check if the backend is running.');
    }

    if (!response.ok) {
      console.error('Send message API error');
      console.error(`Status: ${response.status} ${response.statusText}`);
      console.error('Response data:', JSON.stringify(data, null, 2));
      
      const errorMessage = this.extractErrorMessage(
        data, 
        `Failed to send message (${response.status}): ${response.statusText || 'Unknown error'}`
      );
      
      throw new Error(errorMessage);
    }


    return data;
  },
}; 