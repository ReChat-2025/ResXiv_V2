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
import { authApi } from "@/lib/api/auth-api";

interface FormData {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
  acceptedTerms: boolean;
}

interface FormErrors {
  firstName?: string;
  lastName?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  acceptedTerms?: string;
  general?: string;
}

export default function SignupPage() {
  const router = useRouter();
  const config = authConfig.signup;
  
  const [formData, setFormData] = useState<FormData>({
    firstName: "",
    lastName: "",
    email: "",
    password: "",
    confirmPassword: "",
    acceptedTerms: false,
  });
  
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);

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

  // Handle terms acceptance checkbox
  const handleTermsChange = (checked: boolean) => {
    setFormData(prev => ({
      ...prev,
      acceptedTerms: checked,
    }));
    
    if (errors.acceptedTerms) {
      setErrors(prev => ({
        ...prev,
        acceptedTerms: undefined,
      }));
    }
  };

  // Validate form
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    // First name validation
    if (!formData.firstName.trim()) {
      newErrors.firstName = getValidationMessage('required');
    }

    // Last name validation
    if (!formData.lastName.trim()) {
      newErrors.lastName = getValidationMessage('required');
    }

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = getValidationMessage('required');
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = getValidationMessage('email');
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = getValidationMessage('required');
    } else if (formData.password.length < 8) {
      newErrors.password = getValidationMessage('minLength', 8);
    } else {
      // Check password complexity
      const passwordField = config.fields.find(f => f.name === 'password');
      if (passwordField?.validation?.pattern) {
        const regex = new RegExp(passwordField.validation.pattern);
        if (!regex.test(formData.password)) {
          newErrors.password = passwordField.validation.customMessage || 
            'Password must contain uppercase, lowercase, number and special character';
        }
      }
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = getValidationMessage('required');
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = getValidationMessage('passwordMismatch');
    }

    // Terms acceptance validation
    if (!formData.acceptedTerms) {
      newErrors.acceptedTerms = getValidationMessage('termsRequired');
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
      // Combine first and last name for the backend
      const fullName = `${formData.firstName.trim()} ${formData.lastName.trim()}`;
      
      const result = await authApi.register(
        fullName,
        formData.email,
        formData.password,
        formData.confirmPassword,
        formData.acceptedTerms,
        [] // Empty interests array for now
      );

      // Registration successful - show success message or redirect to login
      console.log('Registration successful:', result);
      
      // Check if email verification is required
      if (result.requires_verification) {
        router.push('/Authentication/login?message=verification-required');
      } else {
        router.push('/Authentication/login?message=registration-success');
      }
      
    } catch (error: any) {
      console.error('Registration error:', error);
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
              console.log('Social signup with:', providerId);
              // TODO: Implement social signup
            }}
          />
        </>
      )}

      {/* Signup Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* General Error */}
        {errors.general && (
          <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
            {errors.general}
          </div>
        )}

        {/* Form Fields */}
        <div className="space-y-4">
          {/* First Name & Last Name in Grid */}
          <div className="grid grid-cols-2 gap-4">
            {config.fields
              .filter(field => field.gridColumn)
              .map((field) => (
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

          {/* Other fields (email, password, confirmPassword) */}
          {config.fields
            .filter(field => !field.gridColumn)
            .map((field) => (
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

        {/* Terms and Conditions */}
        {config.features.termsAcceptance.enabled && (
          <div className="space-y-2">
            <div className="flex items-start space-x-2">
              <Checkbox
                id="acceptedTerms"
                checked={formData.acceptedTerms}
                onCheckedChange={handleTermsChange}
                disabled={isLoading}
                className="mt-1"
              />
              <label
                htmlFor="acceptedTerms"
                className="text-sm leading-relaxed peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                {config.features.termsAcceptance.label}{" "}
                <Link
                  href={config.features.termsAcceptance.termsLink.href}
                  className="text-primary hover:underline"
                  target="_blank"
                >
                  {config.features.termsAcceptance.termsLink.text}
                </Link>
                {" "}and{" "}
                <Link
                  href={config.features.termsAcceptance.privacyLink.href}
                  className="text-primary hover:underline"
                  target="_blank"
                >
                  {config.features.termsAcceptance.privacyLink.text}
                </Link>
              </label>
            </div>
            {errors.acceptedTerms && (
              <p className="text-sm text-destructive">{errors.acceptedTerms}</p>
            )}
          </div>
        )}

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