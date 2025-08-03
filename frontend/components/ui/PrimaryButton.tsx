"use client";

import React from "react";
import { type Icon } from "@phosphor-icons/react";

interface PrimaryButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  icon?: Icon;
  iconColor?: string;
  iconSize?: number;
  iconWeight?: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  disabled?: boolean;
  className?: string;
  style?: React.CSSProperties;
  variant?: "primary" | "secondary";
}

const PrimaryButton: React.FC<PrimaryButtonProps> = ({
  children,
  onClick,
  icon: IconComponent,
  iconColor = "#FFFFFF",
  iconSize = 24,
  iconWeight = "regular",
  disabled = false,
  className = "",
  style = {},
  variant = "primary"
}) => {
  const baseStyles: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    padding: "12px 8px",
    borderRadius: "12px",
    fontFamily: "var(--font-manrope), Manrope, system-ui, sans-serif",
    fontWeight: "400",
    fontSize: "16px",
    lineHeight: "1.75em",
    border: "none",
    cursor: disabled ? "not-allowed" : "pointer",
    width: "100%",
    transition: "background-color 0.2s ease",
    opacity: disabled ? 0.6 : 1,
    ...style
  };

  const variantStyles: React.CSSProperties = variant === "primary" 
    ? {
        backgroundColor: "#0D0D0D",
        color: "#FFFFFF"
      }
    : {
        backgroundColor: "transparent",
        color: "#0D0D0D",
        border: "1px solid #E7E7E7"
      };

  const hoverStyles = variant === "primary"
    ? { backgroundColor: "#262626" }
    : { backgroundColor: "#F5F5F5" };

  const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!disabled) {
      Object.assign(e.currentTarget.style, hoverStyles);
    }
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!disabled) {
      e.currentTarget.style.backgroundColor = variantStyles.backgroundColor || "transparent";
    }
  };

  return (
    <button
      onClick={disabled ? undefined : onClick}
      className={`transition-colors ${className}`}
      style={{
        ...baseStyles,
        ...variantStyles
      }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      disabled={disabled}
    >
      {IconComponent && (
        <IconComponent 
          size={iconSize} 
          weight={iconWeight} 
          color={variant === "primary" ? iconColor : "#0D0D0D"} 
        />
      )}
      <span style={{ whiteSpace: "nowrap" }}>{children}</span>
    </button>
  );
};

export default PrimaryButton; 