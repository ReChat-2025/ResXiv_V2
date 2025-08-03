"use client";

import React, { useState } from "react";
import { papersPageConfig, PaperItem } from "@/lib/config/papers-config";

interface ChatMessage {
  id: string;
  type: 'question' | 'answer';
  content: string;
  timestamp: Date;
}

interface PapersRightSidebarProps {
  paper?: PaperItem | null;
  onSendMessage?: (message: string) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
}

export function PapersRightSidebar({ 
  paper,
  onSendMessage,
  isCollapsed = false,
  onToggleCollapse,
  className = ""
}: PapersRightSidebarProps) {
  const [activeTab, setActiveTab] = useState<'chat' | 'insights'>('chat');
  const [chatMessage, setChatMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      type: "question",
      content: "What is discussed in this paper?",
      timestamp: new Date()
    },
    {
      id: "2",
      type: "answer",
      content: "This paper introduces a novel framework where multiple AI agents are trained using reinforcement learning (RL), but with an added layer of emotional bias simulation. The goal is to explore how modeling human-like emotional tendencies—such as risk aversion, trust, envy, or optimism—affects the learning strategies, cooperation, and competition between agents.",
      timestamp: new Date()
    }
  ]);

  const config = papersPageConfig;

  const handleTabClick = (tabId: 'chat' | 'insights') => {
    setActiveTab(tabId);
  };

  const handleSendClick = () => {
    if (chatMessage.trim() && onSendMessage) {
      onSendMessage(chatMessage.trim());
      
      // Add message to local state
      const newMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'question',
        content: chatMessage.trim(),
        timestamp: new Date()
      };
      setMessages(prev => [...prev, newMessage]);
      setChatMessage("");
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setChatMessage(e.target.value);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSendClick();
    }
  };

  if (isCollapsed) {
    return (
      <div 
        className={`border-l flex flex-col ${className}`}
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
          <config.icons.sidebar 
            size={config.icons.size} 
            weight={config.icons.weight}
            style={{ transform: "scaleX(-1)" }} 
          />
        </button>
      </div>
    );
  }

  return (
    <div 
      className={`border-l flex flex-col ${className}`}
      style={{
        backgroundColor: config.styling.colors.sidebarBackground,
        borderColor: config.styling.colors.borderMedium,
        width: config.dimensions.rightSidebar.width,
        minWidth: config.dimensions.rightSidebar.minWidth,
        padding: config.styling.padding.sidebar,
        minHeight: "100vh"
      }}
    >
      {/* Header Section */}
      <div style={{ 
        display: "flex", 
        flexDirection: "column", 
        gap: config.styling.gap.medium 
      }}>
        
        {/* Tabs and Toggle */}
        <div style={{ 
          display: "flex", 
          justifyContent: "space-between", 
          alignItems: "center",
          gap: config.styling.gap.large
        }}>
          {/* Tab Bar */}
          <div style={{ 
            display: "flex", 
            gap: config.styling.gap.medium 
          }}>
            {config.tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              const IconComponent = tab.icon;
              
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabClick(tab.id)}
                  className="transition-all duration-200"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: config.styling.gap.medium,
                    padding: config.styling.padding.medium,
                    borderRadius: config.styling.borderRadius.button,
                    backgroundColor: isActive ? config.styling.colors.selectedBackground : "transparent",
                    border: "none",
                    cursor: "pointer"
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
                    color: config.styling.colors.textSecondary,
                    fontFamily: config.styling.typography.fontFamily,
                    fontSize: config.styling.typography.sizes.medium,
                    fontWeight: config.styling.typography.weights.normal,
                    lineHeight: config.styling.typography.lineHeights.relaxed
                  }}>
                    {tab.label}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Sidebar Toggle */}
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
            <config.icons.sidebar 
              size={config.icons.size} 
              weight={config.icons.weight}
              style={{ transform: "scaleX(-1)" }}
            />
          </button>
        </div>

        {/* Divider */}
        <div style={{
          height: "1px",
          backgroundColor: config.styling.colors.borderMedium,
          width: "100%"
        }} />
      </div>

      {/* Content Area */}
      <div style={{ 
        flex: 1, 
        display: "flex", 
        flexDirection: "column",
        marginTop: config.styling.gap.large
      }}>
        
        {activeTab === 'chat' ? (
          <>
            {/* Chat Messages */}
            <div style={{
              flex: 1,
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: config.styling.gap.section,
              marginBottom: config.styling.gap.section
            }}>
              {messages.map((message) => (
                <div key={message.id}>
                  {message.type === 'question' && (
                    <div style={{
                      textAlign: "right",
                      marginBottom: config.styling.gap.medium
                    }}>
                      <p style={{
                        color: config.styling.colors.textPrimary,
                        fontFamily: config.styling.typography.fontFamily,
                        fontSize: config.styling.typography.sizes.small,
                        fontWeight: config.styling.typography.weights.normal,
                        lineHeight: "2em",
                        margin: 0
                      }}>
                        {message.content}
                      </p>
                    </div>
                  )}
                  
                  {message.type === 'answer' && (
                    <div style={{ marginBottom: config.styling.gap.section }}>
                      <p style={{
                        color: config.styling.colors.textPrimary,
                        fontFamily: config.styling.typography.fontFamily,
                        fontSize: config.styling.typography.sizes.small,
                        fontWeight: config.styling.typography.weights.normal,
                        lineHeight: config.styling.typography.lineHeights.normal,
                        margin: 0
                      }}>
                        {message.content}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Chat Input */}
            <div style={{
              backgroundColor: config.styling.colors.contentBackground,
              border: `1px solid ${config.styling.colors.borderLight}`,
              borderRadius: config.styling.borderRadius.container,
              padding: config.styling.padding.container,
              boxShadow: `0 14px 25px ${config.styling.colors.shadowLight}`
            }}>
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: config.styling.gap.section
              }}>
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: config.styling.gap.large
                }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "24px",
                    height: "24px",
                    backgroundColor: config.styling.colors.selectedBackground,
                    borderRadius: "500px",
                    border: `1px solid ${config.styling.colors.textMuted}`
                  }}>
                    <config.icons.add 
                      size={24} 
                      weight={config.icons.weight}
                      style={{ color: config.styling.colors.textMuted }}
                    />
                  </div>
                  
                  <input
                    type="text"
                    value={chatMessage}
                    onChange={handleInputChange}
                    onKeyPress={handleKeyPress}
                    placeholder={config.chatPlaceholder}
                    style={{
                      flex: 1,
                      backgroundColor: "transparent",
                      border: "none",
                      outline: "none",
                      color: config.styling.colors.textPrimary,
                      fontFamily: config.styling.typography.fontFamily,
                      fontSize: config.styling.typography.sizes.medium,
                      fontWeight: config.styling.typography.weights.normal,
                      lineHeight: config.styling.typography.lineHeights.relaxed
                    }}
                  />
                </div>

                <button
                  onClick={handleSendClick}
                  disabled={!chatMessage.trim()}
                  className="transition-colors"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "24px",
                    height: "24px",
                    backgroundColor: "transparent",
                    border: "none",
                    cursor: chatMessage.trim() ? "pointer" : "not-allowed",
                    opacity: chatMessage.trim() ? 1 : 0.5
                  }}
                >
                  <config.icons.send 
                    size={config.icons.size} 
                    weight={config.icons.weight}
                    style={{ 
                      color: config.styling.colors.textPrimary,
                      transform: "rotate(45deg)"
                    }}
                  />
                </button>
              </div>
            </div>
          </>
        ) : (
          /* Insights Tab Content */
          <div style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: config.styling.colors.textDisabled
          }}>
            <div style={{ textAlign: "center" }}>
              <config.icons.insights 
                size={24} 
                weight={config.icons.weight}
                style={{ 
                  color: config.styling.colors.textDisabled,
                  marginBottom: config.styling.gap.medium
                }}
              />
              <p style={{
                fontFamily: config.styling.typography.fontFamily,
                fontSize: config.styling.typography.sizes.medium,
                fontWeight: config.styling.typography.weights.normal,
                margin: 0
              }}>
                Insights coming soon
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default PapersRightSidebar; 