"use client";

import React from "react";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";

import { JournalResponse } from "@/lib/api/journals-api";

interface JournalViewerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  journal: JournalResponse | null;
  isLoading?: boolean;
}

export function JournalViewerDialog({ 
  open, 
  onOpenChange, 
  journal,
  isLoading = false
}: JournalViewerDialogProps) {
  
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published': return 'text-green-600';
      case 'draft': return 'text-yellow-600';
      case 'archived': return 'text-gray-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'published': return 'CheckCircle';
      case 'draft': return 'Edit';
      case 'archived': return 'Archive';
      default: return 'FileText';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1 mr-4">
              <DialogTitle className="text-xl font-bold">
                {isLoading ? 'Loading...' : journal?.title || 'Untitled Journal'}
              </DialogTitle>
              <DialogDescription className="mt-2">
                {isLoading ? 'Please wait...' : 'Research journal entry'}
              </DialogDescription>
            </div>
            {journal && !isLoading && (
              <div className="flex items-center gap-2">
                <Badge 
                  variant="secondary" 
                  className={`${journal.is_public ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}`}
                >
                  {journal.is_public ? 'Public' : 'Private'}
                </Badge>
                <div className={`flex items-center gap-1 ${getStatusColor(journal.status)}`}>
                  <Icon name={getStatusIcon(journal.status) as any} size={16} />
                  <span className="text-sm font-medium capitalize">{journal.status}</span>
                </div>
              </div>
            )}
          </div>
        </DialogHeader>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading journal...</p>
            </div>
          </div>
        ) : journal ? (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Journal Metadata */}
            <div className="flex flex-wrap items-center gap-4 py-3 border-b border-border text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <Icon name="User" size={14} />
                <span>Created by {journal.creator_name || journal.created_by || 'Unknown'}</span>
              </div>
              <div className="flex items-center gap-1">
                <Icon name="Calendar" size={14} />
                <span>Created {formatDate(journal.created_at)}</span>
              </div>
              {journal.updated_at !== journal.created_at && (
                <div className="flex items-center gap-1">
                  <Icon name="Clock" size={14} />
                  <span>Updated {formatDate(journal.updated_at)}</span>
                </div>
              )}
                             <div className="flex items-center gap-1">
                 <Icon name="Hash" size={14} />
                 <span>Version {journal.version || 1}</span>
               </div>
              {(journal.collaborator_count || 0) > 0 && (
                <div className="flex items-center gap-1">
                  <Icon name="Users" size={14} />
                  <span>{journal.collaborator_count} collaborator{journal.collaborator_count !== 1 ? 's' : ''}</span>
                </div>
              )}
            </div>

            {/* Tags */}
            {journal.tags && Array.isArray(journal.tags) && journal.tags.length > 0 && (
              <div className="py-3 border-b border-border">
                <div className="flex items-center gap-2 flex-wrap">
                  <Icon name="Tag" size={14} className="text-muted-foreground" />
                  {journal.tags.map((tag, index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Journal Content */}
            <div className="flex-1 mt-4 overflow-y-auto">
              <div className="pr-4">
                {journal.content ? (
                  <div className="prose prose-gray max-w-none">
                    <div className="whitespace-pre-wrap text-foreground leading-relaxed">
                      {journal.content}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <Icon name="File" size={48} className="mx-auto mb-4 opacity-50" />
                    <p>No content available for this journal entry.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Footer Actions */}
            <div className="flex justify-between items-center pt-4 border-t border-border">
              <div className="text-sm text-muted-foreground">
                {journal.project_name && (
                  <span>Project: {journal.project_name}</span>
                )}
              </div>
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Close
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center py-12">
            <div className="text-center text-muted-foreground">
              <Icon name="Warning" size={48} className="mx-auto mb-4 opacity-50" />
              <p>Journal not found or failed to load.</p>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
} 