// Data Configuration for all app content
// This file centralizes all mock data and data structures

export interface Journal {
  id: string;
  title: string;
  content: string;
  timestamp: string;
  privacy: 'private' | 'public' | 'shared';
  author: string;
  authorId: string;
  tags?: string[];
  lastModified: string;
  wordCount?: number;
}

export interface Task {
  id: string;
  name: string;
  description?: string;
  status: 'not_started' | 'in_progress' | 'done' | 'cancelled';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  assignees: TaskAssignee[];
  dueDate: string;
  timeRange?: string;
  createdAt: string;
  updatedAt: string;
  projectId: string;
  tags?: string[];
  estimatedHours?: number;
  actualHours?: number;
}

export interface TaskAssignee {
  id: string;
  name: string;
  avatar?: string;
  fallback: string;
  role?: string;
}

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  content: string;
  venue?: string;
  year: number;
  doi?: string;
  url?: string;
  tags: string[];
  status: 'draft' | 'submitted' | 'under_review' | 'accepted' | 'published';
  createdAt: string;
  updatedAt: string;
  collaborators: string[];
  citations?: number;
}

export interface Message {
  id: string;
  senderName: string;
  senderId: string;
  senderAvatar?: string;
  content: string;
  timestamp: string;
  type: 'text' | 'image' | 'file' | 'system';
  attachments?: Attachment[];
  reactions?: Reaction[];
  isEdited?: boolean;
  replyTo?: string;
}

export interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url: string;
}

export interface Reaction {
  emoji: string;
  users: string[];
  count: number;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: string;
  read: boolean;
  actionUrl?: string;
  userId: string;
}

// Mock Journals Data
export const mockJournals: Journal[] = [
  {
    id: "1",
    title: "Research Methodology Deep Dive",
    content: "Today I explored various research methodologies for data collection. The mixed-methods approach seems most suitable for our current project as it combines quantitative data analysis with qualitative insights from interviews. Key findings include...",
    timestamp: "Today, 2:45 pm",
    privacy: "private",
    author: "John Smith",
    authorId: "1",
    tags: ["methodology", "research", "data-collection"],
    lastModified: new Date().toISOString(),
    wordCount: 245
  },
  {
    id: "2", 
    title: "Literature Review Progress",
    content: "Completed reviewing 15 more papers related to machine learning applications in healthcare. Notable patterns emerging around ethical considerations and bias mitigation strategies. Need to explore the regulatory frameworks more deeply...",
    timestamp: "Yesterday, 2:45 pm",
    privacy: "shared",
    author: "Sarah Johnson",
    authorId: "2",
    tags: ["literature-review", "machine-learning", "healthcare"],
    lastModified: new Date(Date.now() - 86400000).toISOString(),
    wordCount: 189
  },
  {
    id: "3",
    title: "Experimental Design Considerations",
    content: "Working on refining the experimental protocol. The control groups need to be more carefully defined to ensure statistical validity. Considering a randomized controlled trial approach with stratified sampling...",
    timestamp: "2 days ago, 10:30 am",
    privacy: "public",
    author: "Mike Chen",
    authorId: "3",
    tags: ["experimental-design", "statistics", "protocol"],
    lastModified: new Date(Date.now() - 172800000).toISOString(),
    wordCount: 156
  }
];

