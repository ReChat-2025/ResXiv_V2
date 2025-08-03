"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Icon } from "@/components/ui/icon";
import { appConfig } from "@/lib/config/app-config";
import { mockTasks, type Task, type TaskAssignee } from "@/lib/config/data-config";

interface TasksAreaProps {
  tasks?: Task[];
  onCreateTask?: () => void;
  onSortChange?: (sort: string) => void;
  onFilterChange?: (filter: string) => void;
  onTaskClick?: (taskId: string) => void;
  className?: string;
  title?: string;
  showCreateButton?: boolean;
  maxVisibleAssignees?: number;
}

interface SortOption {
  id: string;
  label: string;
}

interface FilterOption {
  id: string;
  label: string;
  value: string;
}

export function TasksArea({
  tasks,
  onCreateTask,
  onSortChange,
  onFilterChange,
  onTaskClick,
  className = "",
  title = "Tasks",
  showCreateButton = true,
  maxVisibleAssignees
}: TasksAreaProps) {
  const [selectedSort, setSelectedSort] = useState("Due Date");
  const [selectedFilter, setSelectedFilter] = useState("All");

  // Get configuration values
  const config = appConfig;
  const maxAssignees = maxVisibleAssignees ?? config.features.maxVisibleAvatars;
  const displayTasks = tasks ?? mockTasks;

  const handleSortChange = (sort: string) => {
    setSelectedSort(sort);
    onSortChange?.(sort);
  };

  const handleFilterChange = (filter: string) => {
    setSelectedFilter(filter);
    onFilterChange?.(filter);
  };

  const handleTaskClick = (taskId: string) => {
    onTaskClick?.(taskId);
  };

  const handleCreateTask = () => {
    onCreateTask?.();
  };

  // Configuration for sort and filter options
  const sortOptions: SortOption[] = [
    { id: "due_date", label: "Due Date" },
    { id: "name", label: "Task Name" },
    { id: "status", label: "Status" },
    { id: "priority", label: "Priority" },
    { id: "assignee", label: "Assignee" }
  ];

  const filterOptions: FilterOption[] = [
    { id: "all", label: "All", value: "all" },
    { id: "not_started", label: "Not Started", value: "not_started" },
    { id: "in_progress", label: "In Progress", value: "in_progress" },
    { id: "done", label: "Done", value: "done" },
    { id: "cancelled", label: "Cancelled", value: "cancelled" }
  ];

  const getStatusConfig = (status: Task['status']) => {
    const statusConfigs = {
      not_started: { 
        label: "Not Started", 
        icon: "Circle",
        className: "text-gray-600 bg-beige-100 hover:bg-beige-100"
      },
      in_progress: { 
        label: "In Progress", 
        icon: "Clock",
        className: "text-yellow-700 bg-yellow-100 hover:bg-yellow-100"
      },
      done: { 
        label: "Done", 
        icon: "CheckCircle",
        className: "text-green-700 bg-green-100 hover:bg-green-100"
      },
      cancelled: { 
        label: "Cancelled", 
        icon: "XCircle",
        className: "text-red-700 bg-red-100 hover:bg-red-100"
      }
    };

    return statusConfigs[status] || statusConfigs.not_started;
  };

  const getStatusBadge = (status: Task['status']) => {
    const config = getStatusConfig(status);
    return (
      <div className="flex items-center gap-2">
        <Icon 
          name={config.icon as any} 
          size={16} 
          weight="regular" 
          className={config.className.split(' ')[0]}
        />
        <span className={`text-sm font-medium ${config.className.split(' ')[0]}`}>
          {config.label}
        </span>
      </div>
    );
  };

  const renderAssignees = (assignees: TaskAssignee[]) => {
    const visibleAssignees = assignees.slice(0, maxAssignees);
    const remainingCount = Math.max(0, assignees.length - maxAssignees);

    return (
      <div className="flex items-center gap-1">
        <div className="flex -space-x-2">
          {visibleAssignees.map((assignee) => (
            <Avatar key={assignee.id} className="h-8 w-8 border-2 border-card">
              <AvatarImage src={assignee.avatar} alt={assignee.name} />
              <AvatarFallback className="text-xs bg-beige-100 font-medium text-gray-700">
                {assignee.fallback}
              </AvatarFallback>
            </Avatar>
          ))}
        </div>
        {remainingCount > 0 && (
          <span className="text-sm text-gray-600 ml-2">
            +{remainingCount}
          </span>
        )}
      </div>
    );
  };

  const tableColumns = [
    { id: "name", label: "Task Name" },
    { id: "status", label: "Status" },
    { id: "assignee", label: "Assignee" },
    { id: "due_date", label: "Due date" },
    { id: "time", label: "Time" }
  ];

  return (
    <div className={`flex-1 flex flex-col bg-card ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-gray-800">{title}</h1>
          
          <div className="flex items-center gap-2">
            {/* Sort Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2 h-10 border-border hover:bg-accent">
                  Sort
                  <Icon name="CaretDown" size={16} weight="regular" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="bg-card border-border">
                {sortOptions.map((option) => (
                  <DropdownMenuItem
                    key={option.id}
                    onClick={() => handleSortChange(option.label)}
                    className="text-gray-700 hover:bg-accent"
                  >
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Filter Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2 h-10 border-border hover:bg-accent">
                  Filter
                  <Icon name="CaretDown" size={16} weight="regular" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="bg-card border-border">
                {filterOptions.map((option) => (
                  <DropdownMenuItem
                    key={option.id}
                    onClick={() => handleFilterChange(option.label)}
                    className="text-gray-700 hover:bg-accent"
                  >
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Create Button */}
            {showCreateButton && (
              <Button 
                onClick={handleCreateTask}
                className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2 rounded-lg h-10"
              >
                <Icon name="Plus" size={16} weight="regular" />
                Create
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Tasks Table */}
      <div className="flex-1 overflow-y-auto">
        {displayTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6">
            <Icon name="CheckSquare" size={64} weight="light" className="mb-4 text-gray-400" />
            <h3 className="text-xl font-semibold text-gray-800 mb-2">No tasks yet</h3>
            <p className="text-gray-600 mb-6">Create your first task to get started</p>
            {showCreateButton && (
              <Button onClick={handleCreateTask} className="bg-primary hover:bg-primary/90 text-primary-foreground">
                Create your first task
              </Button>
            )}
          </div>
        ) : (
          <div className="p-6">
            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  {tableColumns.map((column) => (
                    <TableHead key={column.id} className="text-gray-600 font-medium">
                      {column.label}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayTasks.map((task) => (
                  <TableRow 
                    key={task.id} 
                    className="border-border hover:bg-accent/50 transition-colors cursor-pointer"
                    onClick={() => handleTaskClick(task.id)}
                  >
                    <TableCell className="font-medium text-gray-800 py-4">
                      <div>
                        <div className="font-medium">{task.name}</div>
                        {task.description && (
                          <div className="text-sm text-gray-600 mt-1 line-clamp-1">
                            {task.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="py-4">
                      {getStatusBadge(task.status)}
                    </TableCell>
                    <TableCell className="py-4">
                      {renderAssignees(task.assignees)}
                    </TableCell>
                    <TableCell className="text-gray-600 py-4">
                      {task.dueDate}
                    </TableCell>
                    <TableCell className="text-gray-600 py-4">
                      {task.timeRange || "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
} 