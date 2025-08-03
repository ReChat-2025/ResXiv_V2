"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthLayout } from "@/components/auth/auth-layout";
import { authConfig, getValidationMessage } from "@/lib/auth-config";
import { authApi } from "@/lib/api/auth-api";

interface FormData {
  email: string;
}

interface FormErrors {
  email?: string;
  general?: string;
}

export default function ForgotPasswordPage() {
  const router = useRouter();
  
  const [formData, setFormData] = useState<FormData>({
    email: "",
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

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = getValidationMessage('required');
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = getValidationMessage('email');
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
      await authApi.forgotPassword(formData.email);
      setIsSuccess(true);
      
    } catch (error: any) {
      console.error('Forgot password error:', error);
      setErrors({
        general: error.message || getValidationMessage('genericError'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  // If success, show success message
  if (isSuccess) {
    return (
      <AuthLayout
        title="Check your email"
        cardTitle="Reset link sent"
        links={[{
          text: "Remember your password?",
          linkText: "Back to login",
          href: "/Authentication/login"
        }]}
      >
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">Email sent successfully</h3>
            <p className="text-muted-foreground">
              We've sent a password reset link to <strong>{formData.email}</strong>
            </p>
            <p className="text-sm text-muted-foreground">
              Check your email and click the link to reset your password. 
              If you don't see it, check your spam folder.
            </p>
          </div>

          <div className="pt-4">
            <Button 
              variant="outline" 
              onClick={() => setIsSuccess(false)}
              className="w-full"
            >
              Send another email
            </Button>
          </div>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      cardTitle="Reset password"
      links={[{
        text: "Remember your password?",
        linkText: "Back to login",
        href: "/Authentication/login"
      }]}
    >
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground text-center">
          Enter your email address and we'll send you a link to reset your password.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* General Error */}
          {errors.general && (
            <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
              {errors.general}
            </div>
          )}

          {/* Email Field */}
          <div className="space-y-2">
            <Label htmlFor="email">
              Email address <span className="text-destructive">*</span>
            </Label>
            <Input
              id="email"
              name="email"
              type="email"
              required
              value={formData.email}
              onChange={handleFieldChange}
              placeholder="Enter your email address"
              disabled={isLoading}
              className={errors.email ? "border-destructive" : undefined}
            />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email}</p>
            )}
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            disabled={isLoading}
          >
            {isLoading ? "Sending reset link..." : "Send reset link"}
          </Button>
        </form>
      </div>
    </AuthLayout>
  );
} 