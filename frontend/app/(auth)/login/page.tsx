"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { AuthLayout } from "@/components/auth/auth-layout";
import { FormField } from "@/components/auth/form-field";
import { SocialLogin } from "@/components/auth/social-login";
import { authConfig, getValidationMessage } from "@/lib/auth-config";
import { authService } from "@/lib/services/auth-service";

interface FormData {
  email: string;
  password: string;
  rememberMe: boolean;
}

interface FormErrors {
  email?: string;
  password?: string;
  general?: string;
}

export default function LoginPage() {
  const router = useRouter();
  const config = authConfig.login;
  
  const [formData, setFormData] = useState<FormData>({
    email: "",
    password: "",
    rememberMe: false,
  });
  
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string>("");

  // Check for success messages from URL params
  React.useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    
    switch (message) {
      case 'registration-success':
        setSuccessMessage('Registration successful! Please log in with your credentials.');
        break;
      case 'verification-required':
        setSuccessMessage('Registration successful! Please check your email to verify your account before logging in.');
        break;
      case 'password-reset':
        setSuccessMessage('Password reset successful! You can now log in with your new password.');
        break;
      case 'email-verified':
        setSuccessMessage('Email verified successfully! You can now log in to your account.');
        break;
      default:
        break;
    }
  }, []);

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

  // Handle remember me checkbox
  const handleRememberMeChange = (checked: boolean) => {
    setFormData(prev => ({
      ...prev,
      rememberMe: checked,
    }));
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

    // Password validation
    if (!formData.password) {
      newErrors.password = getValidationMessage('required');
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
      const result = await authService.login(
        formData.email,
        formData.password,
        formData.rememberMe
      );

      // Redirect to projects page or intended destination
      const redirectTo = new URLSearchParams(window.location.search).get('redirect') || '/projects';
      router.push(redirectTo);
      
    } catch (error: any) {
      console.error('Login error:', error);
      setErrors({
        general: error.message || getValidationMessage('genericError'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title={config.title}
      cardTitle={config.cardTitle}
      links={config.links}
    >
      {/* Social Login */}
      {config.socialLogin.enabled && (
        <>
          <SocialLogin
            providers={config.socialLogin.providers}
            dividerText={config.socialLogin.dividerText}
            onProviderClick={(providerId) => {
              console.log('Social login with:', providerId);
              // TODO: Implement social login
            }}
          />
        </>
      )}

      {/* Login Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Success Message */}
        {successMessage && (
          <div className="p-3 text-sm text-green-800 bg-green-50 border border-green-200 rounded-md">
            {successMessage}
          </div>
        )}

        {/* General Error */}
        {errors.general && (
          <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
            {errors.general}
          </div>
        )}

        {/* Form Fields */}
        <div className="space-y-4">
          {config.fields.map((field) => (
            <FormField
              key={field.id}
              field={field}
              value={formData[field.name as keyof FormData] as string}
              onChange={handleFieldChange}
              disabled={isLoading}
              error={errors[field.name as keyof FormErrors]}
            />
          ))}
        </div>

        {/* Remember Me & Forgot Password */}
        <div className="flex items-center justify-between">
          {config.features.rememberMe.enabled && (
            <div className="flex items-center space-x-2">
              <Checkbox
                id="rememberMe"
                checked={formData.rememberMe}
                onCheckedChange={handleRememberMeChange}
                disabled={isLoading}
              />
              <label
                htmlFor="rememberMe"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                {config.features.rememberMe.label}
              </label>
            </div>
          )}

          {config.features.forgotPassword.enabled && (
            <Link
              href="/forgot-password"
              className="text-sm text-primary hover:underline"
            >
              {config.features.forgotPassword.text}
            </Link>
          )}
        </div>

        {/* Submit Button */}
        <Button
          type="submit"
          className="w-full"
          disabled={isLoading}
        >
          {isLoading ? config.submitButton.loading : config.submitButton.idle}
        </Button>
      </form>
    </AuthLayout>
  );
} 