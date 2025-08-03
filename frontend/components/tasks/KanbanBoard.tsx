"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/ui/icon";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { tasksApi, type TaskResponse, type TaskListWithTasks } from "@/lib/api/tasks-api";

interface KanbanBoardProps {
  projectId: string;
}

interface DragItem {
  taskId: string;
  sourceListId: string;
}

export function KanbanBoard({ projectId }: KanbanBoardProps) {
  const [taskLists, setTaskLists] = useState<TaskListWithTasks[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draggedItem, setDraggedItem] = useState<DragItem | null>(null);

  useEffect(() => {
    const fetchTaskLists = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await tasksApi.getTaskLists(projectId);
        
        // Handle the response based on actual API structure
        // The API should return TaskListCollectionResponse { lists: TaskListWithTasks[], total: number }
        if (Array.isArray(response)) {
          // If response is already an array, use it directly
          setTaskLists(response as TaskListWithTasks[]);
        } else if (response && typeof response === 'object' && 'lists' in response) {
          // If response has lists property, extract it
          setTaskLists((response as any).lists);
        } else {
          // Fallback - initialize empty lists
          setTaskLists([]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load task lists');
        console.error('Error fetching task lists:', err);
      } finally {
        setIsLoading(false);
      }
    };

    if (projectId) {
      fetchTaskLists();
    }
  }, [projectId]);

  const handleDragStart = (e: React.DragEvent, taskId: string, sourceListId: string) => {
    setDraggedItem({ taskId, sourceListId });
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e: React.DragEvent, targetListId: string) => {
    e.preventDefault();
    
    if (!draggedItem || draggedItem.sourceListId === targetListId) {
      setDraggedItem(null);
      return;
    }

    try {
      // Update task's list assignment
      await tasksApi.updateTask(projectId, draggedItem.taskId, {
        task_list_id: targetListId
      });

      // Update local state
      setTaskLists(prevLists => {
        const newLists = [...prevLists];
        
        // Find source and target lists
        const sourceList = newLists.find(list => list.id === draggedItem.sourceListId);
        const targetList = newLists.find(list => list.id === targetListId);
        
        if (sourceList && targetList) {
          // Find and remove task from source
          const taskIndex = sourceList.tasks.findIndex(task => task.id === draggedItem.taskId);
          if (taskIndex !== -1) {
            const [task] = sourceList.tasks.splice(taskIndex, 1);
            // Add task to target with updated list_id
            const updatedTask = { ...task, task_list_id: targetListId };
            targetList.tasks.push(updatedTask);
          }
        }
        
        return newLists;
      });
    } catch (err) {
      console.error('Error moving task:', err);
      setError('Failed to move task');
    }
    
    setDraggedItem(null);
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

  const formatDate = (dateString: string | null) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading kanban board...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Icon name="Warning" size={48} className="text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">Error Loading Board</h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          <Button onClick={() => window.location.reload()}>
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-x-auto p-6">
      <div className="flex gap-6 min-w-max h-full">
        {taskLists.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Icon name="Columns" size={48} className="text-muted-foreground opacity-50 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-foreground mb-2">No task lists found</h3>
              <p className="text-muted-foreground mb-4">Create your first task list to get started with the kanban board.</p>
              <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
                <Icon name="Plus" size={16} className="mr-2" />
                Create Task List
              </Button>
            </div>
          </div>
        ) : (
          <>
            {taskLists.map((list) => (
          <div
            key={list.id}
            className="w-80 flex flex-col"
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, list.id)}
          >
            {/* Column Header */}
            <div className="mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {list.color && (
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: list.color }}
                    />
                  )}
                  <h3 className="font-semibold text-foreground">{list.name}</h3>
                  <Badge variant="secondary" className="text-xs">
                    {list.tasks.length}
                  </Badge>
                </div>
                <Button size="sm" variant="ghost">
                  <Icon name="Plus" size={16} />
                </Button>
              </div>
              {list.description && (
                <p className="text-sm text-muted-foreground mt-1">{list.description}</p>
              )}
            </div>

            {/* Tasks Column */}
            <div className="flex-1 space-y-3 min-h-32">
              {list.tasks.map((task) => (
                <Card
                  key={task.id}
                  className="cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow"
                  draggable
                  onDragStart={(e) => handleDragStart(e, task.id, list.id)}
                >
                  <CardContent className="p-4">
                    <div className="space-y-3">
                      {/* Task Header */}
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-medium text-sm text-foreground line-clamp-2 flex-1">
                          {task.title}
                        </h4>
                        <Icon 
                          name={getStatusIcon(task.status) as any} 
                          size={16} 
                          className="text-muted-foreground flex-shrink-0"
                        />
                      </div>

                      {/* Task Description */}
                      {task.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {task.description}
                        </p>
                      )}

                      {/* Task Meta */}
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          {/* Priority */}
                          <div className={`w-2 h-2 rounded-full ${getPriorityColor(task.priority)}`} />
                          
                          {/* Due Date */}
                          {task.due_date && (
                            <div className="flex items-center gap-1 text-muted-foreground">
                              <Icon name="Calendar" size={12} />
                              <span>{formatDate(task.due_date)}</span>
                            </div>
                          )}
                        </div>

                        {/* Progress */}
                        {task.progress !== undefined && task.progress > 0 && (
                          <div className="flex items-center gap-1">
                            <div className="w-12 h-1 bg-muted rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-primary transition-all"
                                style={{ width: `${task.progress}%` }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground">{task.progress}%</span>
                          </div>
                        )}
                      </div>

                      {/* Assignee */}
                      {task.assigned_to && (
                        <div className="flex items-center gap-2">
                          <Avatar className="h-6 w-6">
                            <AvatarFallback className="text-xs">
                              {task.assigned_to.slice(0, 2).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <span className="text-xs text-muted-foreground">Assigned</span>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}

              {/* Empty State */}
              {list.tasks.length === 0 && (
                <div className="flex items-center justify-center h-32 border-2 border-dashed border-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">No tasks</p>
                </div>
              )}
            </div>
          </div>
        ))}

            {/* Add List Column */}
            <div className="w-80 flex-shrink-0">
              <Button
                variant="outline"
                className="w-full h-12 border-dashed"
              >
                <Icon name="Plus" size={16} className="mr-2" />
                Add List
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
} 