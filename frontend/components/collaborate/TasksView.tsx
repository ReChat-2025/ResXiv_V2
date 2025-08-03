"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/ui/icon";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { tasksApi, type TaskResponse } from "@/lib/api/tasks-api";
import { CreateTaskDialog } from "./CreateTaskDialog";
import { EditTaskDialog } from "./EditTaskDialog";
import { useToast } from "@/hooks/use-toast";

interface TasksViewProps {
  projectId: string;
}

export function TasksView({ projectId }: TasksViewProps) {
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<TaskResponse | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await tasksApi.getTasks(projectId);
        setTasks(response.tasks);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load tasks');
        console.error('Error fetching tasks:', err);
      } finally {
        setIsLoading(false);
      }
    };

    if (projectId) {
      fetchTasks();
    }
  }, [projectId]);

  const handleTaskCreated = async () => {
    // Refresh tasks list after creating a new task
    try {
      setError(null);
      const response = await tasksApi.getTasks(projectId);
      setTasks(response.tasks);
      toast({
        title: "Success",
        description: "Task created successfully!"
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh tasks');
      console.error('Error refreshing tasks:', err);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to refresh tasks list"
      });
    }
  };

  const handleTaskUpdated = async () => {
    // Refresh tasks list after updating a task
    try {
      const response = await tasksApi.getTasks(projectId);
      setTasks(response.tasks);
      toast({
        title: "Success",
        description: "Task updated successfully!",
      });
    } catch (err) {
      console.error('Error refreshing tasks:', err);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to refresh tasks list",
      });
    }
  };

  const handleEditTask = (task: TaskResponse) => {
    setSelectedTask(task);
    setIsEditDialogOpen(true);
  };

  const handleDeleteTask = async (task: TaskResponse) => {
    if (!confirm(`Are you sure you want to delete "${task.title}"?`)) {
      return;
    }

    try {
      await tasksApi.deleteTask(projectId, task.id);
      const response = await tasksApi.getTasks(projectId);
      setTasks(response.tasks);
      toast({
        title: "Success",
        description: "Task deleted successfully!",
      });
    } catch (err) {
      console.error('Error deleting task:', err);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to delete task",
      });
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'done': return 'CheckCircle';
      case 'in_progress': return 'Clock';
      case 'review': return 'Eye';
      case 'cancelled': return 'XCircle';
      default: return 'Circle';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'done': return 'text-green-600';
      case 'in_progress': return 'text-blue-600';
      case 'review': return 'text-purple-600';
      case 'cancelled': return 'text-red-600';
      default: return 'text-muted-foreground';
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading tasks...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background">
        <div className="text-center">
          <Icon name="Warning" size={48} className="text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">Error Loading Tasks</h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          <Button onClick={() => window.location.reload()}>
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-background">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Tasks</h1>
            <p className="text-muted-foreground">
              {tasks.length} {tasks.length === 1 ? 'task' : 'tasks'}
            </p>
          </div>
          <Button 
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
            onClick={() => setIsCreateDialogOpen(true)}
          >
            <Icon name="Plus" size={16} className="mr-2" />
            New Task
          </Button>
        </div>
      </div>

      {/* Tasks Table */}
      <div className="flex-1 overflow-auto p-6">
        {tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <Icon name="CheckSquare" size={48} className="text-muted-foreground opacity-50 mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">No tasks yet</h3>
            <p className="text-muted-foreground max-w-sm">
              Create your first task to start organizing your project work.
            </p>
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]">Status</TableHead>
                  <TableHead className="min-w-[200px]">Task</TableHead>
                  <TableHead className="w-[100px]">Priority</TableHead>
                  <TableHead className="w-[120px]">Due Date</TableHead>
                  <TableHead className="w-[100px]">Progress</TableHead>
                  <TableHead className="w-[120px]">Assigned To</TableHead>
                  <TableHead className="w-[100px]">Estimated</TableHead>
                  <TableHead className="w-[120px]">Created</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map((task) => (
                  <TableRow key={task.id} className="hover:bg-muted/50">
                    <TableCell>
                      <Icon 
                        name={getStatusIcon(task.status) as any} 
                        size={16} 
                        className={getStatusColor(task.status)}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <div className="font-medium text-foreground line-clamp-1">
                          {task.title}
                        </div>
                        {task.description && (
                          <div className="text-sm text-muted-foreground line-clamp-1">
                            {task.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant="secondary" 
                        className={`${getPriorityColor(task.priority)} text-white text-xs`}
                      >
                        {task.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {task.due_date ? (
                        <div className="flex items-center gap-1 text-sm">
                          <Icon name="Calendar" size={12} />
                          {formatDate(task.due_date)}
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {task.progress !== undefined && task.progress > 0 ? (
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-primary transition-all"
                              style={{ width: `${task.progress}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground">{task.progress}%</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">0%</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {task.assigned_to ? (
                        <div className="flex items-center gap-2">
                          <Avatar className="h-6 w-6">
                            <AvatarFallback className="text-xs">
                              {task.assigned_to.slice(0, 2).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <span className="text-sm text-muted-foreground">Assigned</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {task.estimated_hours ? (
                        <div className="flex items-center gap-1 text-sm">
                          <Icon name="Clock" size={12} />
                          {task.estimated_hours}h
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {formatDateTime(task.created_at)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditTask(task)}
                          className="h-8 w-8 p-0"
                        >
                          <Icon name="Pencil" size={14} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteTask(task)}
                          className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                        >
                          <Icon name="Trash" size={14} />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Create Task Dialog */}
      <CreateTaskDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        projectId={projectId}
        onTaskCreated={handleTaskCreated}
      />

      {/* Edit Task Dialog */}
      <EditTaskDialog
        open={isEditDialogOpen}
        onOpenChange={setIsEditDialogOpen}
        projectId={projectId}
        task={selectedTask}
        onTaskUpdated={handleTaskUpdated}
      />
    </div>
  );
} 