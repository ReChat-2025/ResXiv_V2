import { 
  Sidebar, 
  MagnifyingGlass, 
  ChatCircle,
  ChartLine,
  Plus,
  FilePlus,
  PaperPlaneTilt,
  Copy,
  Sparkle,
  BookOpenText,
  CaretUp,
  CaretDown,
  PencilSimple
} from "@phosphor-icons/react";

export interface PaperItem {
  id: string;
  title: string;
  authors: string[];
  year?: number;
  tags: string[];
  status: 'reading' | 'completed' | 'bookmarked' | 'to-read';
  isSelected?: boolean;
}

export interface ViewMode {
  id: 'chat' | 'graph';
  label: string;
  icon: React.ElementType;
}

export interface PapersTab {
  id: 'chat' | 'insights';
  label: string;
  icon: React.ElementType;
  isActive?: boolean;
}

export interface ActionPill {
  id: string;
  label: string;
  icon: React.ElementType;
  variant: 'primary' | 'secondary';
}

export interface PapersPageConfig {
  title: string;
  searchPlaceholder: string;
  addPapersLabel: string;
  chatPlaceholder: string;
  
  viewModes: ViewMode[];
  tabs: PapersTab[];
  actionPills: ActionPill[];
  
  dimensions: {
    leftSidebar: {
      width: string;
      minWidth: string;
    };
    rightSidebar: {
      width: string;
      minWidth: string;
    };
    header: {
      height: string;
    };
  };
  
  styling: {
    borderRadius: {
      container: string;
      button: string;
      input: string;
      card: string;
      pill: string;
    };
    padding: {
      container: string;
      sidebar: string;
      content: string;
      button: string;
      input: string;
      medium: string;
    };
    gap: {
      small: string;
      medium: string;
      large: string;
      section: string;
    };
    colors: {
      background: string;
      contentBackground: string;
      sidebarBackground: string;
      borderLight: string;
      borderMedium: string;
      borderDark: string;
      textPrimary: string;
      textSecondary: string;
      textMuted: string;
      textLight: string;
      textDisabled: string;
      buttonPrimary: string;
      buttonPrimaryText: string;
      selectedBackground: string;
      shadowLight: string;
    };
    typography: {
      fontFamily: string;
      sizes: {
        small: string;
        medium: string;
        large: string;
        title: string;
      };
      weights: {
        normal: string;
        medium: string;
        semibold: string;
      };
      lineHeights: {
        tight: string;
        normal: string;
        relaxed: string;
      };
    };
  };
  
  icons: {
    sidebar: typeof Sidebar;
    search: typeof MagnifyingGlass;
    chat: typeof ChatCircle;
    graph: typeof ChartLine;
    add: typeof Plus;
    filePlus: typeof FilePlus;
    send: typeof PaperPlaneTilt;
    copy: typeof Copy;
    insights: typeof Sparkle;
    journal: typeof BookOpenText;
    caretUp: typeof CaretUp;
    caretDown: typeof CaretDown;
    cite: typeof PencilSimple;
    size: number;
    weight: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  };
}

