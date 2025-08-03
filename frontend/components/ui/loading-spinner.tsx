import React from "react";
import { cn } from "@/lib/utils";
import { UIIcon } from "@/components/ui/icon";

// Types
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'primary' | 'secondary' | 'muted';
  className?: string;
  text?: string;
  showText?: boolean;
}

const sizeClasses = {
  sm: "w-4 h-4",
  md: "w-6 h-6",
  lg: "w-8 h-8",
  xl: "w-12 h-12",
};

const variantClasses = {
  default: "text-foreground",
  primary: "text-primary",
  secondary: "text-secondary-foreground",
  muted: "text-muted-foreground",
};

export function LoadingSpinner({
  size = "md",
  variant = "default",
  className,
  text,
  showText = false,
}: LoadingSpinnerProps) {
  return (
    <div className={cn("flex items-center justify-center", className)}>
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "animate-spin rounded-full border-2 border-current border-t-transparent",
            sizeClasses[size],
            variantClasses[variant]
          )}
        />
        {showText && (
          <span className={cn("text-sm", variantClasses[variant])}>
            {text || "Loading..."}
          </span>
        )}
      </div>
    </div>
  );
}

// Icon-based loading spinner
interface IconLoadingSpinnerProps {
  icon?: string;
  size?: number;
  className?: string;
  text?: string;
  showText?: boolean;
}

export function IconLoadingSpinner({
  icon = "loading",
  size = 24,
  className,
  text,
  showText = false,
}: IconLoadingSpinnerProps) {
  return (
    <div className={cn("flex items-center justify-center", className)}>
      <div className="flex items-center gap-2">
        <UIIcon
          variant={icon as any}
          size={size}
          className="animate-spin text-muted-foreground"
        />
        {showText && (
          <span className="text-sm text-muted-foreground">
            {text || "Loading..."}
          </span>
        )}
      </div>
    </div>
  );
}

// Page loading component
interface PageLoadingProps {
  title?: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'primary' | 'secondary' | 'muted';
  className?: string;
}

export function PageLoading({
  title = "Loading...",
  description = "Please wait while we load your content",
  size = "lg",
  variant = "default",
  className,
}: PageLoadingProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center min-h-[400px]", className)}>
      <div className="text-center space-y-4">
        <LoadingSpinner size={size} variant={variant} />
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-foreground">{title}</h3>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
    </div>
  );
}

// Skeleton loading component
interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
}

export function Skeleton({ className, variant = "rectangular" }: SkeletonProps) {
  const baseClasses = "animate-pulse bg-muted";
  
  const variantClasses = {
    text: "h-4 rounded",
    circular: "rounded-full",
    rectangular: "rounded",
  };

  return (
    <div
      className={cn(
        baseClasses,
        variantClasses[variant],
        className
      )}
    />
  );
}

// Skeleton components for common use cases
export const SkeletonComponents = {
  Text: ({ className }: { className?: string }) => (
    <Skeleton variant="text" className={className} />
  ),
  
  Title: ({ className }: { className?: string }) => (
    <Skeleton variant="text" className={cn("h-6 w-3/4", className)} />
  ),
  
  Avatar: ({ className }: { className?: string }) => (
    <Skeleton variant="circular" className={cn("w-10 h-10", className)} />
  ),
  
  Card: ({ className }: { className?: string }) => (
    <div className={cn("space-y-3", className)}>
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  ),
  
  ListItem: ({ className }: { className?: string }) => (
    <div className={cn("flex items-center space-x-3", className)}>
      <Skeleton variant="circular" className="w-8 h-8" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
  ),
  
  Table: ({ rows = 5, className }: { rows?: number; className?: string }) => (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex space-x-3">
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </div>
  ),
};

export default LoadingSpinner; 