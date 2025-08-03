"use client";

import React, { useState, useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/ui/icon";
import { journalsApi, type JournalResponse } from "@/lib/api/journals-api";
import { CreateJournalDialog } from "./CreateJournalDialog";
import { JournalViewerDialog } from "./JournalViewerDialog";
import { useToast } from "@/hooks/use-toast";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface JournalsViewProps {
  projectId: string;
}

export function JournalsView({ projectId }: JournalsViewProps) {
  const [journals, setJournals] = useState<JournalResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [visibilityFilter, setVisibilityFilter] = useState<string>("all");
  const [isViewerDialogOpen, setIsViewerDialogOpen] = useState(false);
  const [selectedJournal, setSelectedJournal] = useState<JournalResponse | null>(null);
  const [isLoadingJournal, setIsLoadingJournal] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const fetchJournals = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const params: any = {};
        
        if (searchQuery.trim()) {
          params.query = searchQuery.trim();
        }
        
        if (statusFilter !== "all") {
          params.journal_status = statusFilter;
        }
        
        if (visibilityFilter !== "all") {
          params.is_public = visibilityFilter === "public";
        }
        
        const response = await journalsApi.getJournals(projectId, params);
        setJournals(response.journals);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load journals';
        setError(errorMessage);
        console.error('Error fetching journals:', {
          error: err,
          message: errorMessage,
          projectId,
          searchQuery,
          statusFilter,
          visibilityFilter
        });
      } finally {
        setIsLoading(false);
      }
    };

    if (projectId && projectId.trim() !== '') {
      fetchJournals();
    } else {
      setIsLoading(false);
      setError('No project selected');
    }
  }, [projectId, searchQuery, statusFilter, visibilityFilter]);

  const handleJournalCreated = async () => {
    // Refresh journals list after creating a new journal
    try {
      setError(null);
      const params: any = {};
      
      if (searchQuery.trim()) {
        params.query = searchQuery.trim();
      }
      
      if (statusFilter !== "all") {
        params.journal_status = statusFilter;
      }
      
      if (visibilityFilter !== "all") {
        params.is_public = visibilityFilter === "public";
      }
      
      const response = await journalsApi.getJournals(projectId, params);
      setJournals(response.journals);
      toast({
        title: "Success",
        description: "Journal created successfully!"
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh journals');
      console.error('Error refreshing journals:', err);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to refresh journals list"
      });
    }
  };

  const handleJournalClick = async (journal: JournalResponse) => {
    // Navigate to the journal editor page instead of opening a dialog
    const projectSlug = window.location.pathname.split('/')[2]; // Extract project slug from current URL
    window.location.href = `/projects/${projectSlug}/collaborate/journals/${journal.id}`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published': return 'text-green-600';
      case 'draft': return 'text-yellow-600';
      case 'archived': return 'text-gray-600';
      default: return 'text-muted-foreground';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'published': return 'CheckCircle';
      case 'draft': return 'Edit';
      case 'archived': return 'Archive';
      default: return 'Circle';
    }
  };

  const getVisibilityColor = (isPublic: boolean) => {
    return isPublic ? 'bg-green-500 hover:bg-green-600' : 'bg-blue-500 hover:bg-blue-600';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const truncateContent = (content: string, maxLength: number = 150) => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading journals...</p>
        </div>
      </div>
    );
  }

  if (error) {
    const isAuthError = error.includes('Authentication') || error.includes('authentication');
    const isProjectError = error.includes('Project ID is required') || error.includes('No project selected');
    
    return (
      <div className="flex-1 flex items-center justify-center bg-background">
        <div className="text-center">
          <Icon 
            name={isAuthError ? "User" : isProjectError ? "FolderOpen" : "Warning"} 
            size={48} 
            className={`mx-auto mb-4 ${isAuthError ? 'text-blue-500' : 'text-red-500'}`} 
          />
          <h3 className="text-lg font-medium text-foreground mb-2">
            {isAuthError ? 'Authentication Required' : isProjectError ? 'No Project Selected' : 'Error Loading Journals'}
          </h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          {isAuthError ? (
                          <Button onClick={() => window.location.href = '/auth/login'}>
                Sign In
              </Button>
          ) : isProjectError ? (
            <Button onClick={() => window.location.href = '/projects'}>
              Select Project
            </Button>
          ) : (
            <Button onClick={() => window.location.reload()}>
              Try Again
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-background">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Journals</h1>
            <p className="text-muted-foreground">
              {journals.length} {journals.length === 1 ? 'journal' : 'journals'}
            </p>
          </div>
          <Button 
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
            onClick={() => setIsCreateDialogOpen(true)}
          >
            <Icon name="Plus" size={16} className="mr-2" />
            New Journal
          </Button>
        </div>

        {/* Search and Filters */}
        <div className="flex items-center gap-4">
          <div className="flex-1 max-w-md">
            <Input
              placeholder="Search journals..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-background border-border"
            />
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2 border-border hover:bg-accent">
                Status: {statusFilter === "all" ? "All" : statusFilter}
                <Icon name="CaretDown" size={16} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="bg-card border-border">
              <DropdownMenuItem onClick={() => setStatusFilter("all")}>
                All Statuses
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter("draft")}>
                Draft
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter("published")}>
                Published
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter("archived")}>
                Archived
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2 border-border hover:bg-accent">
                Visibility: {visibilityFilter === "all" ? "All" : visibilityFilter}
                <Icon name="CaretDown" size={16} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="bg-card border-border">
              <DropdownMenuItem onClick={() => setVisibilityFilter("all")}>
                All Visibility
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setVisibilityFilter("private")}>
                Private
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setVisibilityFilter("public")}>
                Public
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {(searchQuery || statusFilter !== "all" || visibilityFilter !== "all") && (
            <Button 
              variant="ghost" 
              onClick={() => {
                setSearchQuery("");
                setStatusFilter("all");
                setVisibilityFilter("all");
              }}
              className="text-muted-foreground hover:text-foreground"
            >
              <Icon name="X" size={16} className="mr-1" />
              Clear Filters
            </Button>
          )}
        </div>
      </div>

      {/* Journals List */}
      <div className="flex-1 overflow-auto p-6">
        {journals.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <Icon name="Book" size={64} className="text-muted-foreground opacity-50 mb-4" />
            <h3 className="text-xl font-semibold text-foreground mb-2">
              {searchQuery || statusFilter !== "all" || visibilityFilter !== "all" 
                ? "No journals match your filters" 
                : "No journals yet"
              }
            </h3>
            <p className="text-muted-foreground max-w-sm mb-6">
              {searchQuery || statusFilter !== "all" || visibilityFilter !== "all"
                ? "Try adjusting your search or filter criteria to find journals."
                : "Create your first journal to start documenting your research insights and findings."
              }
            </p>
            {(!searchQuery && statusFilter === "all" && visibilityFilter === "all") && (
              <Button 
                onClick={() => setIsCreateDialogOpen(true)}
                className="bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                <Icon name="Plus" size={16} className="mr-2" />
                Create your first journal
              </Button>
            )}
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]">Status</TableHead>
                  <TableHead className="min-w-[200px]">Title</TableHead>
                  <TableHead className="w-[100px]">Visibility</TableHead>
                  <TableHead className="w-[120px]">Updated</TableHead>
                  <TableHead className="w-[80px]">Version</TableHead>
                  <TableHead className="w-[100px]">Collaborators</TableHead>
                  <TableHead className="w-[150px]">Tags</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {journals.map((journal) => (
                  <TableRow 
                    key={journal.id} 
                    className="hover:bg-muted/50 cursor-pointer"
                    onClick={() => handleJournalClick(journal)}
                  >
                    <TableCell>
                      <Icon 
                        name={getStatusIcon(journal.status) as any} 
                        size={16} 
                        className={getStatusColor(journal.status)}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <div className="font-medium text-foreground line-clamp-1 hover:text-primary transition-colors">
                          {journal.title}
                        </div>
                        {journal.content && (
                          <div className="text-sm text-muted-foreground line-clamp-1">
                            {truncateContent(journal.content, 80)}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant="secondary" 
                        className={`${getVisibilityColor(journal.is_public)} text-white text-xs`}
                      >
                        {journal.is_public ? 'Public' : 'Private'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm">
                        <Icon name="Calendar" size={12} />
                        {formatDate(journal.updated_at)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm">
                        <Icon name="GitBranch" size={12} />
                        v{journal.version || 1}
                      </div>
                    </TableCell>
                                      <TableCell>
                    {(journal.collaborator_count || 0) > 0 ? (
                      <div className="flex items-center gap-1 text-sm">
                        <Icon name="Users" size={12} />
                        {journal.collaborator_count}
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-sm">—</span>
                    )}
                  </TableCell>
                                      <TableCell>
                    {journal.tags && Array.isArray(journal.tags) && journal.tags.length > 0 ? (
                      <div className="flex items-center gap-1 flex-wrap">
                        {journal.tags.slice(0, 2).map((tag, index) => (
                          <Badge key={index} variant="outline" className="text-xs px-1 py-0.5">
                            {tag}
                          </Badge>
                        ))}
                        {journal.tags.length > 2 && (
                          <Badge variant="outline" className="text-xs px-1 py-0.5">
                            +{journal.tags.length - 2}
                          </Badge>
                        )}
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-sm">—</span>
                    )}
                  </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Create Journal Dialog */}
      <CreateJournalDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        projectId={projectId}
        onJournalCreated={handleJournalCreated}
      />

      {/* Journal Viewer Dialog */}
      <JournalViewerDialog
        open={isViewerDialogOpen}
        onOpenChange={setIsViewerDialogOpen}
        journal={selectedJournal}
        isLoading={isLoadingJournal}
      />
    </div>
  );
} 