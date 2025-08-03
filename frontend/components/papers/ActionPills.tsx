"use client";

import React from "react";
import { papersPageConfig, ActionPill } from "@/lib/config/papers-config";

interface ActionPillsProps {
  onActionClick?: (actionId: string) => void;
  className?: string;
  position?: {
    bottom?: string;
    left?: string;
    right?: string;
    top?: string;
  };
}

export function ActionPills({ 
  onActionClick,
  className = "",
  position = { bottom: "24px", left: "340px" }
}: ActionPillsProps) {
  const config = papersPageConfig;

  const handleActionClick = (actionId: string) => {
    onActionClick?.(actionId);
  };

  return (
    <div 
      className={`fixed z-10 ${className}`}
      style={{
        bottom: position.bottom,
        left: position.left,
        right: position.right,
        top: position.top,
        display: "flex",
        alignItems: "center",
        gap: config.styling.gap.large
      }}
    >
      {config.actionPills.map((pill) => {
        const IconComponent = pill.icon;
        
        return (
          <button
            key={pill.id}
            onClick={() => handleActionClick(pill.id)}
            className="transition-all duration-200"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: config.styling.gap.small,
              padding: "4px 8px",
              backgroundColor: config.styling.colors.sidebarBackground,
              border: "none",
              borderRadius: config.styling.borderRadius.pill,
              cursor: "pointer",
              boxShadow: `0 2px 8px ${config.styling.colors.shadowLight}`,
              whiteSpace: "nowrap"
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = config.styling.colors.borderLight;
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 4px 12px ${config.styling.colors.shadowLight}`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = config.styling.colors.sidebarBackground;
              e.currentTarget.style.transform = "translateY(0px)";
              e.currentTarget.style.boxShadow = `0 2px 8px ${config.styling.colors.shadowLight}`;
            }}
          >
            <IconComponent 
              size={config.icons.size} 
              weight={config.icons.weight}
              style={{ color: config.styling.colors.textPrimary }}
            />
            <span style={{
              color: config.styling.colors.textSecondary,
              fontFamily: config.styling.typography.fontFamily,
              fontSize: config.styling.typography.sizes.medium,
              fontWeight: config.styling.typography.weights.normal,
              lineHeight: config.styling.typography.lineHeights.relaxed
            }}>
              {pill.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export default ActionPills; 