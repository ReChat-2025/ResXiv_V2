"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { projectsApi } from "@/lib/api/projects-api";
import { membersApi, type ProjectMember } from "@/lib/api/members-api";
import { conversationsApi, type MessageResponse, type ConversationResponse } from "@/lib/api/conversations-api";
import { userApi, type UserResponse } from "@/lib/api/user-api";
import { PageLayout } from "@/components/layout/page-layout";
import { CollaborateSidebar } from "@/components/collaborate/CollaborateSidebar";
import { ChatArea } from "@/components/collaborate/ChatArea";
import { TasksView } from "@/components/collaborate/TasksView";
import { JournalsView } from "@/components/collaborate/JournalsView";
import { AddMemberDialog } from "@/components/collaborate/AddMemberDialog";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { appConfig, type TeamMember } from "@/lib/config/app-config";
import { useToast } from "@/hooks/use-toast";

// Chat component message interface (simplified for compatibility)
interface Message {
  id: string;
  senderName: string;
  senderAvatar?: string;
  content: string;
  timestamp: string;
  type?: 'text' | 'image' | 'file';
}

interface Notification {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  type: 'info' | 'warning' | 'success' | 'error';
}

interface Project {
  id: string;
  name: string;
  avatar?: string;
  avatarFallback: string;
}

