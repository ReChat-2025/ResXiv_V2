"use client";

import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Icon } from "@/components/ui/icon";
import { MessageCircle } from "lucide-react";

interface Message {
  id: string;
  senderName: string;
  senderAvatar?: string;
  content: string;
  timestamp: string;
  type?: 'text' | 'image' | 'file';
}

interface ChatAreaProps {
  messages?: Message[];
  isLoading?: boolean;
  onSendMessage?: (message: string) => void;
  onAttachFile?: () => void;
  onAddImage?: () => void;
}

export function ChatArea({ 
  messages = [], 
  isLoading = false,
  onSendMessage,
  onAttachFile,
  onAddImage 
}: ChatAreaProps) {
  const [messageInput, setMessageInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom function
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    } else if (scrollAreaRef.current) {
      // Fallback method
      scrollAreaRef.current.scrollTo({
        top: scrollAreaRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  // Auto-scroll when messages change (handles both initial load and updates)
  useEffect(() => {
    if (messages.length > 0 && !isLoading) {
      // Small delay to ensure DOM is updated
      const timeoutId = setTimeout(scrollToBottom, 100);
      return () => clearTimeout(timeoutId);
    }
    // Return undefined when condition is not met
    return undefined;
  }, [messages, isLoading]);

  const handleSendMessage = () => {
    if (messageInput.trim() && onSendMessage) {
      onSendMessage(messageInput.trim());
      setMessageInput("");
      // Scroll to bottom after sending message
      setTimeout(scrollToBottom, 150);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-card">
      {/* Messages Area */}
      <div ref={scrollAreaRef} className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <MessageCircle className="h-12 w-12 text-muted-foreground opacity-50 mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">No messages yet</h3>
            <p className="text-muted-foreground max-w-sm">
              Start a conversation with your team members to collaborate on this project.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div key={message.id} className="flex items-start space-x-3">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={message.senderAvatar} alt={message.senderName || 'User'} />
                  <AvatarFallback className="bg-muted text-muted-foreground text-sm">
                    {(message.senderName || 'U').slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-foreground">{message.senderName || 'Unknown User'}</span>
                    <span className="text-xs text-muted-foreground">{message.timestamp}</span>
                  </div>
                  <p className="text-foreground mt-1 break-words">{message.content}</p>
                </div>
              </div>
            ))}
            {/* Invisible div to mark the end of messages for auto-scroll */}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Message Input */}
      <div className="border-t border-border p-4">
        <div className="flex items-center space-x-3">
          <div className="flex-1">
            <Input
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type a message..."
              className="bg-background border-border"
            />
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={onAttachFile}
              className="text-muted-foreground hover:text-foreground"
            >
              <Icon name="Paperclip" size={18} weight="regular" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onAddImage}
              className="text-muted-foreground hover:text-foreground"
            >
              <Icon name="Image" size={18} weight="regular" />
            </Button>
            <Button
              onClick={handleSendMessage}
              disabled={!messageInput.trim()}
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              <Icon name="PaperPlaneTilt" size={16} weight="bold" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
} 