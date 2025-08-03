"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Icon } from "@/components/ui/icon";
import { usePapersStore, usePapersChat } from "@/lib/stores/papers-store";
import { getIconName } from "@/lib/icons";
import { papersConfig, Paper, ChatActionButton } from "@/lib/papers-config";

interface ChatSidebarProps {
  paper?: Paper | null;
  onChatAction?: (action: ChatActionButton) => void;
  onSendMessage?: (message: string) => void;
}

export function ChatSidebar({ paper, onChatAction, onSendMessage }: ChatSidebarProps) {
  const { currentView } = usePapersStore();
  const { input, setInput, sidebarCollapsed, toggleSidebar } = usePapersChat();
  
  // Add null check for config
  const config = papersConfig?.chat;

  const handleSendMessage = () => {
    if (!input?.trim() || !paper) return;
    
    onSendMessage?.(input);
    setInput?.("");
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleChatAction = (action: ChatActionButton) => {
    onChatAction?.(action);
  };

  const tabs = papersConfig?.paperViewer?.tabs || [];

  // Add error boundary for the component
  if (!papersConfig) {
    return (
      <aside className="border-l bg-white w-80 flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm text-gray-500">Loading chat...</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className={`border-l bg-card transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-80'} flex flex-col`}>
      {/* Chat Header with Tabs */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-4">
          {!sidebarCollapsed && (
            <div className="flex gap-1">
              {tabs.map((tab) => (
                <Button
                  key={tab.id}
                  variant={tab.active ? "default" : "ghost"}
                  size="sm"
                  className="gap-2"
                  disabled={!paper} // Disable tabs when no paper is selected
                >
                  <Icon name={tab.iconName as any} size={16} weight="regular" />
                  {tab.label}
                </Button>
              ))}
            </div>
          )}
          
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="h-6 w-6"
            aria-label={sidebarCollapsed ? "Expand chat" : "Collapse chat"}
          >
            <Icon name={getIconName('sidebar')} size={16} weight="regular" />
          </Button>
        </div>
        
        {!sidebarCollapsed && <Separator />}
      </div>

      {/* Chat Content */}
      <div className="flex-1 overflow-y-auto">
        {!sidebarCollapsed && (
          <>
            {paper ? (
              <div className="p-6 space-y-6">
                {/* Main Question */}
                <div className="bg-white rounded-lg p-6 border">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    What is discussed in this paper?
                  </h3>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    This paper introduces a novel framework where multiple AI agents are trained using reinforcement learning (RL), but with an added layer of emotional bias simulation. The goal is to explore how modeling human-like emotional tendencies—such as risk aversion, trust, envy, or optimism—affects the learning strategies, cooperation, and competition between agents.
                  </p>
                </div>

                {/* Quick Actions */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Quick Actions</h4>
                  <div className="space-y-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setInput("Summarize the main findings")}
                      className="w-full justify-start text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                    >
                      📝 Summarize main findings
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setInput("What are the key contributions?")}
                      className="w-full justify-start text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                    >
                      💡 Key contributions
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setInput("Explain the methodology")}
                      className="w-full justify-start text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                    >
                      🔬 Methodology
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setInput("What are the limitations?")}
                      className="w-full justify-start text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                    >
                      ⚠️ Limitations
                    </Button>
                  </div>
                </div>

                {/* Chat Messages Area */}
                <div className="bg-gray-50 rounded-lg p-4 min-h-32">
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <Icon 
                        name={getIconName('chat')} 
                        size={24} 
                        weight="light" 
                        className="mx-auto mb-2 text-gray-400" 
                      />
                      <p className="text-xs text-gray-500">
                        Start a conversation about this paper
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center">
                  <Icon 
                    name={getIconName('chat')} 
                    size={48} 
                    weight="light" 
                    className="mx-auto mb-4 text-gray-400" 
                  />
                  <h3 className="font-medium mb-2 text-gray-900">No Paper Selected</h3>
                  <p className="text-sm text-gray-600">
                    Select a paper to start chatting about it
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Chat Input */}
      {!sidebarCollapsed && paper && (
        <div className="p-4 border-t bg-white">
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-3">
            <div className="flex items-center gap-3">
              {/* Attachment Button */}
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-8 w-8 rounded-full border border-gray-300 bg-white hover:bg-gray-50"
                aria-label="Add attachment"
              >
                <Icon name={getIconName('add')} size={16} weight="regular" />
              </Button>
              
              {/* Text Input */}
              <div className="flex-1">
                <Input
                  placeholder="Chat with pdf..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="border-0 bg-transparent placeholder:text-gray-400 focus-visible:ring-0 focus-visible:ring-offset-0 text-sm"
                  disabled={!paper}
                />
              </div>
              
              {/* Send Button */}
              <Button
                size="icon"
                onClick={handleSendMessage}
                disabled={!input.trim() || !paper}
                className="h-8 w-8 rounded-full bg-gray-900 hover:bg-gray-800"
                aria-label="Send message"
              >
                <Icon name="PaperPlaneTilt" size={16} weight="regular" />
              </Button>
            </div>
          </div>
        </div>
      )}
      
      {/* Collapsed state indicator */}
      {sidebarCollapsed && (
        <div className="p-4 flex flex-col items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            disabled={!paper}
          >
            <Icon name={getIconName('chat')} size={16} weight="regular" />
          </Button>
          {paper && (
            <div className="w-2 h-2 bg-primary rounded-full" />
          )}
        </div>
      )}
    </aside>
  );
} 