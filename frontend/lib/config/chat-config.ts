// Chat Configuration
// Centralizes all chat-related settings and data

import { Sparkle, Image, At, Paperclip } from "@phosphor-icons/react";

export interface ChatAction {
  id: string;
  label: string;
  icon: React.ElementType;
}

export interface ChatConfig {
  placeholder: string;
  actions: ChatAction[];
  ui: {
    borderRadius: string;
    padding: string;
    maxWidth: string;
    buttonSize: string;
    gap: string;
  };
  typography: {
    fontFamily: string;
    fontSize: string;
    lineHeight: string;
  };
  colors: {
    background: string;
    border: string;
    text: string;
    placeholder: string;
    button: string;
    buttonHover: string;
    buttonText: string;
    separator: string;
  };
  icons: {
    size: number;
    weight: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  };
}

export const chatConfig: ChatConfig = {
  placeholder: "Ask me anything...",
  actions: [
    { id: "media", label: "Media", icon: Image },
    { id: "tag-papers", label: "Tag papers", icon: At },
    { id: "attach-pdf", label: "Attach pdf", icon: Paperclip }
  ],
  ui: {
    borderRadius: "24px",
    padding: "24px",
    maxWidth: "650px",
    buttonSize: "48px",
    gap: "24px"
  },
  typography: {
    fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
    fontSize: "16px",
    lineHeight: "1.75em"
  },
  colors: {
    background: "#FDFDFD",
    border: "#F2F2F2",
    text: "#0D0D0D",
    placeholder: "#8C8C8C",
    button: "#262626",
    buttonHover: "#404040",
    buttonText: "#F2F2F2",
    separator: "#D9D9D9"
  },
  icons: {
    size: 24,
    weight: "light"
  }
};

export const getGreeting = (userName?: string) => {
  const hour = new Date().getHours();
  let timeGreeting = "Hello";
  
  if (hour < 12) timeGreeting = "Good morning";
  else if (hour < 18) timeGreeting = "Good afternoon";
  else timeGreeting = "Good evening";
  
  return {
    title: userName ? `${timeGreeting}, ${userName}!` : "Hello, James!",
    subtitle: "What do you want to learn today?"
  };
};

// Typography configuration for greeting text
export const greetingConfig = {
  title: {
    fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
    fontSize: "40px",
    fontWeight: "700",
    lineHeight: "1.4em",
    color: "#404040" // Figma color for greeting title
  },
  subtitle: {
    fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
    fontSize: "24px", 
    fontWeight: "500",
    lineHeight: "1.333em",
    color: "#737373" // Figma color for subtitle
  },
  spacing: {
    // Main container spacing (between greeting and chat input)
    container: "56px", // Increased spacing for better separation
    containerMobile: "40px", // Smaller spacing on mobile
    
    // Text spacing (between title and subtitle)
    text: "8px", // space between title and subtitle
    textMobile: "6px", // Slightly smaller on mobile
    
    // Additional layout spacing options
    sectionPadding: "24px", // Standard section padding
    componentGap: "16px" // Gap between smaller components
  },
  
  // Responsive breakpoints for spacing
  breakpoints: {
    mobile: "768px",
    tablet: "1024px",
    desktop: "1280px"
  }
};

export const handleChatAction = (actionId: string) => {
  switch (actionId) {
    case "media":
      console.log("Opening media picker...");
      // Implement media picker logic
      break;
    case "tag-papers":
      console.log("Opening paper tagger...");
      // Implement paper tagging logic
      break;
    case "attach-pdf":
      console.log("Opening PDF attachment...");
      // Implement PDF attachment logic
      break;
    default:
      console.log(`Unknown action: ${actionId}`);
  }
};

// Helper function to get spacing values based on screen size
export const getSpacing = (
  spacingType: 'container' | 'text' | 'sectionPadding' | 'componentGap',
  isMobile: boolean = false
) => {
  const { spacing } = greetingConfig;
  
  switch (spacingType) {
    case 'container':
      return isMobile ? spacing.containerMobile : spacing.container;
    case 'text':
      return isMobile ? spacing.textMobile : spacing.text;
    case 'sectionPadding':
      return spacing.sectionPadding;
    case 'componentGap':
      return spacing.componentGap;
    default:
      return spacing.componentGap;
  }
};

// Helper to create responsive spacing styles
export const createSpacingStyle = (
  spacingType: 'container' | 'text' | 'sectionPadding' | 'componentGap',
  direction: 'gap' | 'margin' | 'padding' = 'gap'
) => {
  const spacing = getSpacing(spacingType);
  
  switch (direction) {
    case 'gap':
      return { gap: spacing };
    case 'margin':
      return { margin: spacing };
    case 'padding':
      return { padding: spacing };
    default:
      return { gap: spacing };
  }
};

export default chatConfig; 