// Mock Tasks Data
export const mockTasks: Task[] = [
  {
    id: "1",
    name: "Analyse Survey Data",
    description: "Statistical analysis of user survey responses using SPSS and R",
    status: "not_started",
    priority: "high",
    assignees: [
      { id: "1", name: "John Smith", fallback: "JS", role: "Lead Analyst" },
      { id: "2", name: "Sarah Johnson", fallback: "SJ", role: "Statistician" },
      { id: "3", name: "Mike Chen", fallback: "MC", role: "Data Scientist" }
    ],
    dueDate: "18 May 2025",
    timeRange: "3:00 pm - 3:30 pm",
    createdAt: "2024-12-01",
    updatedAt: new Date().toISOString(),
    projectId: "1",
    tags: ["analysis", "survey", "statistics"],
    estimatedHours: 8,
    actualHours: 0
  },
  {
    id: "2",
    name: "Design User Interface",
    description: "Create wireframes and prototypes for the research platform",
    status: "cancelled",
    priority: "medium",
    assignees: [
      { id: "1", name: "John Smith", fallback: "JS", role: "UX Designer" },
      { id: "2", name: "Sarah Johnson", fallback: "SJ", role: "UI Designer" },
      { id: "3", name: "Mike Chen", fallback: "MC", role: "Developer" },
      ...Array.from({ length: 12 }, (_, i) => ({
        id: `designer-${i}`,
        name: `Designer ${i}`,
        fallback: "D",
        role: "Designer"
      }))
    ],
    dueDate: "17 May 2025",
    timeRange: "-",
    createdAt: "2024-11-15",
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    projectId: "1",
    tags: ["design", "ui", "wireframes"],
    estimatedHours: 16,
    actualHours: 8
  },
  {
    id: "3",
    name: "Develop Backend API",
    description: "Build RESTful API for data management and user authentication",
    status: "in_progress",
    priority: "urgent",
    assignees: [
      { id: "1", name: "John Smith", fallback: "JS", role: "Tech Lead" },
      { id: "2", name: "Sarah Johnson", fallback: "SJ", role: "Backend Dev" },
      { id: "3", name: "Mike Chen", fallback: "MC", role: "Full Stack Dev" },
      ...Array.from({ length: 5 }, (_, i) => ({
        id: `dev-${i}`,
        name: `Developer ${i}`,
        fallback: "D",
        role: "Developer"
      }))
    ],
    dueDate: "16 May 2025",
    timeRange: "1:50 pm - 3:00 pm",
    createdAt: "2024-11-01",
    updatedAt: new Date(Date.now() - 3600000).toISOString(),
    projectId: "1",
    tags: ["development", "backend", "api"],
    estimatedHours: 40,
    actualHours: 25
  },
  {
    id: "4",
    name: "AI/ML Model Training",
    description: "Train and validate machine learning models for data prediction",
    status: "not_started",
    priority: "high",
    assignees: [
      { id: "4", name: "Alice Brown", fallback: "AB", role: "ML Engineer" },
      { id: "5", name: "David Wilson", fallback: "DW", role: "Data Scientist" }
    ],
    dueDate: "15 May 2025",
    timeRange: "3:00 pm - 3:30 pm",
    createdAt: "2024-12-05",
    updatedAt: new Date(Date.now() - 7200000).toISOString(),
    projectId: "1",
    tags: ["ai", "machine-learning", "training"],
    estimatedHours: 32,
    actualHours: 0
  },
  {
    id: "5",
    name: "Market Analysis Research",
    description: "Comprehensive analysis of target market and competitor landscape",
    status: "done",
    priority: "medium",
    assignees: [
      { id: "1", name: "John Smith", fallback: "JS", role: "Research Lead" },
      { id: "2", name: "Sarah Johnson", fallback: "SJ", role: "Market Analyst" },
      { id: "3", name: "Mike Chen", fallback: "MC", role: "Business Analyst" },
      ...Array.from({ length: 30 }, (_, i) => ({
        id: `analyst-${i}`,
        name: `Analyst ${i}`,
        fallback: "A",
        role: "Market Researcher"
      }))
    ],
    dueDate: "14 May 2025",
    timeRange: "-",
    createdAt: "2024-10-15",
    updatedAt: new Date(Date.now() - 172800000).toISOString(),
    projectId: "1",
    tags: ["market-research", "analysis", "business"],
    estimatedHours: 24,
    actualHours: 28
  }
];

