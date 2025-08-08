// app/login/page.tsx

"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { AuthLayout } from "@/components/auth/auth-layout";
import { FormField } from "@/components/auth/form-field";
import { SocialLogin } from "@/components/auth/social-login";
import { authConfig } from "@/lib/auth-config";
import { useLoginForm } from "@/hooks/useLoginForm";
import { authApi } from "@/lib/api/auth-api";

export default function LoginPage() {
  const config = authConfig.login;

  const {
    formData,
    handleFieldChange,
    handleRememberMeChange,
    handleSubmit,
    isLoading,
    errors,
    successMessage,
    setErrors,
  } = useLoginForm();

  return (
    <AuthLayout
      title={config.title}
      cardTitle={config.cardTitle}
      links={config.links}
    >
      {/* Social Login */}
      {config.socialLogin.enabled && (
        <SocialLogin
          providers={config.socialLogin.providers}
          dividerText={config.socialLogin.dividerText}
          disabled={isLoading}
          onProviderClick={async (providerId) => {
            try {
              // setIsLoading(true); // Note: setIsLoading is managed by the hook
              const result = await authApi.initiateSocialLogin(providerId);
              // Redirect to social provider's auth URL
              window.location.href = result.authUrl;
            } catch (error: any) {
              console.error('Social login error:', error);
              setErrors({
                general: error.message || 'Social login failed. Please try again.'
              });
            } finally {
              // setIsLoading(false); // Note: setIsLoading is managed by the hook
            }
          }}
        />
      )}

      {/* Login Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {successMessage && (
          <div className="p-3 text-sm text-green-800 bg-green-50 border border-green-200 rounded-md">
            {successMessage}
          </div>
        )}

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
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? config.submitButton.loading : config.submitButton.idle}
        </Button>
      </form>
    </AuthLayout>
  );
}
