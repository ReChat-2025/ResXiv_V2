// import { type IconName } from "@/components/ui/icon";

// Design System Configuration
export const designSystem = {
  // Color Palette
  colors: {
    primary: {
      50: "hsl(var(--beige-50))",
      100: "hsl(var(--beige-100))",
      200: "hsl(var(--beige-200))",
      300: "hsl(var(--beige-300))",
      400: "hsl(var(--beige-400))",
      500: "hsl(var(--beige-500))",
      600: "hsl(var(--beige-600))",
      700: "hsl(var(--beige-700))",
      800: "hsl(var(--beige-800))",
      900: "hsl(var(--beige-900))",
    },
    semantic: {
      background: "hsl(var(--background))",
      foreground: "hsl(var(--foreground))",
      card: "hsl(var(--card))",
      cardForeground: "hsl(var(--card-foreground))",
      popover: "hsl(var(--popover))",
      popoverForeground: "hsl(var(--popover-foreground))",
      primary: "hsl(var(--primary))",
      primaryForeground: "hsl(var(--primary-foreground))",
      secondary: "hsl(var(--secondary))",
      secondaryForeground: "hsl(var(--secondary-foreground))",
      muted: "hsl(var(--muted))",
      mutedForeground: "hsl(var(--muted-foreground))",
      accent: "hsl(var(--accent))",
      accentForeground: "hsl(var(--accent-foreground))",
      destructive: "hsl(var(--destructive))",
      destructiveForeground: "hsl(var(--destructive-foreground))",
      border: "hsl(var(--border))",
      input: "hsl(var(--input))",
      ring: "hsl(var(--ring))",
    }
  },

  // Typography
  typography: {
    fontFamily: {
      sans: "var(--font-manrope), Manrope, system-ui, -apple-system, sans-serif",
      mono: "ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace",
    },
    fontSize: {
      xs: "0.75rem",
      sm: "0.875rem",
      base: "1rem",
      lg: "1.125rem",
      xl: "1.25rem",
      "2xl": "1.5rem",
      "3xl": "1.875rem",
      "4xl": "2.25rem",
      "5xl": "3rem",
      "6xl": "3.75rem",
    },
    fontWeight: {
      thin: "100",
      light: "300",
      normal: "400",
      medium: "500",
      semibold: "600",
      bold: "700",
      extrabold: "800",
    },
    lineHeight: {
      none: "1",
      tight: "1.25",
      snug: "1.375",
      normal: "1.5",
      relaxed: "1.625",
      loose: "2",
    },
  },

  // Spacing
  spacing: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem",
    "2xl": "3rem",
    "3xl": "4rem",
  },

  // Border Radius
  borderRadius: {
    none: "0",
    sm: "0.125rem",
    base: "0.25rem",
    md: "0.375rem",
    lg: "0.5rem",
    xl: "0.75rem",
    "2xl": "1rem",
    full: "9999px",
  },

  // Shadows
  shadows: {
    sm: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
    base: "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    md: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
    lg: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
    xl: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
  },

  // Transitions
  transitions: {
    fast: "150ms ease-in-out",
    base: "200ms ease-in-out",
    slow: "300ms ease-in-out",
  },
};

