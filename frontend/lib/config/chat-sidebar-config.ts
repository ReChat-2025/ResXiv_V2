import { 
  Sidebar, 
  MagnifyingGlass, 
  ChatCircle 
} from "@phosphor-icons/react";

export interface ConversationItem {
  id: string;
  title: string;
  timestamp: string;
  isSelected?: boolean;
}

export interface ConversationGroup {
  label: string;
  conversations: ConversationItem[];
}

export interface ChatSidebarConfig {
  title: string;
  searchPlaceholder: string;
  newChatLabel: string;
  dimensions: {
    expanded: {
      width: string;
      height: string;
    };
    collapsed: {
      width: string;
      height: string;
    };
  };
  styling: {
    padding: string;
    gap: string;
    colors: {
      background: string;
      border: string;
      text: string;
      textSecondary: string;
      textMuted: string;
      divider: string;
      buttonPrimary: string;
      buttonPrimaryHover: string;
      buttonSecondary: string;
      buttonSecondaryHover: string;
      conversationItem: string;
      conversationItemHover: string;
      conversationItemSelected: string;
      conversationItemSelectedHover: string;
    };
    typography: {
      fontFamily: string;
      title: {
        fontWeight: string;
        fontSize: string;
        lineHeight: string;
      };
      body: {
        fontWeight: string;
        fontSize: string;
        lineHeight: string;
      };
      label: {
        fontWeight: string;
        fontSize: string;
        lineHeight: string;
      };
    };
    spacing: {
      sectionGap: string;
      itemGap: string;
      buttonGap: string;
      headerGap: string;
      headerPadding: string;
      buttonPadding: string;
      itemPadding: string;
      labelPadding: string;
      outerPadding: string;
    };
    borderRadius: {
      container: string;
      button: string;
      conversationItem: string;
    };
    layout: {
      titleWidth: string;
      titleHeight: string;
      buttonHeight: string;
      maxTextLines: number;
    };
  };
  icons: {
    sidebar: typeof Sidebar;
    search: typeof MagnifyingGlass;
    newChat: typeof ChatCircle;
    size: number;
    weight: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  };
}

export const chatSidebarConfig: ChatSidebarConfig = {
  title: "Past Conversations",
  searchPlaceholder: "Search",
  newChatLabel: "New Chat",
  
  dimensions: {
    expanded: {
      width: "302px",
      height: "752px"
    },
    collapsed: {
      width: "64px", 
      height: "752px"
    }
  },

  styling: {
    padding: "24px 16px 0px",
    gap: "28px",
    
    colors: {
      background: "#EFEFED",        // Figma: fill_VMELNQ
      border: "#E7E7E7",            // Figma: stroke_ORJVL4
      text: "#0D0D0D",              // Figma: fill_HMUBZX
      textSecondary: "#737373",     // Figma: fill_BRXQJO/stroke_K1S9QE 
      textMuted: "#8C8C8C",         // Figma: fill_L13KAJ
      divider: "#E6E6E6",           // Figma: fill_DVGVVZ
      buttonPrimary: "#0D0D0D",     // Dark button background
      buttonPrimaryHover: "#262626", // Darker on hover
      buttonSecondary: "transparent", // Search button background (transparent)
      buttonSecondaryHover: "#F5F5F5", // Light hover
      conversationItem: "transparent",   // Unselected items - transparent
      conversationItemHover: "#F0F0F0", // Light hover for unselected
      conversationItemSelected: "#E7E5E3", // Figma: fill_EMOB1O - only for selected
      conversationItemSelectedHover: "#D9D7D4", // Selected hover
    },

    typography: {
      fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
      title: {
        fontWeight: "600",          // Figma: style_NY5R3B
        fontSize: "16px",
        lineHeight: "1.75em"
      },
      body: {
        fontWeight: "400",          // Figma: style_TJ18QJ
        fontSize: "16px",
        lineHeight: "1.75em"
      },
      label: {
        fontWeight: "700",          // Figma: style_84Z42Y
        fontSize: "14px", 
        lineHeight: "1.4285714285714286em"
      }
    },

    spacing: {
      sectionGap: "28px",          // Main container gap - Figma layout_XGTC0L
      itemGap: "4px",              // Between conversation groups - Figma layout_L8XRN8
      buttonGap: "12px",           // Increased spacing between action buttons
      headerGap: "24px",           // Increased gap between header and buttons
      headerPadding: "0px 8px",    // Header padding
      buttonPadding: "12px 8px",   // Button padding - Figma layout_DTX5DZ
      itemPadding: "8px",          // Conversation item padding - Figma layout_8VHKTL
      labelPadding: "0px 8px",     // Group label padding - Figma layout_PA3C5Z
      outerPadding: "16px 0px 0px 16px", // Padding around the entire sidebar
    },

    borderRadius: {
      container: "24px 24px 0px 0px", // Main container - Figma borderRadius
      button: "12px",                  // Action buttons - Figma borderRadius  
      conversationItem: "8px"          // Conversation items - Figma borderRadius
    },

    // Layout constraints from Figma
    layout: {
      titleWidth: "174px",         // Figma: width 174 for Past Conversations
      titleHeight: "37px",         // Figma: height 37 for Past Conversations
      buttonHeight: "48px",        // Standard button height
      maxTextLines: 1              // Single line text only
    }
  },

  icons: {
    sidebar: Sidebar,
    search: MagnifyingGlass,
    newChat: ChatCircle,
    size: 24,
    weight: "light"
  }
};