export const papersPageConfig: PapersPageConfig = {
  title: "Papers",
  searchPlaceholder: "Search papers...",
  addPapersLabel: "Add Paper",
  chatPlaceholder: "Chat with pdf...",
  
  viewModes: [
    { id: 'chat', label: 'Chat View', icon: ChatCircle },
    { id: 'graph', label: 'Graph View', icon: ChartLine }
  ],
  
  tabs: [
    { id: 'chat', label: 'Chat', icon: ChatCircle, isActive: true },
    { id: 'insights', label: 'Insights', icon: Sparkle, isActive: false }
  ],
  
  actionPills: [
    { id: 'journal', label: 'Add to Journal', icon: BookOpenText, variant: 'secondary' },
    { id: 'copy', label: 'Copy', icon: Copy, variant: 'secondary' }
  ],
  
  dimensions: {
    leftSidebar: {
      width: "286px",
      minWidth: "240px"
    },
    rightSidebar: {
      width: "341px", 
      minWidth: "300px"
    },
    header: {
      height: "56px"
    }
  },
  
  styling: {
    borderRadius: {
      container: "24px",
      button: "12px",
      input: "12px",
      card: "8px",
      pill: "500px"
    },
    padding: {
      container: "24px",
      sidebar: "24px 24px 0px",
      content: "0px",
      button: "12px 20px",
      input: "12px",
      medium: "12px"
    },
    gap: {
      small: "4px",
      medium: "8px",
      large: "12px",
      section: "24px"
    },
    colors: {
      background: "var(--papers-bg-primary)",
      contentBackground: "var(--papers-bg-secondary)",
      sidebarBackground: "var(--papers-sidebar-bg)",
      borderLight: "var(--papers-border-light)",
      borderMedium: "var(--papers-border-medium)",
      borderDark: "var(--papers-border-dark)",
      textPrimary: "var(--papers-text-primary)",
      textSecondary: "var(--papers-text-secondary)",
      textMuted: "var(--papers-text-muted)",
      textLight: "var(--papers-text-light)",
      textDisabled: "var(--papers-text-disabled)",
      buttonPrimary: "var(--papers-button-primary)",
      buttonPrimaryText: "var(--papers-button-primary-text)",
      selectedBackground: "var(--papers-selected-bg)",
      shadowLight: "var(--papers-shadow-light)"
    },
    typography: {
      fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
      sizes: {
        small: "14px",
        medium: "16px",
        large: "18px",
        title: "20px"
      },
      weights: {
        normal: "400",
        medium: "500", 
        semibold: "600"
      },
      lineHeights: {
        tight: "1.4em",
        normal: "1.5em",
        relaxed: "1.75em"
      }
    }
  },
  
  icons: {
    sidebar: Sidebar,
    search: MagnifyingGlass,
    chat: ChatCircle,
    graph: ChartLine,
    add: Plus,
    filePlus: FilePlus,
    send: PaperPlaneTilt,
    copy: Copy,
    insights: Sparkle,
    journal: BookOpenText,
    caretUp: CaretUp,
    caretDown: CaretDown,
    cite: PencilSimple,
    size: 24,
    weight: "light"
  }
};

// Mock data for papers
export const mockPapers: PaperItem[] = [
  {
    id: "1",
    title: "How do sparse expert models compare to dense transformer architectures in real-world inference efficiency?",
    authors: ["Smith, J.", "Johnson, A."],
    year: 2024,
    tags: ["AI", "Transformers"],
    status: "reading",
    isSelected: true
  },
  {
    id: "2", 
    title: "Emergent abilities in LLMs: artifact or scaling law?",
    authors: ["Brown, K.", "Davis, L."],
    year: 2024,
    tags: ["LLM", "Scaling"],
    status: "completed"
  },
  {
    id: "3",
    title: "Ethics-Driven Latent Space Embeddings for Bias Mitigation",
    authors: ["Wilson, R.", "Garcia, M."],
    year: 2023,
    tags: ["Ethics", "Bias"],
    status: "reading"
  },
  {
    id: "4",
    title: "A Comparative Study of Training Methodologies for Neural Networks",
    authors: ["Chen, X.", "Kumar, S."],
    year: 2023,
    tags: ["Training", "Neural Networks"],
    status: "to-read"
  },
  {
    id: "5",
    title: "Beyond Explainability: Emergent Properties in Large-Scale AI Systems",
    authors: ["Taylor, E.", "Anderson, P."],
    year: 2024,
    tags: ["Explainability", "AI Systems"],
    status: "reading"
  }
];

// Helper functions
export const getPaperCount = (papers: PaperItem[]): string => {
  const count = papers.length;
  return `${count} ${count === 1 ? 'paper' : 'papers'}`;
};

export const getSelectedPaper = (papers: PaperItem[]): PaperItem | null => {
  return papers.find(paper => paper.isSelected) || null;
};

export const formatAuthors = (authors: string[], maxAuthors: number = 2): string => {
  if (authors.length <= maxAuthors) {
    return authors.join(", ");
  }
  return `${authors.slice(0, maxAuthors).join(", ")} et al.`;
};

export default papersPageConfig; 