// Icon System - Centralized icon definitions
export const iconSystem = {
  // Navigation Icons
  navigation: {
    home: "House",
    papers: "FileText",
    draft: "PencilSimple",
    collaborate: "Users",
    settings: "Gear",
  },

  // Action Icons
  actions: {
    add: "Plus",
    edit: "PencilSimple",
    delete: "Trash",
    save: "FloppyDisk",
    close: "X",
    search: "MagnifyingGlass",
    filter: "Funnel",
    sort: "ArrowsDownUp",
    download: "Download",
    upload: "Upload",
    share: "Share",
    copy: "Copy",
    link: "Link",
    bookmark: "BookmarkSimple",
    star: "Star",
    heart: "Heart",
    eye: "Eye",
    eyeSlash: "EyeSlash",
    lock: "Lock",
    unlock: "LockOpen",
    check: "Check",
    warning: "Warning",
    info: "Info",
    error: "XCircle",
    success: "CheckCircle",
    sparkle: "Sparkle",
    cite: "Quotes",
    journal: "Notebook",
  },

  // UI Icons
  ui: {
    chevronDown: "CaretDown",
    chevronUp: "CaretUp",
    chevronLeft: "CaretLeft",
    chevronRight: "CaretRight",
    arrowUp: "ArrowUp",
    arrowDown: "ArrowDown",
    arrowLeft: "ArrowLeft",
    arrowRight: "ArrowRight",
    menu: "List",
    dots: "DotsThreeVertical",
    dotsHorizontal: "DotsThreeHorizontal",
    bell: "Bell",
    user: "User",
    userPlus: "UserPlus",
    userMinus: "UserMinus",
    avatar: "UserCircle",
    settings: "Gear",
    help: "Question",
    external: "ArrowSquareOut",
    refresh: "ArrowClockwise",
    loading: "Spinner",
    sidebar: "Sidebar",
    at: "At",
    attachment: "Paperclip",
    dropdown: "CaretDown",
    arrow: "ArrowUp",
  },

  // Content Icons
  content: {
    file: "File",
    fileText: "FileText",
    filePdf: "FilePdf",
    fileDoc: "FileDoc",
    fileImage: "FileImage",
    folder: "Folder",
    folderOpen: "FolderOpen",
    image: "Image",
    video: "VideoCamera",
    audio: "SpeakerHigh",
    document: "Document",
    note: "Note",
    calendar: "Calendar",
    clock: "Clock",
    tag: "Tag",
    label: "Label",
    bookmark: "BookmarkSimple",
    archive: "Archive",
    inbox: "Inbox",
    send: "PaperPlaneTilt",
    reply: "ArrowUUpLeft",
    forward: "ArrowUUpRight",
    graph: "ChartLine",
    pdf: "FilePdf",
  },

  // Communication Icons
  communication: {
    chat: "ChatCircle",
    chatDots: "ChatDots",
    message: "MessageCircle",
    messageText: "MessageText",
    phone: "Phone",
    envelope: "Envelope",
    at: "At",
    globe: "Globe",
    link: "Link",
    share: "Share",
    broadcast: "Broadcast",
    megaphone: "Megaphone",
  },

  // Status Icons
  status: {
    online: "Circle",
    offline: "CircleSlash",
    busy: "Clock",
    away: "ClockCounterClockwise",
    pending: "Clock",
    completed: "CheckCircle",
    failed: "XCircle",
    warning: "Warning",
    info: "Info",
    error: "XCircle",
    success: "CheckCircle",
  },
};

// Component Variants
export const componentVariants = {
  button: {
    size: {
      sm: "h-8 px-3 text-xs",
      md: "h-10 px-4 text-sm",
      lg: "h-12 px-6 text-base",
    },
    variant: {
      default: "bg-primary text-primary-foreground hover:bg-primary/90",
      secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
      outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
      ghost: "hover:bg-accent hover:text-accent-foreground",
      destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
      link: "text-primary underline-offset-4 hover:underline",
    },
  },
  card: {
    variant: {
      default: "bg-card text-card-foreground",
      secondary: "bg-secondary text-secondary-foreground",
      outline: "border border-border bg-background",
    },
  },
  badge: {
    variant: {
      default: "bg-primary text-primary-foreground",
      secondary: "bg-secondary text-secondary-foreground",
      outline: "border border-border text-foreground",
      destructive: "bg-destructive text-destructive-foreground",
    },
    size: {
      sm: "px-2 py-0.5 text-xs",
      md: "px-2.5 py-0.5 text-sm",
      lg: "px-3 py-1 text-base",
    },
  },
};

// Layout Constants
export const layoutConstants = {
  navbar: {
    height: "3.5rem", // 56px
    zIndex: 50,
  },
  sidebar: {
    width: {
      collapsed: "4rem", // 64px
      expanded: "16rem", // 256px
    },
    zIndex: 40,
  },
  content: {
    maxWidth: "1200px",
    padding: {
      sm: "1rem",
      md: "1.5rem",
      lg: "2rem",
    },
  },
};

// Animation Constants
export const animationConstants = {
  duration: {
    fast: "150ms",
    base: "200ms",
    slow: "300ms",
    slower: "500ms",
  },
  easing: {
    ease: "ease",
    easeIn: "ease-in",
    easeOut: "ease-out",
    easeInOut: "ease-in-out",
  },
};

// Export types for better TypeScript support
export type IconCategory = keyof typeof iconSystem;
export type IconVariant = keyof typeof iconSystem.navigation | keyof typeof iconSystem.actions | keyof typeof iconSystem.ui | keyof typeof iconSystem.content | keyof typeof iconSystem.communication | keyof typeof iconSystem.status; 