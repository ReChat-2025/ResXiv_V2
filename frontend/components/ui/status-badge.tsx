"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Badge } from "./badge"
import { CheckCircle, Clock, AlertCircle, XCircle, Loader2 } from "lucide-react"

const statusBadgeVariants = cva(
  "inline-flex items-center gap-1.5",
  {
    variants: {
      status: {
        success: "text-green-700 bg-green-50 border-green-200",
        warning: "text-yellow-700 bg-yellow-50 border-yellow-200", 
        error: "text-red-700 bg-red-50 border-red-200",
        info: "text-blue-700 bg-blue-50 border-blue-200",
        pending: "text-gray-700 bg-gray-50 border-gray-200",
        processing: "text-purple-700 bg-purple-50 border-purple-200",
        // ResXiv specific statuses
        reading: "text-blue-700 bg-blue-50 border-blue-200",
        completed: "text-green-700 bg-green-50 border-green-200",
        draft: "text-gray-700 bg-gray-50 border-gray-200",
        published: "text-green-700 bg-green-50 border-green-200",
        archived: "text-gray-500 bg-gray-50 border-gray-200",
      },
      size: {
        sm: "text-xs px-2 py-1",
        default: "text-sm px-2.5 py-1",
        lg: "text-sm px-3 py-1.5",
      },
      showIcon: {
        true: "",
        false: "",
      },
    },
    defaultVariants: {
      status: "info",
      size: "default",
      showIcon: true,
    },
  }
)

const iconMap = {
  success: CheckCircle,
  warning: AlertCircle,
  error: XCircle,
  info: AlertCircle,
  pending: Clock,
  processing: Loader2,
  reading: Clock,
  completed: CheckCircle,
  draft: AlertCircle,
  published: CheckCircle,
  archived: XCircle,
}

export interface StatusBadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof statusBadgeVariants> {
  label: string
}

const StatusBadge = React.forwardRef<HTMLDivElement, StatusBadgeProps>(
  ({ 
    className, 
    status = "info", 
    size = "default", 
    showIcon = true,
    label, 
    ...props 
  }, ref) => {
    const IconComponent = iconMap[status!]
    const isProcessing = status === "processing"
    
    return (
      <Badge

        variant="outline"
        className={cn(statusBadgeVariants({ status, size, showIcon, className }))}
        {...props}
      >
        {showIcon && IconComponent && (
          <IconComponent 
            className={cn(
              "h-3 w-3", 
              isProcessing && "animate-spin"
            )} 
          />
        )}
        {label}
      </Badge>
    )
  }
)
StatusBadge.displayName = "StatusBadge"

export { StatusBadge, statusBadgeVariants } 