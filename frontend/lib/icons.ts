import * as PhosphorIcons from "phosphor-react";

// Icon configuration type
export interface IconConfig {
  name: keyof typeof PhosphorIcons;
  size?: number;
  weight?: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  className?: string;
}

// Semantic icon mappings for easier maintenance and i18n
export const iconMap = {
  // Navigation
  home: "House",
  papers: "FileText",
  draft: "PencilSimple", 
  collaborate: "Users",
  settings: "Gear",
  
  // Actions
  search: "MagnifyingGlass",
  add: "Plus",
  edit: "PencilLine",
  delete: "Trash",
  save: "CheckCircle",
  cancel: "X",
  copy: "Copy",
  share: "Share",
  download: "Download",
  upload: "Upload",
  refresh: "ArrowClockwise",
  
  // UI Elements
  menu: "List",
  close: "X",
  expand: "CaretDown",
  collapse: "CaretUp",
  next: "CaretRight",
  previous: "CaretLeft",
  sidebar: "Sidebar",
  notification: "Bell",
  user: "User",
  
  // Communication
  chat: "ChatCircle",
  message: "Envelope",
  phone: "Phone",
  video: "VideoCamera",
  
  // Content
  document: "File",
  pdf: "FilePdf",
  image: "Image",
  link: "Link",
  folder: "Folder",
  archive: "Archive",
  
  // Status
  loading: "CircleNotch",
  success: "CheckCircle",
  error: "XCircle",
  warning: "Warning",
  info: "Info",
  
  // Media
  play: "Play",
  pause: "Pause",
  stop: "Stop",
  volume: "SpeakerHigh",
  mute: "SpeakerX",
  
  // Formatting
  bold: "TextBolder",
  italic: "TextItalic",
  underline: "TextUnderline",
  align_left: "TextAlignLeft",
  align_center: "TextAlignCenter",
  align_right: "TextAlignRight",
  
  // Data
  chart: "ChartLine",
  graph: "ChartBar",
  table: "Table",
  calendar: "Calendar",
  clock: "Clock",
  
  // Tools
  filter: "Funnel",
  sort: "SortAscending",
  zoom_in: "MagnifyingGlassPlus",
  zoom_out: "MagnifyingGlassMinus",
  fullscreen: "ArrowsOut",
  
  // Social
  like: "Heart",
  star: "Star",
  bookmark: "BookmarkSimple",
  follow: "UserPlus",
  
  // Academic
  citation: "Quotes",
  reference: "ArrowBendUpRight",
  journal: "Book",
  conference: "Presentation",
  
  // Special
  sparkle: "Sparkle",
  lightning: "Lightning",
  fire: "Fire",
  target: "Target",
  
} as const;

// Icon theme configurations
export const iconThemes = {
  default: {
    size: 24,
    weight: "regular" as const,
  },
  small: {
    size: 16,
    weight: "regular" as const,
  },
  large: {
    size: 32,
    weight: "regular" as const,
  },
  bold: {
    size: 24,
    weight: "bold" as const,
  },
  light: {
    size: 24,
    weight: "light" as const,
  },
} as const;

// Context-specific icon sets for consistency
export const iconSets = {
  navigation: {
    home: iconMap.home,
    papers: iconMap.papers,
    draft: iconMap.draft,
    collaborate: iconMap.collaborate,
    settings: iconMap.settings,
  },
  
  actions: {
    primary: iconMap.add,
    secondary: iconMap.edit,
    destructive: iconMap.delete,
    confirm: iconMap.save,
    cancel: iconMap.cancel,
  },
  
  status: {
    loading: iconMap.loading,
    success: iconMap.success,
    error: iconMap.error,
    warning: iconMap.warning,
    info: iconMap.info,
  },
  
  media: {
    play: iconMap.play,
    pause: iconMap.pause,
    stop: iconMap.stop,
    volume: iconMap.volume,
    mute: iconMap.mute,
  },
  
  academic: {
    paper: iconMap.document,
    pdf: iconMap.pdf,
    citation: iconMap.citation,
    reference: iconMap.reference,
    journal: iconMap.journal,
    conference: iconMap.conference,
  },
} as const;

