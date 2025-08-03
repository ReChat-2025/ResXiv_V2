"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./table"
import { LoadingSpinner } from "./loading-spinner"
import { EmptyState } from "./empty-state"

export interface Column<T = any> {
  key: string
  title: string
  render?: (value: any, item: T, index: number) => React.ReactNode
  className?: string
  sortable?: boolean
  width?: string | number
}

export interface DataTableProps<T = any> {
  data: T[]
  columns: Column<T>[]
  loading?: boolean
  emptyStateProps?: {
    title: string
    description?: string
    icon?: string
  }
  onRowClick?: (item: T, index: number) => void
  rowClassName?: (item: T, index: number) => string
  className?: string
}

function DataTable<T = any>({
  data,
  columns,
  loading = false,
  emptyStateProps = {
    title: "No data available",
    description: "There's no data to display at the moment.",
  },
  onRowClick,
  rowClassName,
  className,
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <LoadingSpinner text="Loading data..." />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-lg border">
        <EmptyState
          icon="file"
          title={emptyStateProps.title}
          description={emptyStateProps.description}
          size="sm"
        />
      </div>
    )
  }

  return (
    <div className={cn("rounded-md border", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead
                key={column.key}
                className={column.className}
                style={{ width: column.width }}
              >
                {column.title}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((item, index) => (
            <TableRow
              key={index}
              className={cn(
                onRowClick && "cursor-pointer hover:bg-muted/50",
                rowClassName?.(item, index)
              )}
              onClick={() => onRowClick?.(item, index)}
            >
              {columns.map((column) => {
                const value = (item as any)[column.key]
                return (
                  <TableCell
                    key={column.key}
                    className={column.className}
                  >
                    {column.render ? column.render(value, item, index) : value}
                  </TableCell>
                )
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

export { DataTable } 