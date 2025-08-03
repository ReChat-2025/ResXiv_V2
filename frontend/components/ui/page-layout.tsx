"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

// Page Container - Main wrapper for all pages
const pageVariants = cva(
  "min-h-screen",
  {
    variants: {
      background: {
        default: "bg-background",
        gray: "bg-gray-50",
        muted: "bg-muted/30",
        gradient: "bg-gradient-to-br from-background via-muted/20 to-background",
      },
      padding: {
        none: "",
        default: "p-4",
        lg: "p-6",
        xl: "p-8",
      },
    },
    defaultVariants: {
      background: "default",
      padding: "default",
    },
  }
)

export interface PageProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof pageVariants> {}

const Page = React.forwardRef<HTMLDivElement, PageProps>(
  ({ className, background, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(pageVariants({ background, padding, className }))}
      {...props}
    />
  )
)
Page.displayName = "Page"

// Container - Content wrapper with max width
const containerVariants = cva(
  "mx-auto w-full",
  {
    variants: {
      size: {
        sm: "max-w-2xl",
        default: "max-w-4xl",
        lg: "max-w-6xl",
        xl: "max-w-7xl",
        full: "max-w-full",
      },
      padding: {
        none: "",
        default: "px-4",
        lg: "px-6",
        xl: "px-8",
      },
    },
    defaultVariants: {
      size: "default",
      padding: "default",
    },
  }
)

export interface ContainerProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof containerVariants> {}

const Container = React.forwardRef<HTMLDivElement, ContainerProps>(
  ({ className, size, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(containerVariants({ size, padding, className }))}
      {...props}
    />
  )
)
Container.displayName = "Container"

// Section - Content sections with consistent spacing
const sectionVariants = cva(
  "",
  {
    variants: {
      spacing: {
        none: "",
        sm: "py-4",
        default: "py-6",
        lg: "py-8",
        xl: "py-12",
      },
      background: {
        transparent: "bg-transparent",
        muted: "bg-muted/30",
        card: "bg-card",
        accent: "bg-accent/30",
      },
      border: {
        none: "",
        top: "border-t",
        bottom: "border-b",
        around: "border rounded-lg",
      },
    },
    defaultVariants: {
      spacing: "default",
      background: "transparent",
      border: "none",
    },
  }
)

export interface SectionProps
  extends React.HTMLAttributes<HTMLElement>,
    VariantProps<typeof sectionVariants> {}

const Section = React.forwardRef<HTMLElement, SectionProps>(
  ({ className, spacing, background, border, ...props }, ref) => (
    <section
      ref={ref}
      className={cn(sectionVariants({ spacing, background, border, className }))}
      {...props}
    />
  )
)
Section.displayName = "Section"

// Header components for consistent headings
export interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  description?: string
  actions?: React.ReactNode
}

const PageHeader = React.forwardRef<HTMLDivElement, PageHeaderProps>(
  ({ className, title, description, actions, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex items-start justify-between pb-6", className)}
      {...props}
    >
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && (
          <p className="text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
)
PageHeader.displayName = "PageHeader"

export { Page, Container, Section, PageHeader, pageVariants, containerVariants, sectionVariants } 