// Utility functions for icon management
export const getIconName = (semanticName: keyof typeof iconMap): keyof typeof PhosphorIcons => {
  return iconMap[semanticName] as keyof typeof PhosphorIcons;
};

export const getIconConfig = (
  semanticName: keyof typeof iconMap,
  theme: keyof typeof iconThemes = 'default',
  overrides?: Partial<IconConfig>
): IconConfig => {
  const iconName = getIconName(semanticName);
  const themeConfig = iconThemes[theme];
  
  return {
    name: iconName,
    size: themeConfig.size,
    weight: themeConfig.weight,
    ...overrides,
  };
};

// Icon validation
export const isValidIcon = (iconName: string): iconName is keyof typeof PhosphorIcons => {
  return iconName in PhosphorIcons;
};

// Dynamic icon loading for performance
export const loadIcon = async (iconName: keyof typeof PhosphorIcons) => {
  try {
    const IconComponent = PhosphorIcons[iconName];
    if (!IconComponent) {
      throw new Error(`Icon "${String(iconName)}" not found`);
    }
    return IconComponent;
  } catch (error) {
    console.warn(`Failed to load icon "${String(iconName)}":`, error);
    return PhosphorIcons.Question; // Fallback icon
  }
};

// Icon preset configurations for common use cases
export const iconPresets = {
  button: {
    size: 16,
    weight: "regular" as const,
  },
  
  toolbar: {
    size: 20,
    weight: "regular" as const,
  },
  
  sidebar: {
    size: 18,
    weight: "regular" as const,
  },
  
  header: {
    size: 24,
    weight: "regular" as const,
  },
  
  hero: {
    size: 48,
    weight: "light" as const,
  },
  
  indicator: {
    size: 12,
    weight: "bold" as const,
  },
} as const;

// Type helpers
export type SemanticIconName = keyof typeof iconMap;
export type IconTheme = keyof typeof iconThemes;
export type IconPreset = keyof typeof iconPresets;
export type IconWeight = "thin" | "light" | "regular" | "bold" | "fill" | "duotone";

// Helper to get icon class names based on context
export const getIconClassName = (
  context: 'button' | 'navigation' | 'status' | 'decorative' = 'decorative',
  state?: 'active' | 'disabled' | 'hover'
): string => {
  const baseClasses = 'transition-colors duration-200';
  
  const contextClasses = {
    button: 'inline-flex',
    navigation: 'flex-shrink-0',
    status: 'inline-block',
    decorative: '',
  };
  
  const stateClasses = {
    active: 'text-primary',
    disabled: 'text-muted-foreground opacity-50',
    hover: 'hover:text-foreground',
  };
  
  return [
    baseClasses,
    contextClasses[context],
    state ? stateClasses[state] : '',
  ].filter(Boolean).join(' ');
};

// Export commonly used combinations
export const commonIcons = {
  // Primary actions
  addPaper: { name: getIconName('add'), preset: iconPresets.button },
  searchPapers: { name: getIconName('search'), preset: iconPresets.button },
  
  // Navigation
  navHome: { name: getIconName('home'), preset: iconPresets.sidebar },
  navPapers: { name: getIconName('papers'), preset: iconPresets.sidebar },
  navSettings: { name: getIconName('settings'), preset: iconPresets.sidebar },
  
  // Paper actions
  citePaper: { name: getIconName('citation'), preset: iconPresets.toolbar },
  sharePaper: { name: getIconName('share'), preset: iconPresets.toolbar },
  downloadPdf: { name: getIconName('download'), preset: iconPresets.toolbar },
  
  // Status indicators
  loadingSpinner: { name: getIconName('loading'), preset: iconPresets.indicator },
  successCheck: { name: getIconName('success'), preset: iconPresets.indicator },
  errorAlert: { name: getIconName('error'), preset: iconPresets.indicator },
} as const; 