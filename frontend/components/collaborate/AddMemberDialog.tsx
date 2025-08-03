"use client";

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle } from "lucide-react";
import { membersApi, type MemberAdd } from "@/lib/api/members-api";

interface AddMemberDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  onMemberAdded?: () => void;
}

export function AddMemberDialog({
  open,
  onOpenChange,
  projectId,
  onMemberAdded,
}: AddMemberDialogProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"owner" | "admin" | "write" | "read">("read");
  const [message, setMessage] = useState("");
  const [sendInvitation, setSendInvitation] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.trim()) {
      setError("Email is required");
      return;
    }

    if (!projectId) {
      setError("Project ID is required");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const memberData: MemberAdd = {
        email: email.trim(),
        role,
        send_invitation: sendInvitation,
        ...(message.trim() && { message: message.trim() }),
      };

      const response = await membersApi.addProjectMember(projectId, memberData);
      
      if (response.success) {
        // Reset form
        setEmail("");
        setRole("read");
        setMessage("");
        setSendInvitation(true);
        setError(null);
        
        // Close dialog
        onOpenChange(false);
        
        // Trigger refresh
        onMemberAdded?.();
      } else {
        setError(response.error || "Failed to add member");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to add member";
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
        setEmail("");
        setRole("read");
        setMessage("");
        setSendInvitation(true);
        setError(null);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Add Team Member</DialogTitle>
          <DialogDescription>
            Invite a new member to collaborate on this project. They will receive an email invitation.
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
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              placeholder="Enter email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Select value={role} onValueChange={(value: any) => setRole(value)} disabled={isLoading}>
              <SelectTrigger>
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="read">
                  <div className="flex flex-col">
                    <span className="font-medium">Reader</span>
                    <span className="text-sm text-muted-foreground">Can view project content</span>
                  </div>
                </SelectItem>
                <SelectItem value="write">
                  <div className="flex flex-col">
                    <span className="font-medium">Writer</span>
                    <span className="text-sm text-muted-foreground">Can edit and create content</span>
                  </div>
                </SelectItem>
                <SelectItem value="admin">
                  <div className="flex flex-col">
                    <span className="font-medium">Admin</span>
                    <span className="text-sm text-muted-foreground">Can manage project and members</span>
                  </div>
                </SelectItem>
                <SelectItem value="owner">
                  <div className="flex flex-col">
                    <span className="font-medium">Owner</span>
                    <span className="text-sm text-muted-foreground">Full control over project</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="message">Personal Message (Optional)</Label>
            <Textarea
              id="message"
              placeholder="Add a personal message to the invitation..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={isLoading}
              rows={3}
              maxLength={500}
            />
            <div className="text-xs text-muted-foreground text-right">
              {message.length}/500
            </div>
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
            disabled={isLoading}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Send Invitation
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 