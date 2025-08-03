// UI Components Configuration
// Centralized styling and behavior for consistent UI components

export interface ButtonVariantConfig {
  fontFamily: string;
  fontWeight: string;
  fontSize: string;
  lineHeight: string;
  borderRadius: string;
  padding: string;
  gap: string;
  iconSize: number;
  iconWeight: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  transition: string;
  backgroundColor: string;
  color: string;
  hoverBackgroundColor: string;
  hoverColor: string;
  border?: string;
}

export interface ButtonConfig {
  primary: ButtonVariantConfig;
  secondary: ButtonVariantConfig;
}

export interface SearchInputVariantConfig {
  fontFamily: string;
  fontWeight: string;
  fontSize: string;
  lineHeight: string;
  borderRadius: string;
  padding: string;
  gap: string;
  iconSize: number;
  iconWeight: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  transition: string;
  backgroundColor: string;
  color: string;
  border: string;
  placeholderColor: string;
  hoverBorderColor: string;
  focusBorderColor: string;
}

export interface SearchInputConfig {
  default: SearchInputVariantConfig;
  transparent: SearchInputVariantConfig;
}

// Icon sizes for consistent design
export const iconSizes = {
  small: 16,
  medium: 20,
  large: 24,
  xlarge: 32
};

// Default icon configuration
export const defaultIconConfig = {
  size: 24,
  weight: "light" as const
};

export const buttonConfig: ButtonConfig = {
  primary: {
    fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
    fontWeight: "400",
    fontSize: "16px",
    lineHeight: "1.75em",
    borderRadius: "12px",
    padding: "12px 20px",
    gap: "8px",
    iconSize: 24,
    iconWeight: "light",
    transition: "all 0.2s ease",
    backgroundColor: "#0D0D0D",
    color: "#F2F2F2",
    hoverBackgroundColor: "#262626",
    hoverColor: "#F2F2F2"
  },
  secondary: {
    fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
    fontWeight: "400",
    fontSize: "16px",
    lineHeight: "1.75em",
    borderRadius: "12px",
    padding: "12px 20px",
    gap: "8px",
    iconSize: 24,
    iconWeight: "light",
    transition: "all 0.2s ease",
    backgroundColor: "transparent",
    color: "#0D0D0D",
    border: "1px solid #E7E7E7",
    hoverBackgroundColor: "#F0F0F0",
    hoverColor: "#0D0D0D"
  }
};

export const searchInputConfig: SearchInputConfig = {
  default: {
    fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
    fontWeight: "400",
    fontSize: "16px",
    lineHeight: "1.75em",
    borderRadius: "12px",
    padding: "12px",
    gap: "8px",
    iconSize: 24,
    iconWeight: "light",
    transition: "all 0.2s ease",
    backgroundColor: "transparent",
    color: "#0D0D0D",           // --papers-text-primary
    border: "1px solid #E7E7E7", // --papers-border-medium
    placeholderColor: "#8C8C8C", // --papers-text-light
    hoverBorderColor: "#D9D9D9", // --papers-border-dark
    focusBorderColor: "#737373"  // --papers-text-muted
  },
  transparent: {
    fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
    fontWeight: "400", 
    fontSize: "16px",
    lineHeight: "1.75em",
    borderRadius: "12px",
    padding: "12px",
    gap: "8px",
    iconSize: 24,
    iconWeight: "light",
    transition: "all 0.2s ease",
    backgroundColor: "transparent",
    color: "#0D0D0D",           // --papers-text-primary
    border: "none",
    placeholderColor: "#8C8C8C", // --papers-text-light
    hoverBorderColor: "transparent",
    focusBorderColor: "transparent"
  }
};

// Color palette for consistent UI
export const uiColors = {
  primary: "#0D0D0D",
  secondary: "#737373",
  text: "#0D0D0D",
  textSecondary: "#737373",
  textMuted: "#8C8C8C",
  background: "#EFEFED",
  border: "#E7E7E7",
  hover: "#F5F5F5",
  white: "#FFFFFF"
};

// Spacing system
export const spacing = {
  xs: "4px",
  sm: "8px",
  md: "12px",
  lg: "16px",
  xl: "24px",
  xxl: "32px"
};

// Border radius system
export const borderRadius = {
  sm: "8px",
  md: "12px",
  lg: "16px",
  xl: "24px"
};

export default {
  buttonConfig,
  searchInputConfig,
  uiColors,
  spacing,
  borderRadius,
  iconSizes
}; 