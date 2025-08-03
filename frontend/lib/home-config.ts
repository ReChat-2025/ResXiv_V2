// Home page configuration for scalable, production-ready chat interface
// All content can be easily customized for different deployments

export interface ChatMessage {
  id: string;
  content: string;
  timestamp: Date;
  type: 'user' | 'assistant';
}

export interface Conversation {
  id: string;
  title: string;
  lastMessage: string;
  preview: string;
  timestamp: Date;
  messages: ChatMessage[];
}

export interface HomePageConfig {
  greeting: {
    title: string;
    subtitle: string;
  };
  sidebar: {
    title: string;
    searchPlaceholder: string;
    newChatText: string;
    collapsible: boolean;
  };
  chat: {
    inputPlaceholder: string;
    sendButtonText: string;
    actions: ChatAction[];
  };
  chatActions: ChatAction[];
  inputActions: InputAction[];
  navigation: {
    items: NavItem[];
  };
}

export interface ChatAction {
  id: string;
  label: string;
  iconName: string;
  description?: string;
}

export interface InputAction {
  id: string;
  label: string;
  iconName: string;
  description?: string;
}

export interface NavItem {
  id: string;
  label: string;
  iconName: string;
  href: string;
  active?: boolean;
}

// Mock conversation data for production-ready structure
const mockConversations: Conversation[] = [
  {
    id: "1",
    title: "How do sparse expert models compare to dense transformer architectures in real-world inference efficiency?",
    lastMessage: "Great question! Let me analyze the latest research on sparse expert models...",
    preview: "Great question! Let me analyze the latest research on sparse expert models...",
    timestamp: new Date(),
    messages: []
  },
  {
    id: "2", 
    title: "Emergent abilities in LLMs: artifact or scaling law?",
    lastMessage: "This is a fascinating topic in current AI research...",
    preview: "This is a fascinating topic in current AI research...",
    timestamp: new Date(),
    messages: []
  },
  {
    id: "3",
    title: "Prompt engineering vs. architectural tuning — long-term tradeoffs?",
    lastMessage: "Both approaches have their merits and specific use cases...",
    preview: "Both approaches have their merits and specific use cases...",
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // Yesterday
    messages: []
  },
  {
    id: "4",
    title: "Trust calibration in LLM outputs: what works beyond confidence scores?",
    lastMessage: "Confidence scoring is just one approach to trust calibration...",
    preview: "Confidence scoring is just one approach to trust calibration...",
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // Yesterday
    messages: []
  },
  {
    id: "5",
    title: "Can LLMs develop theory of mind, or is it all illusion?",
    lastMessage: "Theory of mind in AI systems is a complex philosophical question...",
    preview: "Theory of mind in AI systems is a complex philosophical question...",
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // Yesterday
    messages: []
  },
  {
    id: "6",
    title: "Latest interpretability methods for tracing LLM decision paths",
    lastMessage: "Several new interpretability techniques have emerged recently...",
    preview: "Several new interpretability techniques have emerged recently...",
    timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
    messages: []
  }
];

// Main home page configuration
export const homeConfig: HomePageConfig = {
  greeting: {
    title: "Hello, James!",
    subtitle: "What do you want to learn today?"
  },
  
  sidebar: {
    title: "Past Conversations",
    searchPlaceholder: "Search papers",
    newChatText: "New Chat",
    collapsible: true
  },

  chat: {
    inputPlaceholder: "Ask me anything...",
    sendButtonText: "Send",
    actions: [
      {
        id: "media",
        label: "Media",
        iconName: "Image",
        description: "Upload images or files"
      },
      {
        id: "tag-papers",
        label: "Tag papers",
        iconName: "Tag", 
        description: "Tag and organize papers"
      },
      {
        id: "attach-pdf",
        label: "Attach pdf",
        iconName: "Paperclip",
        description: "Attach PDF documents"
      }
    ]
  },

  chatActions: [
    {
      id: "analyze-paper",
      label: "Analyze Paper",
      iconName: "FileText",
      description: "Analyze research papers"
    },
    {
      id: "write-summary",
      label: "Write Summary",
      iconName: "PencilSimple",
      description: "Generate paper summaries"
    },
    {
      id: "find-references",
      label: "Find References",
      iconName: "MagnifyingGlass",
      description: "Find relevant references"
    },
    {
      id: "collaboration",
      label: "Collaborate",
      iconName: "Users",
      description: "Work with team members"
    }
  ],

  inputActions: [
    {
      id: "media",
      label: "Media",
      iconName: "Image",
      description: "Upload images or files"
    },
    {
      id: "tag-papers",
      label: "Tag papers",
      iconName: "At",
      description: "Tag and organize papers"  
    },
    {
      id: "attach-pdf",
      label: "Attach pdf",
      iconName: "Paperclip",
      description: "Attach PDF documents"
    }
  ],

  navigation: {
    items: [
      {
        id: "home",
        label: "Home",
        iconName: "House",
        href: "/home",
        active: true
      },
      {
        id: "papers",
        label: "Papers",
        iconName: "FileText",
        href: "/papers"
      },
      {
        id: "draft",
        label: "Draft",
        iconName: "PencilSimple",
        href: "/draft"
      },
      {
        id: "collaborate",
        label: "Collaborate",
        iconName: "Users",
        href: "/collaborate"
      },
      {
        id: "settings",
        label: "Settings",
        iconName: "Gear",
        href: "/settings"
      }
    ]
  }
};

// Helper function to get greeting based on time of day and user
export const getGreeting = (userName: string = "User"): string => {
  const hour = new Date().getHours();
  let timeGreeting = "";
  
  if (hour < 12) timeGreeting = "Good morning";
  else if (hour < 18) timeGreeting = "Good afternoon"; 
  else timeGreeting = "Good evening";
  
  return `Hello, ${userName}!`;
};

// Helper function to group conversations by date
export const groupConversationsByDate = (conversations: Conversation[]): Record<string, Conversation[]> => {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  
  const groups: Record<string, Conversation[]> = {
    "Today": [],
    "Yesterday": [],
    "2 days ago": [],
    "Older": []
  };

  conversations.forEach(conversation => {
    const messageDate = new Date(conversation.timestamp);
    const diffTime = today.getTime() - messageDate.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      groups["Today"].push(conversation);
    } else if (diffDays === 1) {
      groups["Yesterday"].push(conversation);
    } else if (diffDays === 2) {
      groups["2 days ago"].push(conversation);
    } else {
      groups["Older"].push(conversation);
    }
  });

  return groups;
};

// Helper function to format conversation timestamps
export const formatTimestamp = (timestamp: Date): string => {
  const now = new Date();
  const diff = now.getTime() - timestamp.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  
  return timestamp.toLocaleDateString();
};

// Helper function to generate conversation preview
export const generateConversationPreview = (messages: ChatMessage[]): string => {
  if (messages.length === 0) return "No messages yet";
  const lastMessage = messages[messages.length - 1];
  return lastMessage.content.length > 100 
    ? lastMessage.content.substring(0, 100) + "..."
    : lastMessage.content;
};

// Get mock conversations for development
export const getMockConversations = (): Conversation[] => {
  return mockConversations;
};

// Get user name from environment or default
export const getUserName = (): string => {
  return process.env.NEXT_PUBLIC_USER_NAME || "James";
}; 