function ProjectCollaboratePage() {
  const router = useRouter();
  const params = useParams();
  const projectSlug = params.projectSlug as string;
  const { toast } = useToast();
  
  // Current selected section state
  const [selectedSection, setSelectedSection] = useState('messages');
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [isProjectLoading, setIsProjectLoading] = useState(true);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [currentConversation, setCurrentConversation] = useState<ConversationResponse | null>(null);
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isAddMemberDialogOpen, setIsAddMemberDialogOpen] = useState(false);
  const [memberError, setMemberError] = useState<string | null>(null);
  
  // Fetch project data based on slug
  useEffect(() => {
    const fetchProject = async () => {
      if (projectSlug) {
        try {
          setIsProjectLoading(true);
          // Get all projects to find the one with matching slug
          const projectsResponse = await projectsApi.getProjects();
          const project = projectsResponse.projects.find((p: any) => 
            p.slug === projectSlug || p.id === projectSlug
          );
          
          if (project) {
            setCurrentProject({
              id: project.id,
              name: project.name,
              avatarFallback: project.name.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase(),
            });
          } else {
            // Project not found, redirect to projects
            router.push('/projects');
          }
        } catch (error) {
          console.error('Failed to fetch project:', error);
          router.push('/projects');
        } finally {
          setIsProjectLoading(false);
        }
      }
    };

    fetchProject();
  }, [projectSlug, router]);

  // Fetch members when project is loaded
  useEffect(() => {
    const fetchMembers = async () => {
      if (currentProject) {
        try {
          setIsLoadingMembers(true);
          setMemberError(null);
          const projectMembers = await membersApi.getProjectMembers(currentProject.id);
          
          // Transform to TeamMember format
          const teamMembers: TeamMember[] = projectMembers.map((member: ProjectMember) => ({
            id: member.id,
            name: member.user?.name || 'Unknown User',
            avatar: undefined, // No avatar field in backend response
            status: 'offline', // Default status since not provided by backend
            role: member.role || 'read', // Ensure role is always a string, default to 'read'
          }));
          
          setMembers(teamMembers);
        } catch (error) {
          console.error('Failed to fetch project members:', error);
          const errorMessage = error instanceof Error ? error.message : 'Failed to load members';
          setMemberError(errorMessage);
          setMembers([]);
          toast({
            variant: "destructive",
            title: "Error",
            description: "Failed to load project members"
          });
        } finally {
          setIsLoadingMembers(false);
        }
      }
    };

    fetchMembers();
  }, [currentProject]);

  // Fetch current user information
  useEffect(() => {
    const fetchCurrentUser = async () => {
      try {
        const user = await userApi.getCurrentUser();
        setCurrentUser(user);
      } catch (error) {
        console.error('Failed to fetch current user:', error);
      }
    };

    fetchCurrentUser();
  }, []);

  // Fetch conversation when project is loaded
  useEffect(() => {
    const fetchConversation = async () => {
      if (currentProject) {
        console.log('Fetching conversation for project:', currentProject.id);
        console.log('Project ID type:', typeof currentProject.id);
        console.log('Project object:', currentProject);
        try {
          const conversation = await conversationsApi.getProjectConversation(currentProject.id);
          console.log('Successfully fetched conversation:', conversation);
          setCurrentConversation(conversation);
        } catch (error) {
          console.error('Failed to fetch project conversation:', error);
          console.error('Error details:', error instanceof Error ? error.message : String(error));
          
          // If it's an auth error or backend error, show toast
          if (error instanceof Error && 
              (error.message.includes('authentication') || 
               error.message.includes('Backend error') ||
               error.message.includes('Access denied'))) {
            toast({
              variant: "destructive",
              title: "Error",
              description: error.message
            });
          }
          
          setCurrentConversation(null);
        }
      }
    };

    fetchConversation();
  }, [currentProject]);

  // Fetch messages when conversation is available
  useEffect(() => {
    const fetchMessages = async () => {
      if (currentConversation) {
        try {
          setIsLoadingMessages(true);
          const messagesResponse = await conversationsApi.getConversationMessages(
            currentConversation.id,
            { size: 50 } // Get last 50 messages
          );
          
          // Transform backend messages to frontend format
          const transformedMessages: Message[] = (messagesResponse.messages || []).map((msg: MessageResponse) => {
            // Use current user's name if this message was sent by them
            let senderName = msg.sender_name;
            if (!senderName && currentUser && msg.sender_id === currentUser.id) {
              senderName = currentUser.name || currentUser.email || 'You';
            }
            if (!senderName) {
              senderName = 'Unknown User';
            }

            // Ensure we have message content
            const messageContent = msg.content || msg.message;
            
            return {
              id: msg.id,
              senderName,
              senderAvatar: undefined, // No avatar in backend response
              content: messageContent || 'No content',  // Guaranteed to be string
              timestamp: new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              type: msg.message_type === 'text' ? 'text' : msg.message_type as 'image' | 'file',
            };
          });
          
          setMessages(transformedMessages);
        } catch (error) {
          console.error('Failed to fetch messages:', error);
          toast({
            variant: "destructive",
            title: "Error",
            description: "Failed to load messages"
          });
        } finally {
          setIsLoadingMessages(false);
        }
      }
    };

    fetchMessages();
  }, [currentConversation, currentUser, toast]);

  // Event handlers
  const handleAddMember = () => {
    if (!currentProject) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Project not loaded yet"
      });
      return;
    }
    setIsAddMemberDialogOpen(true);
  };

  const handleMemberAdded = async () => {
    if (!currentProject) return;
    
    try {
      setIsLoadingMembers(true);
      const projectMembers = await membersApi.getProjectMembers(currentProject.id);
      
      // Transform to TeamMember format
      const teamMembers: TeamMember[] = projectMembers.map((member: ProjectMember) => ({
        id: member.id,
        name: member.user?.name || 'Unknown User',
        avatar: undefined,
        status: 'offline',
        role: member.role || 'read',
      }));
      
      setMembers(teamMembers);
      toast({
        title: "Success",
        description: "Member added successfully!"
      });
    } catch (error) {
      console.error('Failed to refresh members:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to refresh member list"
      });
    } finally {
      setIsLoadingMembers(false);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!currentProject) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Project not loaded"
      });
      return;
    }

    try {
      // Get conversation if not available yet
      let conversation = currentConversation;
      console.log('Current conversation state:', conversation);
      console.log('Current project ID:', currentProject.id);
      
      if (!conversation) {
        console.log('No conversation found, attempting to get/create one...');
        try {
          conversation = await conversationsApi.getProjectConversation(currentProject.id);
          console.log('Retrieved conversation from API:', conversation);
          setCurrentConversation(conversation);
        } catch (convError) {
          console.error('Failed to get conversation in message send:', convError);
          throw new Error(`Failed to get conversation: ${convError instanceof Error ? convError.message : String(convError)}`);
        }
      }

      if (!conversation) {
        throw new Error('Failed to get conversation - API returned null');
      }
      
      if (!conversation.id) {
        console.error('Conversation object missing ID:', conversation);
        throw new Error('Failed to get valid conversation object - missing ID');
      }
      
      console.log('Using conversation with ID:', conversation.id);


      // Send message
      await conversationsApi.sendMessage(conversation.id, {
        content: message,
        message_type: 'text'
      });

      // Refresh messages after sending
      const messagesResponse = await conversationsApi.getConversationMessages(
        conversation.id,
        { size: 50 }
      );
      
      const transformedMessages: Message[] = (messagesResponse.messages || []).map((msg: MessageResponse) => {
        // Use current user's name if this message was sent by them
        let senderName = msg.sender_name;
        if (!senderName && currentUser && msg.sender_id === currentUser.id) {
          senderName = currentUser.name || currentUser.email || 'You';
        }
        if (!senderName) {
          senderName = 'Unknown User';
        }

        // Ensure we have message content
        const messageContent = msg.content || msg.message;

        return {
          id: msg.id,
          senderName,
          senderAvatar: undefined,
          content: messageContent || 'No content',  // Guaranteed to be string
          timestamp: new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          type: msg.message_type === 'text' ? 'text' : msg.message_type as 'image' | 'file',
        };
      });
      
      setMessages(transformedMessages);
      
    } catch (error) {
      console.error('Failed to send message:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to send message"
      });
    }
  };

  const handleAttachFile = () => {
    console.log("Attach file");
    // In production: open file picker and handle file upload
  };

  const handleAddImage = () => {
    console.log("Add image");
    // In production: open image picker and handle image upload
  };

  const handleNotificationClick = (notificationId: string) => {
    console.log("Notification clicked:", notificationId);
  };

  const handleProjectChange = (projectId: string) => {
    // Find project by ID and navigate to its slug
    projectsApi.getProjects().then(response => {
      const project = response.projects.find((p: any) => p.id === projectId);
      if (project && project.slug) {
        router.push(`/projects/${project.slug}/collaborate`);
      } else if (project) {
        // Fallback to ID if no slug
        router.push(`/projects/${project.id}/collaborate`);
      }
    });
  };

  // Safe avatar generation helper
  const generateAvatarFallback = (members: TeamMember[]): string => {
    if (members.length === 0) return "JS";
    const firstName = members[0]?.name;
    if (!firstName) return "JS";
    
    try {
      return firstName.split(' ').map(n => n[0]).join('').toUpperCase() || "JS";
    } catch (error) {
      console.warn('Error generating avatar fallback:', error);
      return "JS";
    }
  };

  if (isProjectLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading collaboration...</p>
        </div>
      </div>
    );
  }

  if (!currentProject) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-foreground mb-2">Project Not Found</h2>
          <p className="text-muted-foreground mb-4">The requested project could not be found.</p>
          <button 
            onClick={() => router.push('/projects')}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Back to Projects
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex h-full overflow-hidden">
        {/* Left Sidebar */}
        <CollaborateSidebar
          teamMembers={isLoadingMembers ? [] : members}
          onAddMember={handleAddMember}
          maxDisplayMembers={appConfig.features.maxVisibleAvatars}
          title="Collaborate"
          showCalendar={true}
          isLoading={isLoadingMembers}
          selectedSection={selectedSection}
          onSectionChange={setSelectedSection}
        />

        {/* Main Content Area */}
        {selectedSection === 'messages' ? (
          <ChatArea
            messages={messages}
            isLoading={isLoadingMessages}
            onSendMessage={handleSendMessage}
            onAttachFile={handleAttachFile}
            onAddImage={handleAddImage}
          />
        ) : selectedSection === 'journals' ? (
          <JournalsView projectId={currentProject?.id || ''} />
        ) : selectedSection === 'tasks' ? (
          <TasksView projectId={currentProject?.id || ''} />
        ) : (
          <div className="flex-1 flex items-center justify-center bg-card">
            <div className="text-center p-6">
              <h2 className="text-xl font-semibold text-foreground mb-2">Unknown Section</h2>
              <p className="text-muted-foreground">The selected section is not recognized.</p>
            </div>
          </div>
        )}
      </div>

      {/* Add Member Dialog */}
      <AddMemberDialog
        open={isAddMemberDialogOpen}
        onOpenChange={setIsAddMemberDialogOpen}
        projectId={currentProject?.id || ''}
        onMemberAdded={handleMemberAdded}
      />
    </>
  );
} 

export default function ProtectedProjectCollaboratePage() {
  return (
    <ProtectedRoute>
      <ProjectCollaboratePage />
    </ProtectedRoute>
  );
}
