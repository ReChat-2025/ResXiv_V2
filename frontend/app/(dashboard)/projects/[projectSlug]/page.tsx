"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Loader2, Send, Plus, Search, Upload, X, MessageSquare, Tag, Brain, Menu, FileQuestion, Paperclip } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { agenticApi, ConversationHistoryMessage, ProjectConversationResponse, ProjectConversationsResponse } from '@/lib/api/agentic-api';
import { projectsApi } from '@/lib/api/projects-api';
import { userApi, UserResponse } from '@/lib/api/user-api';

interface ConversationItem {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
  type: 'AGENTIC' | 'PDF' | 'DROP' | 'AI' | 'GROUP';
}

interface ChatMode {
  type: 'agentic' | 'paper' | 'drop' | 'simple';
  paper_id?: string;
  paper_title?: string;
  uploaded_file?: File;
}

function ProjectHomePage() {
  const params = useParams();
  const projectSlug = params.projectSlug as string;
  
  // Add refs for auto-scrolling and unique ID counter
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messageIdCounterRef = useRef<number>(0);
  
  // Generate absolutely unique message ID
  const generateUniqueMessageId = (prefix: string): string => {
    messageIdCounterRef.current += 1;
    return `${prefix}_${Date.now()}_${messageIdCounterRef.current}_${Math.random().toString(36).substr(2, 9)}`;
  };
  
  // Core state
  const [currentMessage, setCurrentMessage] = useState('');
  const [conversationHistory, setConversationHistory] = useState<ConversationHistoryMessage[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [user, setUser] = useState<UserResponse | null>(null);
  const [pastConversations, setPastConversations] = useState<ConversationItem[]>([]);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [isLoadingUser, setIsLoadingUser] = useState(true);
  const [projectConversation, setProjectConversation] = useState<ProjectConversationResponse | null>(null);
  const [availableProjects, setAvailableProjects] = useState<any[]>([]);
  
  // Chat mode and file handling state
  const [chatMode, setChatMode] = useState<ChatMode>({ type: 'agentic' });
  const [dragActive, setDragActive] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  
  // UI state
  const [isLoading, setIsLoading] = useState(false);

  // Utility function to ensure unique message IDs and remove duplicates
  const ensureUniqueMessages = (messages: ConversationHistoryMessage[]): ConversationHistoryMessage[] => {
    if (!Array.isArray(messages)) {
      return [];
    }
    
    const seenIds = new Set<string>();
    const uniqueMessages: ConversationHistoryMessage[] = [];
    
    messages.forEach((message, index) => {
      if (!message || typeof message !== 'object') {
        return;
      }
      
      // Handle missing or invalid IDs
      let uniqueId = message.id;
      if (!uniqueId || typeof uniqueId !== 'string') {
        uniqueId = `missing_id_${index}_${Date.now()}`;
      }
      
      // Ensure backend messages have a unique prefix
      if (!uniqueId.startsWith('user_') && !uniqueId.startsWith('assistant_') && !uniqueId.startsWith('error_')) {
        uniqueId = `backend_${uniqueId}_${index}`;
      }
      
      // If ID is still not unique, make it unique
      let counter = 0;
      let finalId = uniqueId;
      while (seenIds.has(finalId)) {
        counter++;
        finalId = `${uniqueId}_dup_${counter}`;
      }
      
      seenIds.add(finalId);
      uniqueMessages.push({
        ...message,
        id: finalId
      });
    });
    
    return uniqueMessages;
  };

  // Validate and fix conversation alternating pattern
  const validateConversationPattern = (messages: ConversationHistoryMessage[]): ConversationHistoryMessage[] => {
    if (messages.length <= 1) return messages;
    
    const fixedMessages = [...messages];
    let fixedCount = 0;
    
    for (let i = 0; i < fixedMessages.length; i++) {
      const current = fixedMessages[i];
      
      // Check for obvious content-based role mismatches
      const content = current.content.toLowerCase();
      const originalContent = current.content;
      
      // AI greeting/response patterns
      const isAIResponse = 
        content.includes('how can i assist') ||
        content.includes('hello! how can i') ||
        content.includes("i'm here to help") ||
        content.includes("hey there!") ||
        content.includes("it sounds like") ||
        content.includes('based on') ||
        content.includes('here are') ||
        content.includes('i found') ||
        content.includes('i can help') ||
        content.startsWith('###') ||
        (content.length > 200 && !content.includes('?') && content.includes('.'));
      
      // User question/message patterns  
      const isUserMessage = 
        (content.includes('?') && content.length < 200) ||
        content.match(/^(hi|hello|hey|yo|what|how|why|when|where|can you|could you|please)/i) ||
        (content.length < 100 && !content.includes('i can help') && !content.includes('based on'));
      
      // Fix AI responses marked as user
      if (current.role === 'user' && isAIResponse && !isUserMessage) {
        fixedMessages[i] = { ...current, role: 'assistant' };
        fixedCount++;
      }
      
      // Special case for greeting messages
      if (originalContent.includes('How can I assist you today') && current.role === 'user') {
        fixedMessages[i] = { ...current, role: 'assistant' };
        fixedCount++;
      }
      
      // Fix user messages marked as AI  
      if (current.role === 'assistant' && isUserMessage && !isAIResponse) {
        fixedMessages[i] = { ...current, role: 'user' };
        fixedCount++;
      }
    }
    
    return fixedMessages;
  };

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [conversationHistory, isLoading]);

  // Load user data on mount
  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await userApi.getCurrentUser();
        setUser(userData);
      } catch (error) {
        console.error('Failed to load user:', error);
      } finally {
        setIsLoadingUser(false);
      }
    };
    loadUser();
  }, []);

  // Resolve project slug to UUID
  useEffect(() => {
    const resolveProjectId = async () => {
      if (!projectSlug) return;
      
      try {
        const { projects } = await projectsApi.getProjects({ size: 100 });
        setAvailableProjects(projects);
        
        // Find project by slug
        const match = projects.find(p => p.slug === projectSlug) ||
                     projects.find(p => p.slug?.toLowerCase() === projectSlug.toLowerCase()) ||
                     projects.find(p => p.name?.toLowerCase().replace(/\s+/g, '-') === projectSlug.toLowerCase());
        
        if (match) {
          setProjectId(match.id);
        } else {
          setProjectError(`Project "${projectSlug}" not found. ${projects.length} projects available.`);
        }
      } catch (error) {
        console.error('Failed to resolve project ID:', error);
        setProjectError('Failed to resolve project - authentication may be required');
      }
    };
    resolveProjectId();
  }, [projectSlug]);

  // Load project data when projectId is available
  useEffect(() => {
    const loadProjectData = async () => {
      if (!projectId) return;
      
      try {
        // Load project's main conversation
        const conversation = await agenticApi.getProjectConversation(projectId);
        setProjectConversation(conversation);
        setCurrentConversationId(conversation.conversation_id);
        
        // Load conversation history if available
        if (conversation.conversation_id) {
          try {
            const history = await agenticApi.getConversationHistory(projectId, conversation.conversation_id);
            if (history.messages) {
              
              const processedMessages = ensureUniqueMessages(history.messages);
              
              const validatedMessages = validateConversationPattern(processedMessages);
              setConversationHistory(validatedMessages);
            }
          } catch (error) {
            console.warn('Failed to load conversation history:', error);
          }
        }
      } catch (error) {
        console.error('Failed to load project conversation:', error);
      }
    };

    loadProjectData();
  }, [projectId]);

  // Load conversations list separately
  useEffect(() => {
    const loadConversations = async () => {
      if (!projectId) return;
      
      setIsLoadingConversations(true);
      try {
        const projectConversations = await agenticApi.getProjectConversations(projectId, 1, 20);
        
        if (projectConversations.success) {
          const conversations: ConversationItem[] = await Promise.all(
            projectConversations.conversations.map(async (conv) => {
              const typeLabels = {
                'AGENTIC': 'AI Chat',
                'DROP': 'PDF Chat', 
                'GROUP': 'Group Chat',
                'PAPER': 'Paper Chat'
              };
              
              let title = '';
              let lastMessage = 'No messages yet';
              
              // Helper function to clean markdown formatting from text
              const cleanMarkdownText = (text: string): string => {
                return text
                  .replace(/#{1,6}\s*/g, '') // Remove markdown headers (# ## ### etc)
                  .replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold formatting
                  .replace(/\*(.*?)\*/g, '$1') // Remove italic formatting
                  .replace(/`(.*?)`/g, '$1') // Remove inline code formatting
                  .replace(/\[(.*?)\]\(.*?\)/g, '$1') // Remove link formatting, keep text
                  .replace(/^\s*[-*+]\s+/gm, '') // Remove bullet points
                  .replace(/^\s*\d+\.\s+/gm, '') // Remove numbered lists
                  .replace(/\n+/g, ' ') // Replace line breaks with spaces
                  .trim();
              };

              // If last_message is null/empty, try to get the first message from conversation history
              if (!conv.last_message || !conv.last_message.trim()) {
                try {
                  const history = await agenticApi.getConversationHistory(projectId, conv.id, 1, 0);
                  if (history.messages && history.messages.length > 0) {
                    const firstMessage = history.messages[0];
                    const cleanedContent = cleanMarkdownText(firstMessage.content);
                    title = cleanedContent.length > 20 
                      ? cleanedContent.substring(0, 20) + '...'
                      : cleanedContent;
                    lastMessage = firstMessage.content;
                  } else {
                    title = `${typeLabels[conv.type as keyof typeof typeLabels] || conv.type}`;
                  }
                } catch (error) {
                  console.warn(`Failed to load history for conversation ${conv.id}:`, error);
                  title = `${typeLabels[conv.type as keyof typeof typeLabels] || conv.type}`;
                }
              } else {
                const cleanedContent = cleanMarkdownText(conv.last_message);
                title = cleanedContent.length > 20 
                  ? cleanedContent.substring(0, 20) + '...'
                  : cleanedContent;
                lastMessage = conv.last_message;
              }
              
              return {
                id: conv.id,
                title: title,
                lastMessage: lastMessage,
                timestamp: conv.updated_at,
                type: conv.type as 'AGENTIC' | 'PDF' | 'DROP' | 'AI' | 'GROUP'
              };
            })
          );
          setPastConversations(conversations);
        } else {
          console.warn('Failed to load conversations: API returned success=false');
          setPastConversations([]);
        }
      } catch (error) {
        console.error('Failed to load conversations list:', error);
        setPastConversations([]);
      } finally {
        setIsLoadingConversations(false);
      }
    };

    loadConversations();
  }, [projectId]);

  // File handlers
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.includes('pdf')) {
      handleFileSelection(files[0]);
    }
  };

  const handleFileInputChange = () => {
    if (fileInputRef.current?.files && fileInputRef.current.files.length > 0) {
      handleFileSelection(fileInputRef.current.files[0]);
    }
  };

  const handleFileSelection = (file: File) => {
    if (!file.type.includes('pdf')) {
      alert('Please select a PDF file');
      return;
    }
    
    if (file.size > 50 * 1024 * 1024) {
      alert('File size must be less than 50MB');
      return;
    }

    setChatMode({
      type: 'drop',
      uploaded_file: file
    });
  };

  const removeUploadedFile = () => {
    setChatMode({ type: 'agentic' });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSendMessage = async () => {
    if (!currentMessage.trim() || !projectId) return;
    
    setIsLoading(true);
    
    // Add user message immediately
    const userMessage: ConversationHistoryMessage = {
      id: generateUniqueMessageId('user'),
      content: currentMessage,
        role: 'user',
        timestamp: new Date().toISOString(),
      };

    setConversationHistory(prev => {
      const updated = ensureUniqueMessages([...prev, userMessage]);
      const validated = validateConversationPattern(updated);
      return validated;
    });
    
    const messageToSend = currentMessage;
    setCurrentMessage('');

    try {
      let response;
      
      switch (chatMode.type) {
        case 'paper':
          if (!chatMode.paper_id) throw new Error('No paper selected');
          response = await agenticApi.paperChat(projectId, {
            paper_id: chatMode.paper_id,
            message: messageToSend,
            conversation_id: currentConversationId || undefined
          });
          break;
          
        case 'drop':
          if (!chatMode.uploaded_file) throw new Error('No file uploaded');
          response = await agenticApi.dropChat(
            projectId,
            chatMode.uploaded_file,
            messageToSend,
            currentConversationId || undefined
          );
          break;
          
        case 'simple':
          response = await agenticApi.simpleChat(projectId, {
            message: messageToSend,
            conversation_id: currentConversationId || undefined,
            context: {}
          });
          break;
          
        default:
          response = await agenticApi.processMessage(projectId, {
            message: messageToSend,
            conversation_id: currentConversationId || undefined,
            context: {}
          });
          break;
      }
      
      // Add assistant response
      const assistantMessage: ConversationHistoryMessage = {
        id: generateUniqueMessageId('assistant'),
        content: response.response,
        role: 'assistant', 
        timestamp: response.timestamp,
        metadata: response.metadata || undefined
      };
      
      setConversationHistory(prev => {
        const updated = ensureUniqueMessages([...prev, assistantMessage]);
        const validated = validateConversationPattern(updated);
        return validated;
      });
      
      if (response.conversation_id !== currentConversationId) {
      setCurrentConversationId(response.conversation_id);
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      
      const errorMessage: ConversationHistoryMessage = {
        id: generateUniqueMessageId('error'),
        content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}`,
        role: 'assistant',
        timestamp: new Date().toISOString(),
      };
      setConversationHistory(prev => ensureUniqueMessages([...prev, errorMessage]));
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setConversationHistory([]);
    setCurrentConversationId(projectConversation?.conversation_id || null);
    setCurrentMessage('');
    setChatMode({ type: 'agentic' });
    removeUploadedFile();
  };

  const handleConversationSelect = async (conversationId: string) => {
    if (!projectId || conversationId === currentConversationId) return;
    
    try {
      setCurrentConversationId(conversationId);
      
      // Load the conversation history
      const history = await agenticApi.getConversationHistory(projectId, conversationId);
      if (history.messages) {
        
        const processedMessages = ensureUniqueMessages(history.messages);
        
        const validatedMessages = validateConversationPattern(processedMessages);
        setConversationHistory(validatedMessages);
      } else {
        setConversationHistory([]);
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
      setConversationHistory([]);
    }
  };

  const formatConversationTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const isToday = date.toDateString() === new Date().toDateString();
    return isToday 
      ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : date.toLocaleDateString();
  };

  // Map conversation types to user-friendly labels and colors
  const getConversationTypeDisplay = (type: string) => {
    const typeMap: Record<string, { label: string; className: string }> = {
      'AGENTIC': { label: 'Agentic', className: 'bg-secondary/10 text-secondary-foreground' },
      'DROP': { label: 'Attach', className: 'bg-secondary/10 text-secondary-foreground' },
      'AI': { label: 'AI', className: 'bg-secondary/10 text-secondary-foreground' },
      'PDF': { label: 'PDF', className: 'bg-secondary/10 text-secondary-foreground' },
      'GROUP': { label: 'Group', className: 'bg-secondary/10 text-secondary-foreground' },
    };
    
    return typeMap[type] || { label: type, className: 'bg-secondary/10 text-secondary-foreground' };
  };

  // Group conversations by date
  const groupConversationsByDate = (conversations: ConversationItem[]) => {
    const groups: { [key: string]: ConversationItem[] } = {};
    
    conversations.forEach(conversation => {
      const date = new Date(conversation.timestamp);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      
      let dateKey: string;
      if (date.toDateString() === today.toDateString()) {
        dateKey = 'Today';
      } else if (date.toDateString() === yesterday.toDateString()) {
        dateKey = 'Yesterday';
      } else {
        dateKey = date.toLocaleDateString('en-US', { 
          weekday: 'long', 
          year: 'numeric', 
          month: 'long', 
          day: 'numeric' 
        });
      }
      
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      groups[dateKey].push(conversation);
    });
    
    // Sort dates with Today first, Yesterday second, then chronologically descending
    const sortedDateKeys = Object.keys(groups).sort((a, b) => {
      if (a === 'Today') return -1;
      if (b === 'Today') return 1;
      if (a === 'Yesterday') return -1;
      if (b === 'Yesterday') return 1;
      
      // For other dates, sort by the first conversation's timestamp in descending order
      const aDate = new Date(groups[a][0].timestamp);
      const bDate = new Date(groups[b][0].timestamp);
      return bDate.getTime() - aDate.getTime();
    });
    
    return sortedDateKeys.map(dateKey => ({
      date: dateKey,
      conversations: groups[dateKey].sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )
    }));
  };

  // Loading states
  if (isLoadingUser || !projectId) {
  return (
      <div className="flex h-full">
        <div className="w-80 border-r bg-muted/20">
          <div className="p-4">
            <div className="h-8 bg-muted rounded animate-pulse mb-4" />
            <div className="h-6 bg-muted rounded animate-pulse mb-2" />
            <div className="h-10 bg-muted rounded animate-pulse" />
          </div>
        </div>
        
        <div className="flex-1 flex items-center justify-center">
          {projectError ? (
            <div className="text-center text-destructive my-8">
              <p className="text-lg font-medium">{projectError}</p>
              {availableProjects.length === 0 && (
                <div className="mt-4 p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground mb-2">
                    No projects found - this usually means you're not authenticated as the correct user.
                  </p>
                  <Button 
                    onClick={() => {
                      localStorage.removeItem('accessToken');
                      window.location.href = '/login';
                    }}
                    variant="outline" 
                    size="sm"
                  >
                    Login as Different User
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="h-8 w-8 animate-spin" />
              <p className="text-muted-foreground">Loading project...</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full max-h-full overflow-hidden">
      {/* Mobile Sidebar Overlay */}
      {isMobileSidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="fixed inset-0 bg-black/50" onClick={() => setIsMobileSidebarOpen(false)} />
          <div className="fixed left-0 top-0 h-full w-80 bg-background border-r shadow-lg overflow-hidden flex flex-col">
            {/* Mobile Sidebar Header */}
            <div className="p-4 border-b flex items-center justify-between flex-shrink-0">
              <h2 className="text-lg font-semibold">Past Conversations</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsMobileSidebarOpen(false)}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            {/* Mobile Sidebar Content */}
            <div className="p-4 flex-shrink-0">
              {/* Search */}
              <div className="relative mb-4">
                <Input 
                  placeholder="Search"
                  className="pl-10" 
                />
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
              </div>
              
              {/* New Chat Button */}
              <Button 
                onClick={() => {
                  handleNewChat();
                  setIsMobileSidebarOpen(false);
                }}
                className="w-full bg-foreground text-background hover:bg-foreground/90 mb-4"
              >
                <Plus className="w-4 h-4 mr-2" />
                New Chat
              </Button>
            </div>
            
            {/* Mobile Conversations List */}
            <div className="flex-1 overflow-y-auto px-4 pb-4 min-h-0">
              {isLoadingConversations ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-16 bg-muted rounded animate-pulse" />
                  ))}
                </div>
              ) : pastConversations.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                  <Search className="w-8 h-8 mb-2" />
                  <p className="text-sm">No past conversations</p>
                </div>
                            ) : (
                <div className="space-y-4">
                  {groupConversationsByDate(pastConversations).map((group) => (
                    <div key={group.date} className="space-y-3">
                      <h3 className="text-sm font-semibold text-muted-foreground px-2 py-1">
                        {group.date}
                      </h3>
                      {group.conversations.map((conversation) => (
                        <div 
                          key={conversation.id} 
                          className="cursor-pointer hover:bg-muted/30 transition-colors px-1.5 py-2 rounded"
                          onClick={() => {
                            handleConversationSelect(conversation.id);
                            setIsMobileSidebarOpen(false);
                          }}
                        >
                          <div className="flex justify-between items-start gap-2">
                            <h4 className="text-sm font-medium truncate flex-1 leading-tight">
                              {conversation.title}
                            </h4>
                            <div className="flex items-center gap-1.5 flex-shrink-0">
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getConversationTypeDisplay(conversation.type).className}`}>
                                {getConversationTypeDisplay(conversation.type).label}
                              </span>
                              {conversation.id === currentConversationId && (
                                <div className="w-2 h-2 bg-primary rounded-full"></div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Left Sidebar - Clean conversations only */}
      <div className="hidden md:flex w-64 lg:w-80 border-r bg-muted/20 flex-col h-full overflow-hidden flex-shrink-0 min-h-0">
        {/* Header */}
        <div className="p-4 lg:p-6 border-b flex-shrink-0">
          <h2 className="text-lg font-semibold mb-4">Past Conversations</h2>
          
          {/* Search */}
          <div className="relative mb-4">
            <Input 
              placeholder="Search" 
              className="pl-10" 
            />
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          </div>
          
          {/* New Chat Button */}
          <Button 
            onClick={handleNewChat}
            className="w-full bg-foreground text-background hover:bg-foreground/90"
          >
            <Plus className="w-4 h-4 mr-2" />
              New Chat
            </Button>
          </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto min-h-0 scroll-smooth flex-shrink-0">
          {isLoadingConversations ? (
            <div className="p-4 space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-muted rounded animate-pulse" />
                ))}
              </div>
          ) : pastConversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
              <Search className="w-8 h-8 mb-2" />
              <p className="text-sm">No past conversations</p>
            </div>
                    ) : (
            <div className="p-4 space-y-4">
              {groupConversationsByDate(pastConversations).map((group) => (
                <div key={group.date} className="space-y-3">
                  <h3 className="text-sm font-semibold text-muted-foreground px-2 py-1">
                    {group.date}
                  </h3>
                  {group.conversations.map((conversation) => (
                    <div 
                      key={conversation.id}
                      className="cursor-pointer hover:bg-muted/30 transition-colors px-1.5 py-2 rounded"
                      onClick={() => handleConversationSelect(conversation.id)}
                    >
                      <div className="flex justify-between items-start gap-2">
                        <h4 className="text-sm font-medium truncate flex-1 leading-tight">
                          {conversation.title}
                        </h4>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getConversationTypeDisplay(conversation.type).className}`}>
                            {getConversationTypeDisplay(conversation.type).label}
                          </span>
                          {conversation.id === currentConversationId && (
                            <div className="w-2 h-2 bg-primary rounded-full"></div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div 
        className={`flex-1 flex flex-col h-full min-h-0 overflow-hidden ${dragActive ? 'bg-muted/50' : ''}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Mobile Header */}
        <div className="md:hidden border-b bg-background p-4 flex items-center justify-between flex-shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsMobileSidebarOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </Button>
          <h1 className="text-lg font-semibold">Chat</h1>
          <div className="w-8" /> {/* Spacer for centering */}
          </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {conversationHistory.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-4 md:p-8">
              <div className="mb-8">
                <h1 className="text-2xl md:text-4xl font-bold text-center mb-4">
                  Hello, {user?.name || 'User'}!
                </h1>
                <p className="text-lg md:text-xl text-muted-foreground text-center">
                  What do you want to learn today?
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto scroll-smooth min-h-0">
              <div className="p-4 md:p-6 lg:p-8">
                <div className="max-w-full md:max-w-4xl mx-auto space-y-4 md:space-y-6">
                  {conversationHistory.map((message) => (
                    <div 
                      key={message.id}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`flex items-start max-w-[90%] md:max-w-[80%] ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                        <Avatar className={`w-6 h-6 md:w-8 md:h-8 ${message.role === 'user' ? 'ml-2' : 'mr-2'} flex-shrink-0`}>
                          <AvatarFallback className="text-xs md:text-sm">
                            {message.role === 'user' ? (user?.name?.charAt(0) || 'U') : 'AI'}
                          </AvatarFallback>
                        </Avatar>
                        <div className={`p-2 md:p-3 rounded-lg ${
                          message.role === 'user' 
                            ? 'bg-primary text-primary-foreground' 
                            : 'bg-muted'
                        }`}>
                          {message.role === 'assistant' ? (
                            <div className="prose prose-sm md:prose-base prose-slate dark:prose-invert max-w-none">
                              <ReactMarkdown 
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  h1: ({children}) => <h1 className="text-lg md:text-xl font-bold mb-2 mt-3 first:mt-0">{children}</h1>,
                                  h2: ({children}) => <h2 className="text-base md:text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h2>,
                                  h3: ({children}) => <h3 className="text-sm md:text-base font-bold mb-2 mt-2 first:mt-0">{children}</h3>,
                                  p: ({children}) => <p className="mb-2 last:mb-0 text-sm md:text-base leading-relaxed">{children}</p>,
                                  ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1 text-sm md:text-base">{children}</ul>,
                                  ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1 text-sm md:text-base">{children}</ol>,
                                  li: ({children}) => <li className="leading-relaxed">{children}</li>,
                                  strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                                  em: ({children}) => <em className="italic">{children}</em>,
                                  code: ({children}) => <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                                  pre: ({children}) => <pre className="bg-muted p-2 rounded text-xs overflow-x-auto mb-2">{children}</pre>,
                                  blockquote: ({children}) => <blockquote className="border-l-4 border-muted-foreground pl-3 my-2 italic">{children}</blockquote>
                                }}
                              >
                                {message.content}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            <p className="whitespace-pre-wrap break-words text-sm md:text-base">{message.content}</p>
                          )}
                          {message.metadata && (
                            <div className="mt-1 text-xs opacity-70">
                              {message.metadata.agent && `Agent: ${message.metadata.agent}`}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="flex items-start">
                        <Avatar className="w-6 h-6 md:w-8 md:h-8 mr-2 flex-shrink-0">
                          <AvatarFallback className="text-xs md:text-sm">AI</AvatarFallback>
                        </Avatar>
                        <div className="p-2 md:p-3 rounded-lg bg-muted">
                          <div className="flex items-center gap-1">
                            <Loader2 className="w-3 h-3 md:w-4 md:h-4 animate-spin" />
                            <span className="text-sm">Thinking...</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  {/* Scroll anchor */}
                  <div ref={messagesEndRef} />
                </div>
              </div>
            </div>
          )}
          
          {/* Input Area with Chat Mode Selector */}
          <div className="border-t bg-background p-3 md:p-4 flex-shrink-0">
            <div className="max-w-full md:max-w-4xl mx-auto space-y-3">
              {/* Upload indicator */}
              {chatMode.type === 'drop' && chatMode.uploaded_file && (
                <div className="p-2 bg-muted rounded-md text-xs flex items-center justify-between">
                  <span className="truncate flex-1">{chatMode.uploaded_file.name}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={removeUploadedFile}
                    className="h-6 w-6 p-0"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              )}

              {/* Input */}
              <div className="relative bg-background border-2 border-border rounded-2xl shadow-sm hover:shadow-md focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all duration-200">
                <Input 
                  value={currentMessage}
                  onChange={(e) => setCurrentMessage(e.target.value)}
                  placeholder="Ask me anything..."
                  className="w-full h-14 pr-16 text-base bg-transparent border-0 rounded-2xl focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/60"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  disabled={isLoading}
                />
                
                {/* Send Button - Right Side */}
                <Button 
                  onClick={handleSendMessage}
                  disabled={!currentMessage.trim() || isLoading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-10 w-10 rounded-xl bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  {isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-primary-foreground" />
                  ) : (
                    <Send className="h-6 w-6 rotate-45 text-primary-foreground" />
                  )}
                </Button>
              </div>

              {/* Chat Mode Buttons */}
              <div className="flex justify-center gap-2 overflow-x-auto pt-2">
                <Button 
                  variant={chatMode.type === 'agentic' ? 'default' : 'outline'} 
                  size="sm"
                  onClick={() => setChatMode({ type: 'agentic' })}
                  className="flex-shrink-0 h-9 px-4"
                >
                  <Brain className="w-4 h-4 mr-2" />
                  <span>Agentic</span>
                </Button>
                <Button 
                  variant={chatMode.type === 'simple' ? 'default' : 'outline'} 
                  size="sm"
                  onClick={() => setChatMode({ type: 'simple' })}
                  className="flex-shrink-0 h-9 px-4"
                >
                  <MessageSquare className="w-4 h-4 mr-2" />
                  <span>AI Chat</span>
                </Button>
                <Button 
                  variant={chatMode.type === 'paper' ? 'default' : 'outline'} 
                  size="sm"
                  onClick={() => setChatMode({ type: 'paper' })}
                  className="flex-shrink-0 h-9 px-4"
                >
                  <Tag className="w-4 h-4 mr-2" />
                  <span>Tag papers</span>
                </Button>
                <Button 
                  variant={chatMode.type === 'drop' ? 'default' : 'outline'} 
                  size="sm"
                  onClick={() => {
                    setChatMode({ type: 'drop' });
                    fileInputRef.current?.click();
                  }}
                  className="flex-shrink-0 h-9 px-4"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  <span>Attach pdf</span>
                </Button>
              </div>
            </div>
          </div>
        </div>
        
        {/* Drag overlay */}
        {dragActive && (
          <div className="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary flex items-center justify-center">
            <div className="text-center">
              <Upload className="w-12 h-12 mx-auto mb-4 text-primary" />
              <p className="text-lg font-medium text-primary">Drop PDF here to chat</p>
              </div>
          </div>
        )}
        
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileInputChange}
          className="hidden"
        />
      </div>
      </div>
  );
}

function ProtectedProjectHomePage() {
  return <ProjectHomePage />;
}

export default ProtectedProjectHomePage; 