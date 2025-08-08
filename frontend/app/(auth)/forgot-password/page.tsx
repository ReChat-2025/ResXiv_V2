"use client";

import { useForgotPasswordForm } from "@/hooks/useForgotPasswordForm";
import { AuthLayout } from "@/components/auth/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// Success view component
function SuccessView({ email, onResend }: { email: string; onResend: () => void }) {
  return (
    <AuthLayout 
      title="Check your email" 
      cardTitle="Reset link sent" 
      links={[{
        text: "Remember your password?",
        linkText: "Back to login",
        href: "/login"
      }]}
    >
      <div className="text-center space-y-4">
        <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26c.3.16.67.16.97 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Reset link sent</h3>
          <p className="text-muted-foreground">
            We've sent a password reset link to <strong>{email}</strong>
          </p>
          <p className="text-sm text-muted-foreground">
            Check your email and click the link to reset your password. The link will expire in 30 minutes.
          </p>
        </div>

        <div className="pt-4">
          <Button 
            variant="outline" 
            onClick={onResend}
            className="w-full"
          >
            Didn't receive the email? Send again
          </Button>
        </div>
      </div>
    </AuthLayout>
  );
}

export default function ForgotPasswordPage() {
  const {
    formData,
    errors,
    isLoading,
    isSuccess,
    handleFieldChange,
    handleSubmit,
    setIsSuccess,
  } = useForgotPasswordForm();

  if (isSuccess) {
    return <SuccessView email={formData.email} onResend={() => setIsSuccess(false)} />;
  }

  const links = [
    {
      text: "Remember your password?",
      linkText: "Back to login",
      href: "/login"
    }
  ];

  return (
    <AuthLayout title="Forgot your password?" cardTitle="Reset password" links={links}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* General Error */}
        {errors.general && (
          <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
            {errors.general}
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="email">Email address</Label>
          <Input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleFieldChange}
            disabled={isLoading}
            placeholder="Enter your email address"
            className={errors.email ? 'border-destructive' : ''}
          />
          {errors.email && (
            <p className="text-sm text-destructive">{errors.email}</p>
          )}
          <p className="text-sm text-muted-foreground">
            We'll send you a link to reset your password.
          </p>
        </div>

        <Button 
          type="submit" 
          disabled={isLoading}
          className="w-full"
        >
          {isLoading ? 'Sending...' : 'Send reset link'}
        </Button>
      </form>
    </AuthLayout>
  );
}
