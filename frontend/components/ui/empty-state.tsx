import React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { UIIcon, ActionIcon, ContentIcon } from "@/components/ui/icon";

// Types
interface EmptyStateProps {
  icon?: React.ReactNode;
  iconName?: string;
  iconCategory?: 'ui' | 'actions' | 'content';
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'default' | 'outline' | 'ghost' | 'link';
    icon?: string;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
    variant?: 'default' | 'outline' | 'ghost' | 'link';
    icon?: string;
  };
  className?: string;
  variant?: 'default' | 'card' | 'minimal';
  size?: 'sm' | 'md' | 'lg';
}

const getIconComponent = (category: string, iconName: string) => {
  switch (category) {
    case 'ui':
      return <UIIcon variant={iconName as any} size={48} />;
    case 'actions':
      return <ActionIcon variant={iconName as any} size={48} />;
    case 'content':
      return <ContentIcon variant={iconName as any} size={48} />;
    default:
      return <UIIcon variant="help" size={48} />;
  }
};

const getIconComponentSmall = (category: string, iconName: string) => {
  switch (category) {
    case 'ui':
      return <UIIcon variant={iconName as any} size={24} />;
    case 'actions':
      return <ActionIcon variant={iconName as any} size={24} />;
    case 'content':
      return <ContentIcon variant={iconName as any} size={24} />;
    default:
      return <UIIcon variant="help" size={24} />;
  }
};

export function EmptyState({
  icon,
  iconName = "help",
  iconCategory = "ui",
  title,
  description,
  action,
  secondaryAction,
  className,
  variant = "default",
  size = "md",
}: EmptyStateProps) {
  const sizeClasses = {
    sm: {
      icon: "w-12 h-12",
      title: "text-lg",
      description: "text-sm",
      spacing: "space-y-3",
    },
    md: {
      icon: "w-16 h-16",
      title: "text-xl",
      description: "text-base",
      spacing: "space-y-4",
    },
    lg: {
      icon: "w-20 h-20",
      title: "text-2xl",
      description: "text-lg",
      spacing: "space-y-6",
    },
  };

  const iconElement = icon || getIconComponent(iconCategory, iconName);
  const sizeConfig = sizeClasses[size];

  const content = (
    <div className={cn("text-center", sizeConfig.spacing, className)}>
      {/* Icon */}
      <div className={cn(
        "mx-auto bg-muted/50 rounded-full flex items-center justify-center",
        sizeConfig.icon
      )}>
        <div className="text-muted-foreground">
          {iconElement}
        </div>
      </div>

      {/* Text Content */}
      <div className="space-y-2">
        <h3 className={cn("font-semibold text-foreground", sizeConfig.title)}>
          {title}
        </h3>
        {description && (
          <p className={cn("text-muted-foreground", sizeConfig.description)}>
            {description}
          </p>
        )}
      </div>

      {/* Actions */}
      {(action || secondaryAction) && (
        <div className="flex items-center justify-center gap-3">
          {action && (
            <Button
              variant={action.variant || "default"}
              onClick={action.onClick}
              className="gap-2"
            >
              {action.icon && getIconComponentSmall(iconCategory, action.icon)}
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              variant={secondaryAction.variant || "outline"}
              onClick={secondaryAction.onClick}
              className="gap-2"
            >
              {secondaryAction.icon && getIconComponentSmall(iconCategory, secondaryAction.icon)}
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );

  if (variant === "card") {
    return (
      <Card className="p-8">
        <CardContent className="p-0">
          {content}
        </CardContent>
      </Card>
    );
  }

  if (variant === "minimal") {
    return (
      <div className="p-4">
        {content}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center p-8">
      <div className="max-w-md">
        {content}
      </div>
    </div>
  );
}

// Predefined empty states for common scenarios
export const EmptyStates = {
  NoData: ({ title = "No data available", ...props }: Omit<EmptyStateProps, 'iconName' | 'iconCategory'>) => (
    <EmptyState
      iconName="database"
      iconCategory="content"
      title={title}
      description="There's no data to display at the moment."
      {...props}
    />
  ),
  
  NoResults: ({ title = "No results found", ...props }: Omit<EmptyStateProps, 'iconName' | 'iconCategory'>) => (
    <EmptyState
      iconName="search"
      iconCategory="ui"
      title={title}
      description="Try adjusting your search criteria or filters."
      {...props}
    />
  ),
  
  NoFiles: ({ title = "No files uploaded", ...props }: Omit<EmptyStateProps, 'iconName' | 'iconCategory'>) => (
    <EmptyState
      iconName="file"
      iconCategory="content"
      title={title}
      description="Upload your first file to get started."
      action={{
        label: "Upload File",
        onClick: () => console.log("Upload file"),
        icon: "upload",
      }}
      {...props}
    />
  ),
  
  NoProjects: ({ title = "No projects yet", ...props }: Omit<EmptyStateProps, 'iconName' | 'iconCategory'>) => (
    <EmptyState
      iconName="folder"
      iconCategory="content"
      title={title}
      description="Create your first project to start organizing your research."
      action={{
        label: "Create Project",
        onClick: () => console.log("Create project"),
        icon: "add",
      }}
      {...props}
    />
  ),
  
  NoConversations: ({ title = "No conversations yet", ...props }: Omit<EmptyStateProps, 'iconName' | 'iconCategory'>) => (
    <EmptyState
      iconName="chat"
      iconCategory="ui"
      title={title}
      description="Start a new conversation to begin exploring your research."
      action={{
        label: "New Chat",
        onClick: () => console.log("New chat"),
        icon: "add",
      }}
      {...props}
    />
  ),
  
  Error: ({ title = "Something went wrong", ...props }: Omit<EmptyStateProps, 'iconName' | 'iconCategory'>) => (
    <EmptyState
      iconName="warning"
      iconCategory="ui"
      title={title}
      description="An error occurred while loading this content."
      action={{
        label: "Try Again",
        onClick: () => console.log("Retry"),
        icon: "refresh",
      }}
      {...props}
    />
  ),
  
  Loading: ({ title = "Loading...", ...props }: Omit<EmptyStateProps, 'iconName' | 'iconCategory'>) => (
    <EmptyState
      iconName="loading"
      iconCategory="ui"
      title={title}
      description="Please wait while we load your content."
      {...props}
    />
  ),
};

export default EmptyState; 