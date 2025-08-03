"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getValidationMessage } from "@/lib/auth-config";
import { authApi } from "@/lib/api/auth-api";

interface FormData {
  currentPassword: string;
  newPassword: string;
  confirmNewPassword: string;
}

interface FormErrors {
  currentPassword?: string;
  newPassword?: string;
  confirmNewPassword?: string;
  general?: string;
}

interface ChangePasswordFormProps {
  onSuccess?: () => void;
  className?: string;
}

export function ChangePasswordForm({ onSuccess, className = "" }: ChangePasswordFormProps) {
  const [formData, setFormData] = useState<FormData>({
    currentPassword: "",
    newPassword: "",
    confirmNewPassword: "",
  });
  
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  // Handle form field changes
  const handleFieldChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    
    // Clear field error when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({
        ...prev,
        [name]: undefined,
      }));
    }
  };

  // Validate form
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    // Current password validation
    if (!formData.currentPassword) {
      newErrors.currentPassword = getValidationMessage('required');
    }

    // New password validation
    if (!formData.newPassword) {
      newErrors.newPassword = getValidationMessage('required');
    } else if (formData.newPassword.length < 8) {
      newErrors.newPassword = getValidationMessage('minLength', 8);
    } else {
      // Check password complexity
      const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&].{7,}$/;
      if (!passwordRegex.test(formData.newPassword)) {
        newErrors.newPassword = 'Password must contain uppercase, lowercase, number and special character';
      }
    }

    // Confirm password validation
    if (!formData.confirmNewPassword) {
      newErrors.confirmNewPassword = getValidationMessage('required');
    } else if (formData.newPassword !== formData.confirmNewPassword) {
      newErrors.confirmNewPassword = getValidationMessage('passwordMismatch');
    }

    // Check if new password is different from current
    if (formData.currentPassword && formData.newPassword && formData.currentPassword === formData.newPassword) {
      newErrors.newPassword = 'New password must be different from current password';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      await authApi.changePassword(
        formData.currentPassword,
        formData.newPassword,
        formData.confirmNewPassword
      );
      
      setIsSuccess(true);
      setFormData({
        currentPassword: "",
        newPassword: "",
        confirmNewPassword: "",
      });
      
      if (onSuccess) {
        onSuccess();
      }

      // Auto-hide success message after 3 seconds
      setTimeout(() => {
        setIsSuccess(false);
      }, 3000);
      
    } catch (error: any) {
      console.error('Change password error:', error);
      setErrors({
        general: error.message || getValidationMessage('genericError'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Change Password</CardTitle>
        <CardDescription>
          Update your password to keep your account secure
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Success Message */}
          {isSuccess && (
            <div className="p-3 text-sm text-green-800 bg-green-50 border border-green-200 rounded-md">
              Password changed successfully!
            </div>
          )}

          {/* General Error */}
          {errors.general && (
            <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
              {errors.general}
            </div>
          )}

          {/* Current Password Field */}
          <div className="space-y-2">
            <Label htmlFor="currentPassword">
              Current password <span className="text-destructive">*</span>
            </Label>
            <Input
              id="currentPassword"
              name="currentPassword"
              type="password"
              required
              value={formData.currentPassword}
              onChange={handleFieldChange}
              placeholder="Enter your current password"
              disabled={isLoading}
              className={errors.currentPassword ? "border-destructive" : undefined}
            />
            {errors.currentPassword && (
              <p className="text-sm text-destructive">{errors.currentPassword}</p>
            )}
          </div>

          {/* New Password Field */}
          <div className="space-y-2">
            <Label htmlFor="newPassword">
              New password <span className="text-destructive">*</span>
            </Label>
            <Input
              id="newPassword"
              name="newPassword"
              type="password"
              required
              value={formData.newPassword}
              onChange={handleFieldChange}
              placeholder="Create a strong password"
              disabled={isLoading}
              className={errors.newPassword ? "border-destructive" : undefined}
            />
            {errors.newPassword && (
              <p className="text-sm text-destructive">{errors.newPassword}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Must contain uppercase, lowercase, number and special character
            </p>
          </div>

          {/* Confirm Password Field */}
          <div className="space-y-2">
            <Label htmlFor="confirmNewPassword">
              Confirm new password <span className="text-destructive">*</span>
            </Label>
            <Input
              id="confirmNewPassword"
              name="confirmNewPassword"
              type="password"
              required
              value={formData.confirmNewPassword}
              onChange={handleFieldChange}
              placeholder="Confirm your new password"
              disabled={isLoading}
              className={errors.confirmNewPassword ? "border-destructive" : undefined}
            />
            {errors.confirmNewPassword && (
              <p className="text-sm text-destructive">{errors.confirmNewPassword}</p>
            )}
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isLoading}
            className="w-full sm:w-auto"
          >
            {isLoading ? "Changing password..." : "Change password"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
} 