import React from "react";
import * as PhosphorIcons from "phosphor-react";
import { cn } from "@/lib/utils";
import { iconSystem, type IconCategory, type IconVariant } from "@/lib/design-system";

type IconName = keyof typeof PhosphorIcons;

interface IconProps {
  name: IconName;
  size?: number;
  weight?: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  className?: string;
}

// Enhanced Icon component with design system integration
export function Icon({ name, size = 24, weight = "regular", className }: IconProps) {
  const IconComponent = PhosphorIcons[name] as React.ComponentType<{
    size?: number;
    weight?: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
    className?: string;
  }>;
  
  if (!IconComponent) {
    console.warn(`Icon "${String(name)}" not found in Phosphor Icons`);
    return null;
  }
  
  return <IconComponent size={size} weight={weight} className={cn(className)} />;
}

// Design System Icon component for consistent usage
interface DesignSystemIconProps {
  category: IconCategory;
  variant: IconVariant;
  size?: number;
  weight?: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  className?: string;
}

export function DesignSystemIcon({ 
  category, 
  variant, 
  size = 24, 
  weight = "regular", 
  className 
}: DesignSystemIconProps) {
  const iconName = (iconSystem as any)[category as any][variant as any] as IconName;
  
  if (!iconName) {
    console.warn(`Icon variant "${variant}" not found in category "${category}"`);
    return null;
  }
  
  return <Icon name={iconName} size={size} weight={weight} className={className} />;
}

// Predefined icon components for common use cases
export const NavigationIcon = ({ variant, ...props }: Omit<DesignSystemIconProps, 'category'>) => (
  <DesignSystemIcon category="navigation" variant={variant} {...props} />
);

export const ActionIcon = ({ variant, ...props }: Omit<DesignSystemIconProps, 'category'>) => (
  <DesignSystemIcon category="actions" variant={variant} {...props} />
);

export const UIIcon = ({ variant, ...props }: Omit<DesignSystemIconProps, 'category'>) => (
  <DesignSystemIcon category="ui" variant={variant} {...props} />
);

export const ContentIcon = ({ variant, ...props }: Omit<DesignSystemIconProps, 'category'>) => (
  <DesignSystemIcon category="content" variant={variant} {...props} />
);

export const CommunicationIcon = ({ variant, ...props }: Omit<DesignSystemIconProps, 'category'>) => (
  <DesignSystemIcon category="communication" variant={variant} {...props} />
);

export const StatusIcon = ({ variant, ...props }: Omit<DesignSystemIconProps, 'category'>) => (
  <DesignSystemIcon category="status" variant={variant} {...props} />
);

// Export commonly used icon names for better TypeScript support
export type CommonIconNames = 
  | "House"
  | "FileText" 
  | "PencilSimple"
  | "Users"
  | "Gear"
  | "ChatCircle"
  | "Bell"
  | "User"
  | "Plus"
  | "X"
  | "Check"
  | "CaretDown"
  | "CaretLeft"
  | "CaretRight"
  | "List"
  | "MagnifyingGlass"
  | "PaperPlaneTilt"
  | "Image"
  | "Tag"
  | "Paperclip"
  | "DotsThreeVertical"
  | "ArrowUp"
  | "ArrowRight"
  | "ArrowLeft"
  | "Copy"
  | "Upload"
  | "Download"
  | "Share"
  | "Heart"
  | "Star"
  | "Bookmark"
  | "BookmarkSimple"
  | "Eye"
  | "EyeSlash"
  | "Lock"
  | "LockOpen"
  | "Shield"
  | "Warning"
  | "Info"
  | "CheckCircle"
  | "XCircle"
  | "Question"
  | "Lightbulb"
  | "Calendar"
  | "Clock"
  | "MapPin"
  | "Phone"
  | "Envelope"
  | "Link"
  | "Globe"
  | "Folder"
  | "FolderOpen"
  | "File"
  | "FilePdf"
  | "FileDoc"
  | "FileImage"
  | "Archive"
  | "Trash"
  | "PencilLine"
  | "Eraser"
  | "Palette"
  | "Code"
  | "Terminal"
  | "Database"
  | "CloudArrowUp"
  | "CloudArrowDown"
  | "Wifi"
  | "WifiSlash"
  | "Battery"
  | "BatteryLow"
  | "Lightning"
  | "Sun"
  | "Moon"
  | "Cpu"
  | "HardDrives"
  | "Monitor"
  | "DeviceMobile"
  | "Headphones"
  | "Microphone"
  | "Camera"
  | "VideoCamera"
  | "Play"
  | "Pause"
  | "Stop"
  | "SkipBack"
  | "SkipForward"
  | "Repeat"
  | "Shuffle"
  | "SpeakerHigh"
  | "SpeakerX"
  | "GraphicsCard"
  | "ChartBar"
  | "ChartLine"
  | "ChartPie"
  | "TrendUp"
  | "TrendDown"
  | "Target"
  | "Flag"
  | "Medal"
  | "Trophy"
  | "Crown"
  | "Diamond"
  | "Fire"
  | "ThumbsUp"
  | "ThumbsDown"
  | "Smiley"
  | "SmileyWink"
  | "SmileySad"
  | "Handshake"
  | "HandWaving"
  | "Rocket"
  | "Airplane"
  | "Car"
  | "Bicycle"
  | "Train"
  | "Boat"
  | "Truck"
  | "Bus"
  | "Motorcycle"
  | "Scooter"
  | "Sidebar"
  | "SidebarSimple"
  | "Sparkle"
  | "At"
  | "UserPlus"
  | "CheckSquare"
  | "BookOpen"
  | "Funnel"
  | "ArrowsDownUp"
  | "CaretUp"
  | "DotsThreeHorizontal"
  | "UserMinus"
  | "UserCircle"
  | "ArrowSquareOut"
  | "ArrowClockwise"
  | "Spinner"
  | "Document"
  | "Note"
  | "Label"
  | "Inbox"
  | "MessageCircle"
  | "ChatDots"
  | "MessageText"
  | "Broadcast"
  | "Megaphone"
  | "Circle"
  | "CircleSlash"
  | "ClockCounterClockwise"
  | "FloppyDisk";

export default Icon; 