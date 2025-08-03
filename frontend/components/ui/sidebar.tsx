"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
// Removed ScrollArea import - using div instead
import { UIIcon } from "@/components/ui/icon";
import { layoutConstants } from "@/lib/design-system";

// Types
interface SidebarItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  href?: string;
  onClick?: () => void;
  badge?: string | number;
  disabled?: boolean;
  children?: SidebarItem[];
}

interface SidebarSection {
  id: string;
  title?: string;
  items: SidebarItem[];
}

interface SidebarProps {
  sections: SidebarSection[];
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
  selectedItemId?: string;
  onItemSelect?: (itemId: string) => void;
  showToggleButton?: boolean;
  toggleButtonLabel?: string;
}

export function Sidebar({
  sections,
  collapsed = false,
  onToggleCollapse,
  className,
  selectedItemId,
  onItemSelect,
  showToggleButton = true,
  toggleButtonLabel = "Toggle Sidebar",
}: SidebarProps) {
  const handleItemClick = (item: SidebarItem) => {
    if (item.disabled) return;
    
    if (item.onClick) {
      item.onClick();
    } else if (onItemSelect) {
      onItemSelect(item.id);
    }
  };

  const renderItem = (item: SidebarItem, level: number = 0) => {
    const isSelected = selectedItemId === item.id;
    const hasChildren = item.children && item.children.length > 0;

    return (
      <div key={item.id}>
        <Button
          variant={isSelected ? "default" : "ghost"}
          size="sm"
          className={cn(
            "w-full justify-start gap-2 h-9",
            level > 0 && "ml-4",
            collapsed && "justify-center px-2"
          )}
          onClick={() => handleItemClick(item)}
          disabled={item.disabled}
        >
          {item.icon && (
            <div className="flex-shrink-0">
              {item.icon}
            </div>
          )}
          {!collapsed && (
            <>
              <span className="flex-1 text-left truncate">
                {item.label}
              </span>
              {item.badge && (
                <span className="ml-auto px-2 py-0.5 text-xs bg-primary text-primary-foreground rounded-full">
                  {item.badge}
                </span>
              )}
            </>
          )}
        </Button>
        
        {hasChildren && !collapsed && (
          <div className="ml-4 mt-1 space-y-1">
            {item.children!.map((child) => renderItem(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <aside
      className={cn(
        "flex flex-col border-r bg-card transition-all duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64",
        className
      )}
    >
      {/* Header */}
      {showToggleButton && onToggleCollapse && (
        <div className="flex items-center justify-between p-4 border-b">
          {!collapsed && (
            <h2 className="text-lg font-semibold">Navigation</h2>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleCollapse}
            className="h-8 w-8"
            aria-label={toggleButtonLabel}
          >
            <UIIcon 
              variant={collapsed ? "chevronRight" : "chevronLeft"} 
              size={16} 
            />
          </Button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-6">
          {sections.map((section) => (
            <div key={section.id} className="space-y-2">
              {section.title && !collapsed && (
                <h3 className="text-sm font-medium text-muted-foreground px-2">
                  {section.title}
                </h3>
              )}
              <div className="space-y-1">
                {section.items.map((item) => renderItem(item))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

// Specialized sidebar components
interface NavigationSidebarProps extends Omit<SidebarProps, 'sections'> {
  currentPath?: string;
  onNavigate?: (path: string) => void;
}

export function NavigationSidebar({
  currentPath,
  onNavigate,
  ...props
}: NavigationSidebarProps) {
  const navigationSections = [
    {
      id: "main",
      items: [
        {
          id: "home",
          label: "Home",
          href: "/home",
        },
        {
          id: "papers",
          label: "Papers",
          href: "/papers",
        },
        {
          id: "draft",
          label: "Draft",
          href: "/draft",
        },
        {
          id: "collaborate",
          label: "Collaborate",
          href: "/collaborate",
        },
      ],
    },
    {
      id: "settings",
      items: [
        {
          id: "settings",
          label: "Settings",
          href: "/settings",
        },
      ],
    },
  ];

  const handleItemSelect = (itemId: string) => {
    const item = navigationSections
      .flatMap(section => section.items)
      .find(item => item.id === itemId);
    
    if (item?.href && onNavigate) {
      onNavigate(item.href);
    }
  };

  return (
    <Sidebar
      sections={navigationSections}
      selectedItemId={currentPath}
      onItemSelect={handleItemSelect}
      {...props}
    />
  );
}

export default Sidebar; 