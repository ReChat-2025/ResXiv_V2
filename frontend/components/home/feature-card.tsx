import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NavigationIcon, ActionIcon, UIIcon, ContentIcon } from "@/components/ui/icon";
import { cn } from "@/lib/utils";

// Types
interface FeatureConfig {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: string;
  variant?: 'default' | 'outline' | 'ghost' | 'link';
  category?: 'navigation' | 'actions' | 'ui' | 'content';
  badge?: string;
  disabled?: boolean;
}

interface FeatureCardProps {
  feature: FeatureConfig;
  className?: string;
  onClick?: () => void;
}

// Icon mapping for different categories
const getIconComponent = (category: string, icon: string) => {
  switch (category) {
    case 'navigation':
      return <NavigationIcon variant={icon as any} size={24} />;
    case 'actions':
      return <ActionIcon variant={icon as any} size={24} />;
    case 'ui':
      return <UIIcon variant={icon as any} size={24} />;
    case 'content':
      return <ContentIcon variant={icon as any} size={24} />;
    default:
      return <UIIcon variant="help" size={24} />;
  }
};

export function FeatureCard({ feature, className, onClick }: FeatureCardProps) {
  const IconComponent = getIconComponent(feature.category || 'ui', feature.icon);

  const cardContent = (
    <Card 
      variant="interactive" 
      className={cn(
        "group transition-all duration-200 hover:shadow-md",
        feature.disabled && "opacity-50 cursor-not-allowed",
        className
      )}
      onClick={onClick}
    >
      <CardHeader className="text-center pb-4">
        <div className="mx-auto w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
          <div className="text-primary">
            {IconComponent}
          </div>
        </div>
        <CardTitle className="text-lg font-semibold">{feature.title}</CardTitle>
        <CardDescription className="text-sm text-muted-foreground">
          {feature.description}
        </CardDescription>
        {feature.badge && (
          <div className="mt-2">
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
              {feature.badge}
            </span>
          </div>
        )}
      </CardHeader>
      <CardContent className="pt-0">
        <Button 
          asChild 
          variant={feature.variant || "default"}
          className="w-full"
          disabled={feature.disabled}
        >
          <Link href={feature.href}>
            {feature.title}
          </Link>
        </Button>
      </CardContent>
    </Card>
  );

  if (feature.disabled) {
    return cardContent;
  }

  return (
    <Link href={feature.href} className="block">
      {cardContent}
    </Link>
  );
}

// Predefined feature configurations - removed tasks and journals
export const featureConfigs: FeatureConfig[] = [
  {
    id: "papers",
    title: "Browse Papers",
    description: "Explore and manage your research papers with AI-powered insights",
    href: "/papers",
    icon: "papers",
    category: "navigation",
    badge: "Popular",
  },
  {
    id: "draft",
    title: "Start Writing",
    description: "Create and edit your research documents with collaborative tools",
    href: "/draft",
    icon: "draft",
    category: "navigation",
  },
  {
    id: "collaborate",
    title: "Collaborate",
    description: "Work together with your research team in real-time",
    href: "/collaborate",
    icon: "collaborate",
    category: "navigation",
  },
  {
    id: "settings",
    title: "Settings",
    description: "Configure your workspace and preferences",
    href: "/settings",
    icon: "settings",
    category: "navigation",
  },
];

// Feature grid component for displaying multiple features
interface FeatureGridProps {
  features?: FeatureConfig[];
  columns?: 1 | 2 | 3 | 4;
  className?: string;
}

export function FeatureGrid({ 
  features = featureConfigs, 
  columns = 3, 
  className 
}: FeatureGridProps) {
  const gridCols = {
    1: "grid-cols-1",
    2: "grid-cols-1 md:grid-cols-2",
    3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
  };

  return (
    <div className={cn("grid gap-6", gridCols[columns], className)}>
      {features.map((feature) => (
        <FeatureCard key={feature.id} feature={feature} />
      ))}
    </div>
  );
} 