import React from "react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Icon } from "@/components/ui/icon";

interface SettingsSidebarItem {
  id: string;
  label: string;
  iconName: string;
  href?: string;
}

interface SettingsSidebarConfig {
  title: string;
  items: SettingsSidebarItem[];
  upgradeButton: {
    text: string;
    iconName: string;
  };
}

interface SettingsSidebarProps {
  activeSection: string;
  onSectionChange: (sectionId: string) => void;
  config: SettingsSidebarConfig;
}

export function SettingsSidebar({
  activeSection,
  onSectionChange,
  config
}: SettingsSidebarProps) {
  return (
    <aside className="w-80 border-r bg-muted/30 flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b">
        <div className="flex items-center gap-2">
          <Icon name="FileText" size={20} weight="regular" className="text-muted-foreground" />
          <h2 className="text-lg font-semibold text-foreground">
            {config.title}
          </h2>
        </div>
      </div>

      {/* Navigation Items */}
      <div className="flex-1 p-4 space-y-2">
        {config.items.map((item) => {
          const isActive = activeSection === item.id;
          
          return (
            <Button
              key={item.id}
              variant={isActive ? "default" : "ghost"}
              className={`w-full justify-start gap-3 h-10 ${
                isActive 
                  ? "bg-primary text-primary-foreground hover:bg-primary/90" 
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
              onClick={() => onSectionChange(item.id)}
            >
              <Icon 
                name={item.iconName as any}
                size={16} 
                weight="regular"
                className={isActive ? "text-primary-foreground" : "text-muted-foreground"}
              />
              <span className="font-medium">
                {item.label}
              </span>
            </Button>
          );
        })}
      </div>

      {/* Upgrade Button */}
      <div className="p-4 border-t">
        <Button 
          variant="default" 
          className="w-full bg-primary hover:bg-primary/90 text-primary-foreground gap-2"
          onClick={() => console.log("Upgrade to Pro")}
        >
          <Icon name="ArrowUp" size={16} weight="regular" />
          {config.upgradeButton.text}
        </Button>
      </div>
    </aside>
  );
}

export default SettingsSidebar; 