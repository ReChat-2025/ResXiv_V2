// Papers page configuration for scalable, production-ready paper management
// All content can be easily customized for different deployments

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract?: string;
  year?: number;
  venue?: string;
  url?: string;
  pdfUrl?: string;
  tags: string[];
  dateAdded: Date;
  lastViewed?: Date;
  status: PaperStatus;
  isSelected?: boolean;
}

export type PaperStatus = 'unread' | 'reading' | 'read' | 'archived';
export type PaperView = 'chat' | 'graph' | 'insights';

export interface PapersPageConfig {
  title: string;
  sidebar: {
    title: string;
    addButtonText: string;
    searchPlaceholder: string;
    paperCount: string;
    collapsible: boolean;
  };
  paperViewer: {
    controls: {
      languages: LanguageOption[];
      defaultLanguage: string;
      zoomLevels: string[];
      defaultZoom: string;
      pagination: {
        format: string; // e.g., "{current} of {total} pages"
      };
    };
    actions: PaperAction[];
    tabs: PaperTab[];
  };
  chat: {
    title: string;
    subtitle: string;
    placeholder: string;
    suggestedQuestions: string[];
    actions: ChatActionButton[];
  };
}

export interface LanguageOption {
  id: string;
  label: string;
  code: string;
}

export interface PaperAction {
  id: string;
  label: string;
  iconName: string;
  variant?: string;
}

export interface PaperTab {
  id: string;
  label: string;
  iconName: string;
  active?: boolean;
}

export interface ChatActionButton {
  id: string;
  label: string;
  iconName: string;
  variant?: string;
}

// Mock papers data matching Figma design
const mockPapers: Paper[] = [
  {
    id: "1",
    title: "Reinforcement Learning with Multi-Agent Emotional Bias Simulation",
    authors: ["Dr. Sarah Chen", "Prof. Michael Rodriguez", "Dr. Anna Kim"],
    abstract: "This paper introduces a novel framework where multiple AI agents are trained using reinforcement learning (RL), but with an added layer of emotional bias simulation...",
    year: 2024,
    venue: "Nature Machine Intelligence",
    tags: ["Reinforcement Learning", "Multi-Agent Systems", "Emotional AI"],
    dateAdded: new Date(),
    status: "reading",
    isSelected: true
  },
  {
    id: "2",
    title: "Zero-Shot Prompt Tuning in Multilingual Generative Models",
    authors: ["Dr. Elena Kowalski", "Prof. James Thompson"],
    abstract: "We present a comprehensive study on zero-shot prompt engineering techniques...",
    year: 2024,
    venue: "ACL 2024",
    tags: ["NLP", "Prompt Engineering", "Multilingual"],
    dateAdded: new Date(),
    status: "unread"
  },
  {
    id: "3",
    title: "Ethics-Driven Latent Space Navigation in Diffusion Models",
    authors: ["Dr. Alex Petrov", "Dr. Maria Garcia"],
    abstract: "This work explores ethical considerations in diffusion model generation...",
    year: 2024,
    venue: "ICML 2024",
    tags: ["Ethics", "Diffusion Models", "AI Safety"],
    dateAdded: new Date(),
    status: "unread"
  },
  {
    id: "4",
    title: "A Comparative Study of Transformer-Based Models on Real-World Noise Data",
    authors: ["Prof. David Liu", "Dr. Sophie Martin"],
    abstract: "We analyze the performance of various transformer architectures...",
    year: 2024,
    venue: "ICLR 2024",
    tags: ["Transformers", "Robustness", "Noise"],
    dateAdded: new Date(),
    status: "unread"
  },
  {
    id: "5",
    title: "Beyond Explainability: Emergent Behaviors in Self-Correcting AI Systems",
    authors: ["Dr. John Anderson", "Prof. Lisa Wong"],
    abstract: "This paper investigates emergent behaviors in self-correcting AI systems...",
    year: 2024,
    venue: "AAAI 2024",
    tags: ["Explainability", "Self-Correction", "Emergent Behavior"],
    dateAdded: new Date(),
    status: "unread"
  }
];

