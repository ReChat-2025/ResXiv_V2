import React from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Icon } from "@/components/ui/icon";
import { cn } from "@/lib/utils";

interface ErrorMessageProps {
  message: string;
  className?: string;
  variant?: "inline" | "alert" | "badge";
  showIcon?: boolean;
}

export function ErrorMessage({ 
  message, 
  className,
  variant = "inline",
  showIcon = true 
}: ErrorMessageProps) {
  if (variant === "alert") {
    return (
      <Alert variant="destructive" className={cn("mb-4", className)}>
        {showIcon && (
          <Icon name="XCircle" size={16} className="text-destructive" />
        )}
        <AlertDescription>{message}</AlertDescription>
      </Alert>
    );
  }

  if (variant === "badge") {
    return (
      <div className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium",
        "text-red-700 bg-red-50 border border-red-200",
        className
      )}>
        {showIcon && (
          <Icon name="XCircle" size={12} className="text-red-600" />
        )}
        {message}
      </div>
    );
  }

  // inline variant (default)
  return (
    <div className={cn(
      "flex items-center gap-1.5 text-sm text-destructive",
      className
    )}>
      {showIcon && (
        <Icon name="XCircle" size={14} className="text-destructive flex-shrink-0" />
      )}
      <span>{message}</span>
    </div>
  );
}