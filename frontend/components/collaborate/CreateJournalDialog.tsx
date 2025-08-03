"use client";

import React, { useState } from "react";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle } from "lucide-react";
import { journalsApi, type JournalCreate } from "@/lib/api/journals-api";

interface CreateJournalDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  onJournalCreated?: () => void;
}

export function CreateJournalDialog({ 
  open, 
  onOpenChange, 
  projectId, 
  onJournalCreated 
}: CreateJournalDialogProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [tags, setTags] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!title.trim()) {
      setError("Journal title is required");
      return;
    }

    if (!projectId || projectId.trim() === '') {
      setError("Project ID is required");
      return;
    }

    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(projectId)) {
      setError("Invalid project ID format");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const journalData: JournalCreate = {
        title: title.trim(),
        content: content.trim() || "",
        is_public: isPublic,
        status: 'draft',
        tags: tags.trim() ? tags.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0) : null,
      };

      await journalsApi.createJournal(projectId, journalData);
      
      // Reset form
      setTitle("");
      setContent("");
      setIsPublic(false);
      setTags("");
      setError(null);
      
      // Close dialog and notify parent
      onOpenChange(false);
      onJournalCreated?.();
      
    } catch (err) {
      console.error('Create journal error:', err);
      console.error('Project ID:', projectId);
      console.error('Journal data:', {
        title: title.trim(),
        content: content.trim() || "",
        is_public: isPublic,
        status: 'draft',
        tags: tags.trim() ? tags.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0) : null,
      });
      
      const errorMessage = err instanceof Error ? err.message : "Failed to create journal";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!isLoading) {
      onOpenChange(newOpen);
      if (!newOpen) {
        // Reset form when closing
        setTitle("");
        setContent("");
        setIsPublic(false);
        setTags("");
        setError(null);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Create New Journal</DialogTitle>
          <DialogDescription>
            Document your research insights and findings in a new journal entry.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="title">Journal Title *</Label>
            <Input
              id="title"
              placeholder="Enter journal title..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="content">Content</Label>
            <Textarea
              id="content"
              placeholder="Write your journal content..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              disabled={isLoading}
              rows={5}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="tags">Tags</Label>
            <Input
              id="tags"
              placeholder="Add tags separated by commas (e.g., research, analysis, ideas)"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="visibility">Visibility</Label>
            <Select value={isPublic ? "public" : "private"} onValueChange={(value) => setIsPublic(value === "public")} disabled={isLoading}>
              <SelectTrigger>
                <SelectValue placeholder="Select visibility" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="private">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                    Private
                  </div>
                </SelectItem>
                <SelectItem value="public">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    Public
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </form>

        <DialogFooter>
          <Button 
            type="button" 
            variant="outline" 
            onClick={() => handleOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button 
            type="submit" 
            onClick={handleSubmit}
            disabled={isLoading || !title.trim()}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create Journal
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 