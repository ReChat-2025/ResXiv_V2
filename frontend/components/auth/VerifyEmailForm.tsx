// components/auth/VerifyEmailForm.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthLayout } from "./auth-layout";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api/auth-api";

interface VerifyEmailFormProps {
  token: string;
}

export default function VerifyEmailForm({ token }: VerifyEmailFormProps) {
  const router = useRouter();
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const handleVerification = async () => {
    setIsVerifying(true);
    
    try {
      const result = await authApi.verifyEmail(token);
      setVerificationResult({
        success: result.success,
        message: result.message || "Email verified successfully!"
      });
      
      if (result.success) {
        // Redirect to login with success message after a delay
        setTimeout(() => {
          router.push('/login?message=email-verified');
        }, 2000);
      }
    } catch (error: any) {
      console.error('Email verification error:', error);
      setVerificationResult({
        success: false,
        message: error.message || "Failed to verify email. Please try again."
      });
    } finally {
      setIsVerifying(false);
    }
  };

  if (verificationResult) {
    return (
      <AuthLayout
        title={verificationResult.success ? "Email verified!" : "Verification failed"}
        cardTitle={verificationResult.success ? "Welcome!" : "Error"}
        links={[{
          text: verificationResult.success ? "Continue to" : "Try again or",
          linkText: "Login",
          href: "/login"
        }]}
      >
        <div className="text-center space-y-4">
          <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center ${
            verificationResult.success 
              ? 'bg-green-100' 
              : 'bg-red-100'
          }`}>
            {verificationResult.success ? (
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
          </div>
          
          <div className="space-y-2">
            <p className={`text-lg font-semibold ${
              verificationResult.success ? 'text-green-800' : 'text-red-800'
            }`}>
              {verificationResult.message}
            </p>
            {verificationResult.success && (
              <p className="text-muted-foreground">
                You can now log in to your account.
              </p>
            )}
          </div>

          {verificationResult.success && (
            <div className="pt-4">
              <Button 
                onClick={() => router.push('/login?message=email-verified')}
                className="w-full"
              >
                Continue to login
              </Button>
            </div>
          )}
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Verify your email"
      cardTitle="Email verification"
      links={[{
        text: "Back to",
        linkText: "Login",
        href: "/login"
      }]}
    >
      <div className="text-center space-y-4">
        <div className="w-16 h-16 mx-auto bg-blue-100 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26c.3.16.67.16.97 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 002 2z" />
          </svg>
        </div>
        
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Verify your email address</h3>
          <p className="text-muted-foreground">
            Click the button below to verify your email address and activate your account.
          </p>
        </div>

        <div className="pt-4">
          <Button 
            onClick={handleVerification}
            disabled={isVerifying}
            className="w-full"
          >
            {isVerifying ? 'Verifying...' : 'Verify Email'}
          </Button>
        </div>
      </div>
    </AuthLayout>
  );
}