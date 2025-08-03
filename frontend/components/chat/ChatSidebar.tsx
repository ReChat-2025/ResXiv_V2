"use client";

import React, { useState } from "react";
import { ChatCircle } from "@phosphor-icons/react";
import { 
  chatSidebarConfig,
  defaultConversations,
  searchConversations,
  type ConversationItem,
  type ConversationGroup
} from "@/lib/config/chat-sidebar-config";
import PrimaryButton from "@/components/ui/PrimaryButton";
import SearchInput from "@/components/ui/SearchInput";

interface ChatSidebarProps {
  conversations?: ConversationGroup[];
  isCollapsed?: boolean;
  selectedConversationId?: string | null; // Add support for selected conversation
  onToggleCollapse?: () => void;
  onNewChat?: () => void;
  onSearchSubmit?: (query: string) => void;
  onConversationSelect?: (conversationId: string) => void;
  className?: string;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations = defaultConversations,
  isCollapsed = false,
  selectedConversationId = null,
  onToggleCollapse,
  onNewChat,
  onSearchSubmit,
  onConversationSelect,
  className = ""
}) => {
  const config = chatSidebarConfig;
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredConversations, setFilteredConversations] = useState(conversations);
  
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    
    // Filter conversations based on search query
    const filtered = searchConversations(conversations, value);
    setFilteredConversations(filtered);
  };

  const handleSearchSubmit = (value: string) => {
    if (onSearchSubmit) {
      onSearchSubmit(value);
    }
  };

  const handleNewChatClick = () => {
    if (onNewChat) {
      onNewChat();
    }
  };

  const handleConversationClick = (conversationId: string) => {
    if (onConversationSelect) {
      onConversationSelect(conversationId);
    }
  };

  // Collapsed state
  if (isCollapsed) {
    return (
      <div 
        className={`border flex flex-col ${className}`}
        style={{
          backgroundColor: config.styling.colors.background,
          borderColor: config.styling.colors.border,
          width: config.dimensions.collapsed.width,
          height: config.dimensions.collapsed.height,
          borderRadius: config.styling.borderRadius.container,
          padding: config.styling.padding,
          margin: config.styling.spacing.outerPadding
        }}
      >
        <button
          onClick={onToggleCollapse}
          className="flex items-center justify-center w-6 h-6 transition-colors"
          style={{
            color: config.styling.colors.textSecondary
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = config.styling.colors.text;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = config.styling.colors.textSecondary;
          }}
        >
          <config.icons.sidebar 
            size={config.icons.size} 
            weight={config.icons.weight} 
          />
        </button>
      </div>
    );
  }

  // Expanded state
  return (
    <div 
      className={`border flex flex-col ${className}`}
      style={{
        backgroundColor: config.styling.colors.background,
        borderColor: config.styling.colors.border,
        width: config.dimensions.expanded.width,
        height: config.dimensions.expanded.height,
        borderRadius: config.styling.borderRadius.container,
        padding: config.styling.padding,
        gap: config.styling.spacing.sectionGap,
        fontFamily: config.styling.typography.fontFamily,
        margin: config.styling.spacing.outerPadding
      }}
    >
      {/* Header Section */}
      <div style={{ 
        display: "flex", 
        flexDirection: "column", 
        gap: config.styling.spacing.headerGap, 
        padding: config.styling.spacing.headerPadding 
      }}>
        <div style={{ 
          display: "flex", 
          justifyContent: "space-between", 
          alignItems: "center", 
          gap: "16px" 
        }}>
          {/* Title container with flexible width to show full text */}
          <div style={{ 
            display: "flex",
            alignItems: "center",
            overflow: "visible",
            flex: "1",
            minWidth: "0"
          }}>
            <h2 
              style={{
                color: config.styling.colors.text,
                fontFamily: config.styling.typography.fontFamily,
                fontWeight: config.styling.typography.title.fontWeight,
                fontSize: config.styling.typography.title.fontSize,
                lineHeight: config.styling.typography.title.lineHeight,
                margin: 0,
                whiteSpace: "nowrap",
                overflow: "visible"
              }}
            >
              {config.title}
            </h2>
          </div>
          
          <button
            onClick={onToggleCollapse}
            className="w-6 h-6 transition-colors flex items-center justify-center flex-shrink-0"
            style={{
              color: config.styling.colors.textSecondary
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = config.styling.colors.text;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = config.styling.colors.textSecondary;
            }}
          >
            <config.icons.sidebar 
              size={config.icons.size} 
              weight={config.icons.weight} 
            />
          </button>
        </div>

        {/* Action Buttons */}
        <div style={{ 
          display: "flex", 
          flexDirection: "column", 
          gap: config.styling.spacing.buttonGap 
        }}>
          {/* New Chat Button - Using PrimaryButton Component */}
          <PrimaryButton
            onClick={handleNewChatClick}
            icon={ChatCircle}
            iconSize={config.icons.size}
            iconWeight={config.icons.weight}
            variant="primary"
          >
            {config.newChatLabel}
          </PrimaryButton>

          {/* Search Input - Using SearchInput Component */}
          <SearchInput
            placeholder={config.searchPlaceholder}
            value={searchQuery}
            onChange={handleSearchChange}
            onSubmit={handleSearchSubmit}
            iconSize={config.icons.size}
            iconWeight={config.icons.weight}
            variant="default"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div 
        className="flex-1 overflow-y-auto"
        style={{ 
          display: "flex", 
          flexDirection: "column", 
          gap: config.styling.spacing.itemGap 
        }}
      >
        {filteredConversations.map((group, groupIndex) => (
          <div 
            key={groupIndex} 
            style={{ 
              display: "flex", 
              flexDirection: "column", 
              gap: config.styling.spacing.itemGap,
              marginBottom: groupIndex < filteredConversations.length - 1 ? "16px" : "0"
            }}
          >
            {/* Group Label */}
            <div style={{ padding: config.styling.spacing.labelPadding }}>
              <h3 
                style={{
                  color: config.styling.colors.textMuted,
                  fontFamily: config.styling.typography.fontFamily,
                  fontWeight: config.styling.typography.label.fontWeight,
                  fontSize: config.styling.typography.label.fontSize,
                  lineHeight: config.styling.typography.label.lineHeight,
                  margin: 0,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis"
                }}
              >
                {group.label}
              </h3>
            </div>

            {/* Conversations in Group */}
            {group.conversations.map((conversation) => {
              const isSelected = conversation.id === selectedConversationId;
              
              return (
                <button
                  key={conversation.id}
                  onClick={() => handleConversationClick(conversation.id)}
                  className="transition-colors text-left"
                  style={{
                    backgroundColor: isSelected 
                      ? config.styling.colors.conversationItemSelected 
                      : config.styling.colors.conversationItem,
                    padding: config.styling.spacing.itemPadding,
                    borderRadius: config.styling.borderRadius.conversationItem,
                    width: "fit-content",
                    border: "none",
                    cursor: "pointer",
                    maxWidth: "100%"
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = isSelected 
                      ? config.styling.colors.conversationItemSelectedHover
                      : config.styling.colors.conversationItemHover;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = isSelected 
                      ? config.styling.colors.conversationItemSelected
                      : config.styling.colors.conversationItem;
                  }}
                >
                  <p 
                    style={{
                      color: config.styling.colors.text,
                      fontFamily: config.styling.typography.fontFamily,
                      fontWeight: config.styling.typography.body.fontWeight,
                      fontSize: config.styling.typography.body.fontSize,
                      lineHeight: config.styling.typography.body.lineHeight,
                      margin: 0,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      maxWidth: "250px" // Constrain width to prevent overflow
                    }}
                  >
                    {conversation.title}
                  </p>
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChatSidebar; 