// Mock Papers Data  
export const mockPapers: Paper[] = [
  {
    id: "1",
    title: "Advanced Machine Learning Techniques in Healthcare Data Analysis",
    authors: ["John Smith", "Sarah Johnson", "Mike Chen"],
    abstract: "This paper presents novel machine learning approaches for analyzing complex healthcare datasets. We introduce a hybrid methodology combining deep learning with traditional statistical methods to improve prediction accuracy while maintaining interpretability.",
    content: "## Introduction\n\nHealthcare data analysis has become increasingly complex...\n\n## Methodology\n\nOur approach combines several key components...",
    venue: "Journal of Medical Informatics",
    year: 2024,
    doi: "10.1000/xyz123",
    url: "https://example.com/paper1",
    tags: ["machine-learning", "healthcare", "data-analysis"],
    status: "under_review",
    createdAt: "2024-01-15",
    updatedAt: new Date().toISOString(),
    collaborators: ["1", "2", "3"],
    citations: 0
  },
  {
    id: "2",
    title: "Ethical Considerations in AI Research: A Comprehensive Framework",
    authors: ["Alice Brown", "David Wilson"],
    abstract: "As artificial intelligence continues to transform research methodologies, ensuring ethical practices becomes paramount. This paper proposes a comprehensive framework for ethical AI research.",
    content: "## Abstract\n\nThe rapid advancement of AI technologies...\n\n## Ethical Framework\n\nOur proposed framework consists of four key pillars...",
    venue: "Ethics in Technology Conference",
    year: 2024,
    doi: "10.1000/eth456",
    tags: ["ethics", "ai", "research-methodology"],
    status: "published",
    createdAt: "2024-02-01",
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    collaborators: ["4", "5"],
    citations: 12
  }
];

// Mock Messages Data
export const mockMessages: Message[] = [
  {
    id: "1",
    senderName: "John Smith",
    senderId: "1",
    content: "Hey team! I've uploaded the latest research findings to the shared folder. Please review and let me know your thoughts.",
    timestamp: "10:30 AM",
    type: "text"
  },
  {
    id: "2",
    senderName: "Sarah Johnson", 
    senderId: "2",
    content: "Thanks John! I'll review it this afternoon. The preliminary data looks promising.",
    timestamp: "10:35 AM",
    type: "text"
  },
  {
    id: "3",
    senderName: "Mike Chen",
    senderId: "3", 
    content: "Great work! I've added some statistical analysis notes. Should we schedule a meeting to discuss next steps?",
    timestamp: "10:45 AM",
    type: "text"
  },
  {
    id: "4",
    senderName: "Alice Brown",
    senderId: "4",
    content: "I can join the meeting. How about Thursday at 2 PM?",
    timestamp: "11:00 AM", 
    type: "text"
  }
];

// Mock Notifications Data
export const mockNotifications: Notification[] = [
  {
    id: "1",
    title: "New Task Assigned",
    message: "You have been assigned to 'Analyse Survey Data'",
    type: "info",
    timestamp: new Date().toISOString(),
    read: false,
    actionUrl: "/tasks",
    userId: "1"
  },
  {
    id: "2",
    title: "Paper Review Complete", 
    message: "Your paper review has been completed by Dr. Smith",
    type: "success",
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    read: false,
    actionUrl: "/papers",
    userId: "1"
  },
  {
    id: "3",
    title: "Meeting Reminder",
    message: "Team meeting starts in 30 minutes",
    type: "warning", 
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    read: true,
    actionUrl: "/collaborate",
    userId: "1"
  }
];

// Utility functions for data manipulation
export const getJournalsByAuthor = (authorId: string): Journal[] => {
  return mockJournals.filter(journal => journal.authorId === authorId);
};

export const getTasksByAssignee = (assigneeId: string): Task[] => {
  return mockTasks.filter(task => 
    task.assignees.some(assignee => assignee.id === assigneeId)
  );
};

export const getTasksByStatus = (status: Task['status']): Task[] => {
  return mockTasks.filter(task => task.status === status);
};

export const getPapersByCollaborator = (collaboratorId: string): Paper[] => {
  return mockPapers.filter(paper => 
    paper.collaborators.includes(collaboratorId)
  );
};

export const getUnreadNotifications = (userId: string): Notification[] => {
  return mockNotifications.filter(notification => 
    notification.userId === userId && !notification.read
  );
};

export const getMessagesByTimestamp = (messages: Message[]): Message[] => {
  return [...messages].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
};

// Data generation utilities
export const generateTaskAssignees = (count: number, baseAssignees: TaskAssignee[] = []): TaskAssignee[] => {
  const additionalAssignees = Array.from({ length: count }, (_, i) => ({
    id: `generated-${i}`,
    name: `Team Member ${i + 1}`,
    fallback: `T${i + 1}`,
    role: "Collaborator"
  }));
  
  return [...baseAssignees, ...additionalAssignees];
};

export const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  
  return date.toLocaleDateString();
}; 