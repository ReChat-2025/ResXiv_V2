"use client";

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Loader2, AlertCircle } from 'lucide-react';
import { projectsApi, ProjectCreate, Project } from '@/lib/api/projects-api';

interface CreateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onProjectCreated?: (project: Project) => void;
}

interface FormData {
  name: string;
  description: string;
  is_private: boolean;
}

interface FormErrors {
  name?: string;
  description?: string;
  general?: string;
}

export default function CreateProjectDialog({
  open,
  onOpenChange,
  onProjectCreated,
}: CreateProjectDialogProps) {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    is_private: true,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);

  const handleInputChange = (field: keyof FormData, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear field error when user starts typing
    if (errors[field as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    // Name validation (required)
    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (formData.name.length < 1 || formData.name.length > 200) {
      newErrors.name = 'Project name must be between 1 and 200 characters';
    }

    // Description validation (optional)
    if (formData.description && formData.description.length > 2000) {
      newErrors.description = 'Description must be less than 2000 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      // Prepare project data for API - only send necessary fields
      const projectData: ProjectCreate = {
        name: formData.name.trim(),
        description: formData.description.trim() || null,
        is_private: formData.is_private,
        // Use backend defaults for optional fields
        slug: null,
        repo_url: null,
        access_model: 'role_based', // Use default
      };

      const newProject = await projectsApi.createProject(projectData);
      
      // Reset form
      setFormData({
        name: '',
        description: '',
        is_private: true,
      });

      // Close dialog and notify parent
      onOpenChange(false);
      onProjectCreated?.(newProject);
      
    } catch (error: any) {
      console.error('Create project error:', error);
      
      let errorMessage = 'Failed to create project';
      
      if (error && typeof error === 'object') {
        if (error.message && typeof error.message === 'string') {
          errorMessage = error.message;
        } else if (typeof error === 'string') {
          errorMessage = error;
        }
      }

      // Check for specific validation errors
      if (errorMessage.includes('name') && errorMessage.includes('already exists')) {
        setErrors({ name: 'A project with this name already exists.' });
      } else {
        setErrors({ general: errorMessage });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    // Reset form and close dialog
    setFormData({
      name: '',
      description: '',
      is_private: true,
    });
    setErrors({});
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* General Error */}
          {errors.general && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-red-800">{errors.general}</div>
            </div>
          )}

          {/* Project Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Project Name *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              placeholder="My Research Project"
              disabled={isLoading}
              maxLength={200}
              required
            />
            {errors.name && (
              <p className="text-sm text-red-600">{errors.name}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Describe your project..."
              disabled={isLoading}
              maxLength={2000}
              rows={3}
            />
            {errors.description && (
              <p className="text-sm text-red-600">{errors.description}</p>
            )}
            <p className="text-xs text-gray-500">
              {formData.description.length}/2000 characters
            </p>
          </div>

          {/* Privacy Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="is_private">Private Project</Label>
              <p className="text-xs text-gray-500">
                Private projects are only visible to invited members
              </p>
            </div>
            <Switch
              id="is_private"
              checked={formData.is_private}
              onCheckedChange={(checked) => handleInputChange('is_private', checked)}
              disabled={isLoading}
            />
          </div>
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            onClick={handleSubmit}
            disabled={isLoading || !formData.name.trim()}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Project'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 