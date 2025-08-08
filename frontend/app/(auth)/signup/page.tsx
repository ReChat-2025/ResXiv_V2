"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { AuthLayout } from "@/components/auth/auth-layout";
import { FormField } from "@/components/auth/form-field";
import { SocialLogin } from "@/components/auth/social-login";
import { useSignupForm } from "@/hooks/useSignupForm";
import { authApi } from "@/lib/api/auth-api";

export default function SignupPage() {
  const {
    formData,
    errors,
    isLoading,
    config,
    handleFieldChange,
    handleRememberMeChange,
    handleSubmit,
    setErrors,
  } = useSignupForm();

  return (
    <AuthLayout
      title={config.title}
      cardTitle={config.cardTitle}
      links={config.links}
    >
      {config.socialLogin.enabled && (
        <SocialLogin
          providers={config.socialLogin.providers}
          dividerText={config.socialLogin.dividerText}
          disabled={isLoading}
          onProviderClick={async (providerId) => {
            try {
              setIsLoading(true);
              const result = await authApi.initiateSocialLogin(providerId);
              // Redirect to social provider's auth URL
              window.location.href = result.authUrl;
            } catch (error: any) {
              console.error('Social signup error:', error);
              setErrors({
                general: error.message || 'Social signup failed. Please try again.'
              });
            } finally {
              setIsLoading(false);
            }
          }}
        />
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {errors.general && (
          <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
            {errors.general}
          </div>
        )}

        <div className="space-y-4">
          {config.fields.map((field) => (
            <FormField
              key={field.id}
              field={field}
              value={formData[field.name as keyof typeof formData] as string}
              onChange={handleFieldChange}
              disabled={isLoading}
              error={errors[field.name as keyof typeof errors]}
            />
          ))}
        </div>

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
                className="text-sm font-medium leading-none"
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

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading
            ? config.submitButton.loading
            : config.submitButton.idle}
        </Button>
      </form>
    </AuthLayout>
  );
}
