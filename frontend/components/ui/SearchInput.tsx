"use client";

import React, { useState } from "react";
import { MagnifyingGlass } from "@phosphor-icons/react";
import { searchInputConfig } from "@/lib/config/ui-config";

interface SearchInputProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  onSubmit?: (value: string) => void;
  onKeyPress?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  className?: string;
  style?: React.CSSProperties;
  iconSize?: number;
  iconWeight?: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  variant?: "default" | "transparent";
}

const SearchInput: React.FC<SearchInputProps> = ({
  placeholder = "Search",
  value,
  onChange,
  onSubmit,
  onKeyPress,
  disabled = false,
  className = "",
  style = {},
  iconSize,
  iconWeight,
  variant = "default"
}) => {
  const [internalValue, setInternalValue] = useState("");
  const inputValue = value !== undefined ? value : internalValue;

  // Get configuration for the variant
  const config = variant === "transparent" 
    ? searchInputConfig.transparent 
    : searchInputConfig.default;

  // Use config values or props
  const finalIconSize = iconSize || config.iconSize;
  const finalIconWeight = iconWeight || config.iconWeight;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    if (value === undefined) {
      setInternalValue(newValue);
    }
    if (onChange) {
      onChange(newValue);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && onSubmit) {
      onSubmit(inputValue);
    }
    if (onKeyPress) {
      onKeyPress(e);
    }
  };

  const baseStyles: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: config.gap,
    padding: config.padding,
    borderRadius: config.borderRadius,
    width: "100%",
    transition: config.transition,
    fontFamily: config.fontFamily,
    fontSize: config.fontSize,
    fontWeight: config.fontWeight,
    lineHeight: config.lineHeight,
    backgroundColor: config.backgroundColor,
    border: config.border,
    cursor: disabled ? "not-allowed" : "default",
    opacity: disabled ? 0.6 : 1,
    ...style
  };

  const [isHovered, setIsHovered] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const currentBorderColor = isFocused 
    ? config.focusBorderColor 
    : isHovered 
      ? config.hoverBorderColor 
      : config.border?.includes('#') 
        ? config.border.split(' ')[2] 
        : '#E7E7E7';

  const dynamicStyles: React.CSSProperties = {
    ...baseStyles,
    borderColor: currentBorderColor
  };

  return (
    <div
      className={`transition-all duration-200 ${className}`}
      style={dynamicStyles}
      onMouseEnter={() => !disabled && setIsHovered(true)}
      onMouseLeave={() => !disabled && setIsHovered(false)}
    >
      <MagnifyingGlass 
        size={finalIconSize} 
        weight={finalIconWeight} 
        style={{ 
          color: "#737373", // --papers-text-muted - consistent across all variants
          flexShrink: 0
        }}
      />
      <input
        type="text"
        placeholder={placeholder}
        value={inputValue}
        onChange={handleInputChange}
        onKeyPress={handleKeyPress}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        disabled={disabled}
        className="bg-transparent border-none outline-none flex-1 min-w-0"
        style={{
          color: config.color,
          fontFamily: config.fontFamily,
          fontWeight: config.fontWeight,
          fontSize: config.fontSize,
          lineHeight: config.lineHeight
        }}
      />
      <style jsx>{`
        input::placeholder {
          color: ${config.placeholderColor};
        }
        input:disabled {
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};

export default SearchInput; 