// Default conversation data matching Figma design
export const defaultConversations: ConversationGroup[] = [
  {
    label: "Today",
    conversations: [
      {
        id: "conv-1",
        title: "How do sparse expert models compare to dense transformer architectures in real-world inference efficiency?",
        timestamp: "Today",
      },
      {
        id: "conv-2", 
        title: "Emergent abilities in LLMs: artifact or scaling law?",
        timestamp: "Today",
      }
    ]
  },
  {
    label: "Yesterday", 
    conversations: [
      {
        id: "conv-3",
        title: "Prompt engineering vs. architectural tuning — long-term tradeoffs?",
        timestamp: "Yesterday",
      },
      {
        id: "conv-4",
        title: "Trust calibration in LLM outputs: what works beyond confidence scores?",
        timestamp: "Yesterday",
      }
    ]
  },
  {
    label: "2 Days Ago",
    conversations: [
      {
        id: "conv-5", 
        title: "Can LLMs develop theory of mind, or is it all illusion?",
        timestamp: "2 days ago",
      },
      {
        id: "conv-6",
        title: "Latest interpretability methods for mapping LLM decision paths",
        timestamp: "2 days ago",
      }
    ]
  }
];

// Helper functions for conversation management
export const groupConversationsByDate = (conversations: ConversationItem[]): ConversationGroup[] => {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  
  const groups: { [key: string]: ConversationItem[] } = {
    "Today": [],
    "Yesterday": [],
    "2 Days Ago": [],
    "Older": []
  };

  conversations.forEach(conv => {
    const convDate = new Date(conv.timestamp);
    const diffTime = Math.abs(today.getTime() - convDate.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      groups["Today"].push(conv);
    } else if (diffDays === 1) {
      groups["Yesterday"].push(conv);
    } else if (diffDays === 2) {
      groups["2 Days Ago"].push(conv);
    } else {
      groups["Older"].push(conv);
    }
  });

  return Object.entries(groups)
    .filter(([_, convs]) => convs.length > 0)
    .map(([label, conversations]) => ({ label, conversations }));
};

export const searchConversations = (
  conversations: ConversationGroup[], 
  query: string
): ConversationGroup[] => {
  if (!query.trim()) return conversations;
  
  const filteredGroups = conversations.map(group => ({
    ...group,
    conversations: group.conversations.filter(conv =>
      conv.title.toLowerCase().includes(query.toLowerCase())
    )
  })).filter(group => group.conversations.length > 0);

  return filteredGroups;
};

export const getConversationById = (
  conversations: ConversationGroup[], 
  id: string
): ConversationItem | null => {
  for (const group of conversations) {
    const conversation = group.conversations.find(conv => conv.id === id);
    if (conversation) return conversation;
  }
  return null;
};

export default chatSidebarConfig; 