// Main papers page configuration
export const papersConfig: PapersPageConfig = {
  title: "Papers",
  
  sidebar: {
    title: "Papers",
    addButtonText: "Add Papers",
    searchPlaceholder: "Search papers...",
    paperCount: "5 papers",
    collapsible: true
  },

  paperViewer: {
    controls: {
      languages: [
        { id: "en", label: "English", code: "en" },
        { id: "es", label: "Spanish", code: "es" },
        { id: "fr", label: "French", code: "fr" },
        { id: "de", label: "German", code: "de" },
        { id: "zh", label: "Chinese", code: "zh" }
      ],
      defaultLanguage: "English",
      zoomLevels: ["50%", "75%", "100%", "125%", "150%", "200%"],
      defaultZoom: "100%",
      pagination: {
        format: "{current} of {total} pages"
      }
    },
    actions: [
      {
        id: "cite",
        label: "Cite",
        iconName: "PencilSimple",
        variant: "default"
      }
    ],
    tabs: [
      {
        id: "chat",
        label: "Chat",
        iconName: "ChatCircle",
        active: true
      },
      {
        id: "insights",
        label: "Insights",
        iconName: "Sparkle",
        active: false
      }
    ]
  },

  chat: {
    title: "What is discussed in this paper?",
    subtitle: "This paper introduces a novel framework where multiple AI agents are trained using reinforcement learning (RL), but with an added layer of emotional bias simulation. The goal is to explore how modeling human-like emotional tendencies—such as risk aversion, trust, envy, or optimism—affects the learning strategies, cooperation, and competition between agents.",
    placeholder: "Chat with pdf...",
    suggestedQuestions: [
      "What is the main contribution of this paper?",
      "How does emotional bias affect agent behavior?",
      "What are the experimental results?",
      "How does this compare to previous work?"
    ],
    actions: [
      {
        id: "add-to-journal",
        label: "Add to Journal",
        iconName: "Plus",
        variant: "secondary"
      },
      {
        id: "copy",
        label: "Copy",
        iconName: "Copy",
        variant: "secondary"
      }
    ]
  }
};

// Helper function to format paper count
export const formatPaperCount = (count: number): string => {
  if (count === 0) return "No papers";
  if (count === 1) return "1 paper";
  return `${count} papers`;
};

// Helper function to generate paper preview
export const generatePaperPreview = (title: string, maxLength: number = 100): string => {
  if (title.length <= maxLength) return title;
  return title.substring(0, maxLength).trim() + "...";
};

// Helper function to get mock papers
export const getMockPapers = (): Paper[] => {
  return mockPapers;
};

// Helper function to get selected paper
export const getSelectedPaper = (): Paper | null => {
  return mockPapers.find(paper => paper.isSelected) || null;
};

// Helper function to format author names
export const formatAuthors = (authors: string[], maxAuthors: number = 3): string => {
  if (authors.length <= maxAuthors) {
    return authors.join(", ");
  }
  return `${authors.slice(0, maxAuthors).join(", ")} et al.`;
};

// Helper function to get paper by ID
export const getPaperById = (id: string): Paper | undefined => {
  return mockPapers.find(paper => paper.id === id);
};

// Helper function to update paper selection
export const updatePaperSelection = (paperId: string): Paper[] => {
  return mockPapers.map(paper => ({
    ...paper,
    isSelected: paper.id === paperId
  }));
};

// Helper function to format pagination
export const formatPagination = (current: number, total: number): string => {
  return papersConfig.paperViewer.controls.pagination.format
    .replace("{current}", current.toString())
    .replace("{total}", total.toString());
};

// Helper function to validate paper data
export const validatePaper = (paper: Partial<Paper>): boolean => {
  return !!(paper.title && paper.authors && paper.authors.length > 0);
};

// Helper function to get papers by status
export const getPapersByStatus = (status: PaperStatus): Paper[] => {
  return mockPapers.filter(paper => paper.status === status);
};

// Helper function to search papers
export const searchPapers = (query: string): Paper[] => {
  if (!query.trim()) return mockPapers;
  
  const lowercaseQuery = query.toLowerCase();
  return mockPapers.filter(paper => 
    paper.title.toLowerCase().includes(lowercaseQuery) ||
    paper.authors.some(author => author.toLowerCase().includes(lowercaseQuery)) ||
    paper.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery)) ||
    (paper.abstract && paper.abstract.toLowerCase().includes(lowercaseQuery))
  );
}; 