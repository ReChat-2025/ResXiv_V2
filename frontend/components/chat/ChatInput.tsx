"use client";

import React, { useState } from "react";
import { Sparkle } from "@phosphor-icons/react";
import { chatConfig, handleChatAction, type ChatAction } from "@/lib/config/chat-config";

interface ChatInputProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  onSend?: (message: string) => void;
  onKeyPress?: (e: React.KeyboardEvent) => void;
  actions?: ChatAction[];
  disabled?: boolean;
  className?: string;
}

export function ChatInput({
  placeholder = chatConfig.placeholder,
  value = "",
  onChange,
  onSend,
  onKeyPress,
  actions = chatConfig.actions,
  disabled = false,
  className = ""
}: ChatInputProps) {
  const [inputValue, setInputValue] = useState(value);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    if (onChange) {
      onChange(newValue);
    }
  };

  const handleSend = () => {
    if (!inputValue.trim() || disabled) return;
    if (onSend) {
      onSend(inputValue);
    }
    setInputValue("");
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (onKeyPress) {
      onKeyPress(e);
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleActionClick = (action: ChatAction) => {
    handleChatAction(action.id);
  };

  return (
    <>
      <style jsx>{`
        .chat-input::placeholder {
          color: ${chatConfig.colors.placeholder} !important;
          opacity: 1;
        }
      `}</style>
      <div 
        className={`border rounded-3xl ${className}`}
        style={{
          backgroundColor: chatConfig.colors.background,
          borderColor: chatConfig.colors.border,
          padding: chatConfig.ui.padding,
          maxWidth: chatConfig.ui.maxWidth,
          margin: '0 auto'
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: chatConfig.ui.gap }}>
          {/* Main Input Area */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ flex: 1 }}>
              <textarea
                placeholder={placeholder}
                value={inputValue}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                disabled={disabled}
                className="w-full resize-none border-0 bg-transparent focus:outline-none chat-input"
                rows={1}
                style={{ 
                  fontFamily: chatConfig.typography.fontFamily,
                  fontSize: chatConfig.typography.fontSize,
                  lineHeight: chatConfig.typography.lineHeight,
                  color: chatConfig.colors.text,
                  minHeight: '48px'
                }}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || disabled}
              className="rounded-full flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                height: chatConfig.ui.buttonSize,
                width: chatConfig.ui.buttonSize,
                backgroundColor: chatConfig.colors.button,
                color: chatConfig.colors.buttonText
              }}
              onMouseEnter={(e) => {
                if (!disabled && inputValue.trim()) {
                  e.currentTarget.style.backgroundColor = chatConfig.colors.buttonHover;
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = chatConfig.colors.button;
              }}
            >
              <Sparkle size={chatConfig.icons.size} weight={chatConfig.icons.weight} />
            </button>
          </div>

          {/* Action Buttons */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            gap: '24px' 
          }}>
            {actions.map((action, index) => (
              <React.Fragment key={action.id}>
                <button
                  onClick={() => handleActionClick(action)}
                  className="flex items-center transition-colors"
                  style={{
                    gap: '4px',
                    fontFamily: chatConfig.typography.fontFamily,
                    fontSize: chatConfig.typography.fontSize,
                    lineHeight: chatConfig.typography.lineHeight,
                    color: chatConfig.colors.text,
                    border: 'none',
                    background: 'none',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = chatConfig.colors.buttonHover;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = chatConfig.colors.text;
                  }}
                >
                  <action.icon size={chatConfig.icons.size} weight={chatConfig.icons.weight} />
                  {action.label}
                </button>
                {index < actions.length - 1 && (
                  <div 
                    style={{
                      height: '24px',
                      width: '1px',
                      backgroundColor: chatConfig.colors.separator
                    }}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

export default ChatInput; 