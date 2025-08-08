"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { AuthLayout } from "@/components/auth/auth-layout";
import { authConfig, getValidationMessage } from "@/lib/auth-config";
import { authApi } from "@/lib/api/auth-api";

interface FormData {
  newPassword: string;
  confirmNewPassword: string;
}

interface FormErrors {
  newPassword?: string;
  confirmNewPassword?: string;
  general?: string;
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resetToken = searchParams.get('token');
  
  const [formData, setFormData] = useState<FormData>({
    newPassword: "",
    confirmNewPassword: "",
  });
  
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);

  // Validate token on component mount
  useEffect(() => {
    const validateToken = async () => {
      if (!resetToken) {
        setTokenValid(false);
        setErrors({ general: 'Invalid or missing reset token' });
        return;
      }

      try {
        await authApi.validateResetToken(resetToken);
        setTokenValid(true);
      } catch (error: any) {
        console.error('Token validation error:', error);
        setTokenValid(false);
        setErrors({ 
          general: error.message || 'Invalid or expired reset token' 
        });
      }
    };

    validateToken();
  }, [resetToken]);

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

    // Password validation
    if (!formData.newPassword) {
      newErrors.newPassword = getValidationMessage('required');
    } else if (formData.newPassword.length < 8) {
      newErrors.newPassword = getValidationMessage('minLength', 8);
    } else {
      // Check password complexity (same as signup)
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

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm() || !resetToken) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      await authApi.resetPassword(
        resetToken,
        formData.newPassword,
        formData.confirmNewPassword
      );
      setIsSuccess(true);
      
    } catch (error: any) {
      console.error('Reset password error:', error);
      setErrors({
        general: error.message || getValidationMessage('genericError'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  // If no token or invalid token
  if (tokenValid === false) {
    return (
      <AuthLayout
        title="Invalid reset link"
        cardTitle="Reset link expired"
        links={[{
          text: "Need a new reset link?",
          linkText: "Request password reset",
          href: "/forgot-password"
        }]}
      >
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">Reset link is invalid</h3>
            <p className="text-muted-foreground">
              This password reset link is invalid or has expired.
            </p>
            <p className="text-sm text-muted-foreground">
              Please request a new password reset link to continue.
            </p>
          </div>
        </div>
      </AuthLayout>
    );
  }

  // If success, show success message
  if (isSuccess) {
    return (
      <AuthLayout
        title="Password reset successful"
        cardTitle="Password updated"
        links={[{
          text: "Continue to",
          linkText: "Login",
          href: "/login"
        }]}
      >
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">Password updated successfully</h3>
            <p className="text-muted-foreground">
              Your password has been reset successfully. You can now log in with your new password.
            </p>
          </div>

          <div className="pt-4">
            <Button 
              onClick={() => router.push('/login?message=password-reset')}
              className="w-full"
            >
              Continue to login
            </Button>
          </div>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Reset your password"
      cardTitle="Create new password"
      links={[{
        text: "Remember your password?",
        linkText: "Back to login",
        href: "/login"
      }]}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* General Error */}
        {errors.general && (
          <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
            {errors.general}
          </div>
        )}

        {/* New Password */}
        <div className="space-y-2">
          <Label htmlFor="newPassword">New Password</Label>
          <PasswordInput
            id="newPassword"
            name="newPassword"
            value={formData.newPassword}
            onChange={handleFieldChange}
            disabled={isLoading}
            placeholder="Enter your new password"
            className={errors.newPassword ? 'border-destructive' : ''}
          />
          {errors.newPassword && (
            <p className="text-sm text-destructive">{errors.newPassword}</p>
          )}
        </div>

        {/* Confirm New Password */}
        <div className="space-y-2">
          <Label htmlFor="confirmNewPassword">Confirm New Password</Label>
          <PasswordInput
            id="confirmNewPassword"
            name="confirmNewPassword"
            value={formData.confirmNewPassword}
            onChange={handleFieldChange}
            disabled={isLoading}
            placeholder="Confirm your new password"
            className={errors.confirmNewPassword ? 'border-destructive' : ''}
          />
          {errors.confirmNewPassword && (
            <p className="text-sm text-destructive">{errors.confirmNewPassword}</p>
          )}
        </div>

        {/* Submit Button */}
        <Button 
          type="submit" 
          disabled={isLoading}
          className="w-full"
        >
          {isLoading ? 'Resetting...' : 'Reset Password'}
        </Button>
      </form>
    </AuthLayout>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <AuthLayout title="Loading..." cardTitle="Loading..." links={[]}>
        <div className="flex justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </AuthLayout>
    }>
      <ResetPasswordForm />
    </Suspense>
  );
} 