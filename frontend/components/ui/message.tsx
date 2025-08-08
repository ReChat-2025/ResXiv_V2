import React from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Icon } from "@/components/ui/icon";
import { cn } from "@/lib/utils";

interface MessageProps {
  message: string;
  type: "success" | "error" | "warning" | "info";
  className?: string;
  variant?: "inline" | "alert" | "badge";
  showIcon?: boolean;
}

const messageConfig = {
  success: {
    icon: "CheckCircle" as const,
    alertClass: "border-green-200 bg-green-50 text-green-800 [&>svg]:text-green-600",
    badgeClass: "text-green-700 bg-green-50 border-green-200",
    inlineClass: "text-green-700",
    iconClass: "text-green-600"
  },
  error: {
    icon: "XCircle" as const,
    alertClass: "border-red-200 bg-red-50 text-red-800 [&>svg]:text-red-600",
    badgeClass: "text-red-700 bg-red-50 border-red-200", 
    inlineClass: "text-destructive",
    iconClass: "text-red-600"
  },
  warning: {
    icon: "Warning" as const,
    alertClass: "border-yellow-200 bg-yellow-50 text-yellow-800 [&>svg]:text-yellow-600",
    badgeClass: "text-yellow-700 bg-yellow-50 border-yellow-200",
    inlineClass: "text-yellow-700",
    iconClass: "text-yellow-600"
  },
  info: {
    icon: "Info" as const,
    alertClass: "border-blue-200 bg-blue-50 text-blue-800 [&>svg]:text-blue-600",
    badgeClass: "text-blue-700 bg-blue-50 border-blue-200",
    inlineClass: "text-blue-700",
    iconClass: "text-blue-600"
  }
};

export function Message({ 
  message, 
  type,
  className,
  variant = "inline",
  showIcon = true 
}: MessageProps) {
  const config = messageConfig[type];

  if (variant === "alert") {
    return (
      <Alert className={cn(config.alertClass, "mb-4", className)}>
        {showIcon && (
          <Icon name={config.icon} size={16} />
        )}
        <AlertDescription>{message}</AlertDescription>
      </Alert>
    );
  }

  if (variant === "badge") {
    return (
      <div className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border",
        config.badgeClass,
        className
      )}>
        {showIcon && (
          <Icon name={config.icon} size={12} />
        )}
        {message}
      </div>
    );
  }

  // inline variant (default)
  return (
    <div className={cn(
      "flex items-center gap-1.5 text-sm",
      config.inlineClass,
      className
    )}>
      {showIcon && (
        <Icon name={config.icon} size={14} className={cn(config.iconClass, "flex-shrink-0")} />
      )}
      <span>{message}</span>
    </div>
  );
}