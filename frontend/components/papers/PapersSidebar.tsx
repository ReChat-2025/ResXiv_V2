"use client";

import React, { useState } from "react";
import { 
  papersPageConfig, 
  mockPapers,
  getPaperCount,
  formatAuthors,
  PaperItem,
  ViewMode
} from "@/lib/config/papers-config";
import SearchInput from "@/components/ui/SearchInput";
import PrimaryButton from "@/components/ui/PrimaryButton";

interface PapersSidebarProps {
  papers?: PaperItem[];
  onAddPapers?: () => void;
  onPaperSelect?: (paper: PaperItem) => void;
  onViewModeChange?: (mode: 'chat' | 'graph') => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
}

export function PapersSidebar({ 
  papers = mockPapers,
  onAddPapers,
  onPaperSelect,
  onViewModeChange,
  isCollapsed = false,
  onToggleCollapse,
  className = ""
}: PapersSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedViewMode, setSelectedViewMode] = useState<'chat' | 'graph'>('chat');
  const [selectedPaperId, setSelectedPaperId] = useState<string>(papers.find(p => p.isSelected)?.id || "");

  const config = papersPageConfig;
  const filteredPapers = papers.filter(paper =>
    paper.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    paper.authors.some(author => author.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handlePaperClick = (paper: PaperItem) => {
    setSelectedPaperId(paper.id);
    onPaperSelect?.(paper);
  };

  const handleViewModeClick = (mode: 'chat' | 'graph') => {
    setSelectedViewMode(mode);
    onViewModeChange?.(mode);
  };

  const handleAddPapersClick = () => {
    onAddPapers?.();
  };

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
  };

  const handleSearchSubmit = (query: string) => {
    setSearchQuery(query);
  };

  if (isCollapsed) {
    return (
      <div 
        className={`border-r flex flex-col ${className}`}
        style={{
          backgroundColor: config.styling.colors.sidebarBackground,
          borderColor: config.styling.colors.borderMedium,
          width: "64px",
          padding: config.styling.padding.sidebar,
          minHeight: "100vh"
        }}
      >
        <button
          onClick={onToggleCollapse}
          className="flex items-center justify-center transition-colors"
          style={{
            width: "24px",
            height: "24px",
            color: config.styling.colors.textMuted
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = config.styling.colors.textPrimary;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = config.styling.colors.textMuted;
          }}
        >
          <config.icons.sidebar size={config.icons.size} weight={config.icons.weight} />
        </button>
      </div>
    );
  }

  return (
    <div 
      className={`border-r flex flex-col ${className}`}
      style={{
        backgroundColor: config.styling.colors.sidebarBackground,
        borderColor: config.styling.colors.borderMedium,
        width: config.dimensions.leftSidebar.width,
        minWidth: config.dimensions.leftSidebar.minWidth,
        padding: config.styling.padding.sidebar,
        minHeight: "100vh"
      }}
    >
      {/* Header Section - Papers title and toggle */}
      <div style={{ 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "center",
        marginBottom: config.styling.gap.section
      }}>
        <h1 style={{
          color: config.styling.colors.textPrimary,
          fontFamily: config.styling.typography.fontFamily,
          fontSize: config.styling.typography.sizes.medium,
          fontWeight: config.styling.typography.weights.normal,
          lineHeight: config.styling.typography.lineHeights.relaxed,
          margin: 0
        }}>
          {config.title}
        </h1>
        
        <button
          onClick={onToggleCollapse}
          className="transition-colors"
          style={{
            width: "24px",
            height: "24px",
            color: config.styling.colors.textMuted,
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = config.styling.colors.textPrimary;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = config.styling.colors.textMuted;
          }}
        >
          <config.icons.sidebar size={config.icons.size} weight={config.icons.weight} />
        </button>
      </div>

      {/* View Mode Buttons */}
      <div style={{ 
        display: "flex", 
        flexDirection: "column", 
        gap: "2px",
        marginBottom: config.styling.gap.section
      }}>
        {config.viewModes.map((mode) => {
          const isActive = selectedViewMode === mode.id;
          const IconComponent = mode.icon;
          
          return (
            <button
              key={mode.id}
              onClick={() => handleViewModeClick(mode.id)}
              className="transition-all duration-200"
              style={{
                display: "flex",
                alignItems: "center",
                gap: config.styling.gap.medium,
                padding: config.styling.padding.button,
                borderRadius: config.styling.borderRadius.button,
                backgroundColor: isActive ? config.styling.colors.selectedBackground : "transparent",
                border: "none",
                cursor: "pointer",
                width: "100%",
                textAlign: "left"
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = config.styling.colors.borderLight;
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "transparent";
                }
              }}
            >
              <IconComponent 
                size={config.icons.size} 
                weight={config.icons.weight}
                style={{ color: config.styling.colors.textMuted }}
              />
              <span style={{
                color: config.styling.colors.textPrimary,
                fontFamily: config.styling.typography.fontFamily,
                fontSize: config.styling.typography.sizes.medium,
                fontWeight: config.styling.typography.weights.normal,
                lineHeight: config.styling.typography.lineHeights.relaxed
              }}>
                {mode.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Divider */}
      <div style={{
        height: "1px",
        backgroundColor: config.styling.colors.borderMedium,
        width: "100%",
        marginBottom: config.styling.gap.section
      }} />

      {/* Add Paper Button (Full Width) */}
      <div style={{ 
        marginBottom: config.styling.gap.section
      }}>
        <PrimaryButton
          onClick={handleAddPapersClick}
          icon={config.icons.filePlus}
          style={{ width: "100%" }}
        >
          Add Paper
        </PrimaryButton>
      </div>

      {/* Search Input (Full Width) */}
      <div style={{ 
        marginBottom: config.styling.gap.section
      }}>
        <SearchInput
          placeholder="Search papers..."
          value={searchQuery}
          onChange={handleSearchChange}
          onSubmit={handleSearchSubmit}
          variant="transparent"
          iconSize={config.icons.size}
          iconWeight={config.icons.weight}
        />
      </div>

      {/* Papers List */}
      <div style={{ 
        flex: 1, 
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: config.styling.gap.small
      }}>
        {filteredPapers.length === 0 ? (
          <div style={{
            textAlign: "center",
            padding: config.styling.gap.section,
            color: config.styling.colors.textDisabled
          }}>
            <p style={{
              fontFamily: config.styling.typography.fontFamily,
              fontSize: config.styling.typography.sizes.small,
              margin: 0
            }}>
              {searchQuery ? 'No papers found' : 'No papers yet'}
            </p>
          </div>
        ) : (
          filteredPapers.map((paper) => {
            const isSelected = selectedPaperId === paper.id;
            
            return (
              <button
                key={paper.id}
                onClick={() => handlePaperClick(paper)}
                className="transition-all duration-200"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: config.styling.padding.medium,
                  backgroundColor: isSelected ? config.styling.colors.selectedBackground : "transparent",
                  border: "none",
                  borderRadius: config.styling.borderRadius.card,
                  cursor: "pointer",
                  width: "100%",
                  textAlign: "center"
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = config.styling.colors.borderLight;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = "transparent";
                  }
                }}
              >
                <span style={{
                  color: config.styling.colors.textPrimary,
                  fontFamily: config.styling.typography.fontFamily,
                  fontSize: config.styling.typography.sizes.medium,
                  fontWeight: config.styling.typography.weights.normal,
                  lineHeight: config.styling.typography.lineHeights.relaxed,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  width: "100%"
                }}>
                  {paper.title}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
} 