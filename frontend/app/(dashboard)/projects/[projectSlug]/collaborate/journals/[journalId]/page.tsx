"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/ui/icon";
import { useToast } from "@/hooks/use-toast";
import { journalsApi, type JournalResponse, type JournalUpdate } from "@/lib/api/journals-api";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";



export default function JournalEditorPage() {
  const params = useParams<{ projectSlug: string; journalId: string }>();
  const router = useRouter();
  
  // Type-safe parameter extraction
  const projectSlug = params.projectSlug || '';
  const journalId = params.journalId || '';
  const { toast } = useToast();
  
  const [journal, setJournal] = useState<JournalResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [status, setStatus] = useState<'draft' | 'published' | 'archived'>('draft');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  const contentRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLInputElement>(null);

  // Load journal data
  useEffect(() => {
    const loadJournal = async () => {
      try {
        setIsLoading(true);
        
        // Debug logging
        console.log('Loading journal with ID:', journalId);
        console.log('Project slug:', projectSlug);
        
        // Validate journal ID format (should be UUID)
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
        if (!uuidRegex.test(journalId)) {
          throw new Error('Invalid journal ID format');
        }
        
        // Get project ID from slug - we need to resolve the project first
        let projectId: string | null = null;
        try {
          console.log('Resolving project ID from slug...');
          // Import here to avoid circular dependencies
          const { projectsApi } = await import('@/lib/api/projects-api');
          const projectsResponse = await projectsApi.getProjects();
          const project = projectsResponse.projects.find((p: any) => 
            p.slug === projectSlug || p.id === projectSlug
          );
          
          if (!project) {
            throw new Error('Project not found');
          }
          
          projectId = project.id;
          console.log('Resolved project ID:', projectId);
        } catch (projectError) {
          console.error('Failed to resolve project:', projectError);
          throw new Error('Failed to find project');
        }
        
        // Now load journal within project context
        const journalData = await journalsApi.getProjectJournal(projectId, journalId);
        
        console.log('Journal loaded successfully:', journalData.title);
        
        setJournal(journalData);
        setTitle(journalData.title || "");
        setContent(journalData.content || "");
        setIsPublic(journalData.is_public || false);
        setStatus(journalData.status as 'draft' | 'published' | 'archived' || 'draft');
      } catch (error) {
        console.error('Error loading journal:', error);
        
        // Handle specific error types
        if (error instanceof Error) {
          const errorMessage = error.message;
          
          if (errorMessage.includes('Journal not found in this project')) {
            toast({
              variant: "destructive",
              title: "Journal Not Found",
              description: "This journal doesn't exist in this project or you don't have access to it.",
            });
          } else if (errorMessage.includes('Failed to get journal') || errorMessage.includes('500')) {
            toast({
              variant: "destructive",
              title: "Server Error",
              description: "There was a server error accessing this journal. Please try again later.",
            });
          } else if (errorMessage.includes('Invalid journal ID format')) {
            toast({
              variant: "destructive",
              title: "Invalid Journal Link",
              description: "The journal link appears to be invalid.",
            });
          } else if (errorMessage.includes('Authentication required')) {
            toast({
              variant: "destructive",
              title: "Authentication Required",
              description: "Please log in to access this journal.",
            });
          } else if (errorMessage.includes('Project not found') || errorMessage.includes('Failed to find project')) {
            toast({
              variant: "destructive",
              title: "Project Not Found",
              description: "The project for this journal could not be found.",
            });
          } else {
            toast({
              variant: "destructive",
              title: "Error",
              description: "Failed to load journal. Please try again.",
            });
          }
        }
        
        // Navigate back to collaborate page after a short delay
        setTimeout(() => {
          router.push(`/projects/${projectSlug}/collaborate`);
        }, 2000);
      } finally {
        setIsLoading(false);
      }
    };

    if (journalId && projectSlug) {
      loadJournal();
    } else {
      setIsLoading(false);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Missing journal or project information.",
      });
      router.push(`/projects/${projectSlug}/collaborate`);
    }
  }, [journalId, projectSlug, router, toast]);

  // Track changes
  useEffect(() => {
    if (journal && !isLoading) {
      const hasChanges = 
        title !== (journal.title || "") ||
        content !== (journal.content || "") ||
        isPublic !== (journal.is_public || false) ||
        status !== (journal.status || 'draft');
      setHasUnsavedChanges(hasChanges);
    }
  }, [title, content, isPublic, status, journal, isLoading]);

  // Handle saving
  const handleSave = async () => {
    if (!journal || !hasUnsavedChanges) return;
    
    try {
      setIsSaving(true);
      
      const updateData: JournalUpdate = {
        title: title.trim() || null,
        content: content || null,
        is_public: isPublic,
        status: status,
      };

      const updatedJournal = await journalsApi.updateJournal(journal.id, updateData);
      setJournal(updatedJournal);
      setHasUnsavedChanges(false);
      
      toast({
        title: "Success",
        description: "Journal saved successfully!",
      });
    } catch (error) {
      console.error('Error saving journal:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to save journal. Please try again.",
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Format content as user types
  const handleContentChange = (e: React.FormEvent<HTMLDivElement>) => {
    const newContent = e.currentTarget.textContent || "";
    setContent(newContent);
  };

  // Apply formatting to selected text
  const applyFormatting = (command: string, value?: string) => {
    document.execCommand(command, false, value);
    if (contentRef.current) {
      contentRef.current.focus();
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 's':
          e.preventDefault();
          handleSave();
          break;
        case 'b':
          e.preventDefault();
          applyFormatting('bold');
          break;
        case 'i':
          e.preventDefault();
          applyFormatting('italic');
          break;
        case 'u':
          e.preventDefault();
          applyFormatting('underline');
          break;
      }
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading journal...</p>
        </div>
      </div>
    );
  }

  if (!journal) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Icon name="Warning" size={48} className="mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">Journal not found.</p>
          <Button 
            variant="outline" 
                            onClick={() => router.push(`/projects/${projectSlug}/collaborate`)}
            className="mt-4"
          >
            Back to Collaborate
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Breadcrumb */}
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <button
                onClick={() => router.push(`/projects/${projectSlug}/collaborate`)}
                className="hover:text-foreground transition-colors"
              >
                All Journals
              </button>
              <span>/</span>
              <span className="text-foreground font-medium truncate max-w-[200px]">
                {title || "Untitled"}
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center space-x-3">
              <Badge variant={isPublic ? "default" : "secondary"}>
                {isPublic ? "Public" : "Private"}
              </Badge>
              
              <Button
                onClick={handleSave}
                disabled={!hasUnsavedChanges || isSaving}
                className="bg-primary hover:bg-primary/90"
              >
                {isSaving ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Saving...
                  </>
                ) : (
                  "Save"
                )}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Editor Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Settings Bar */}
        <div className="flex items-center justify-between mb-6 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">Status:</label>
              <Select value={status} onValueChange={(value: 'draft' | 'published' | 'archived') => setStatus(value)}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="published">Published</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">Visibility:</label>
              <Select value={isPublic ? "public" : "private"} onValueChange={(value) => setIsPublic(value === "public")}>
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="private">Private</SelectItem>
                  <SelectItem value="public">Public</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="text-sm text-muted-foreground">
            {hasUnsavedChanges && <span className="text-orange-600">• Unsaved changes</span>}
          </div>
        </div>

        {/* Formatting Toolbar */}
        <div className="flex items-center space-x-1 p-2 border border-border rounded-t-lg bg-background">
          <Select defaultValue="paragraph">
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="paragraph">Paragraph</SelectItem>
              <SelectItem value="heading1">Heading 1</SelectItem>
              <SelectItem value="heading2">Heading 2</SelectItem>
              <SelectItem value="heading3">Heading 3</SelectItem>
            </SelectContent>
          </Select>

          <Separator orientation="vertical" className="h-6 mx-2" />

                     <Button
             variant="ghost"
             size="sm"
             onClick={() => applyFormatting('bold')}
             className="p-2"
           >
             <strong>B</strong>
           </Button>
           
           <Button
             variant="ghost"
             size="sm"
             onClick={() => applyFormatting('italic')}
             className="p-2"
           >
             <em>I</em>
           </Button>
           
           <Button
             variant="ghost"
             size="sm"
             onClick={() => applyFormatting('underline')}
             className="p-2"
           >
             <u>U</u>
           </Button>

          <Separator orientation="vertical" className="h-6 mx-2" />

                     <Button
             variant="ghost"
             size="sm"
             onClick={() => applyFormatting('insertUnorderedList')}
             className="p-2"
           >
             <Icon name="List" size={16} />
           </Button>
           
           <Button
             variant="ghost"
             size="sm"
             onClick={() => applyFormatting('insertOrderedList')}
             className="p-2"
           >
             <span className="font-mono text-sm">1.</span>
           </Button>

          <Separator orientation="vertical" className="h-6 mx-2" />

                     <Button
             variant="ghost"
             size="sm"
             className="p-2"
           >
             <Icon name="Paperclip" size={16} />
             <span className="ml-1 text-sm">Attach PDF</span>
           </Button>
        </div>

        {/* Title Editor */}
        <Input
          ref={titleRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Untitled"
          className="text-3xl font-bold border-0 border-b border-border rounded-none px-0 py-4 focus:ring-0 focus:border-primary bg-transparent"
          onKeyDown={handleKeyDown}
        />

        {/* Content Editor */}
        <div
          ref={contentRef}
          contentEditable
          className="min-h-[400px] p-4 border border-border border-t-0 rounded-b-lg focus:outline-none focus:ring-2 focus:ring-primary/20 bg-background"
          style={{ whiteSpace: 'pre-wrap' }}
          onInput={handleContentChange}
          onKeyDown={handleKeyDown}
          suppressContentEditableWarning={true}
          dangerouslySetInnerHTML={{ __html: content }}
        />

        {/* Footer */}
        <div className="mt-8 pt-4 border-t border-border text-sm text-muted-foreground">
          <div className="flex items-center justify-between">
            <div>
              Created by {journal.creator_name || journal.created_by || 'Unknown'} • 
              {journal.created_at && (
                <span> {new Date(journal.created_at).toLocaleDateString()}</span>
              )}
            </div>
            <div>
              Version {journal.version || 1}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 