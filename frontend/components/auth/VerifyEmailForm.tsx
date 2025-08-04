"use client";

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { authApi } from '@/lib/api/auth-api';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle, XCircle, Mail, AlertTriangle } from 'lucide-react';

type VerifyState = 'loading' | 'success' | 'error' | 'invalid_token';

export default function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [state, setState] = useState<VerifyState>('loading');
  const [token, setToken] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const tokenParam = searchParams.get('token');
    if (!tokenParam) {
      setState('invalid_token');
      setMessage('No verification token provided');
      return;
    }

    setToken(tokenParam);
    
    // Add timeout to prevent infinite loading
    const timeoutId = setTimeout(() => {
      setState('error');
      setMessage('Verification is taking too long. Please try again or check your network connection.');
    }, 10000); // 10 second timeout
    
    verifyEmail(tokenParam).finally(() => {
      clearTimeout(timeoutId);
    });
    
    return () => clearTimeout(timeoutId);
  }, [searchParams]);

  const verifyEmail = async (verificationToken: string) => {
    setState('loading'); // Ensure we're in loading state
    
    try {
      console.log('Starting email verification...');
      const result = await authApi.verifyEmail(verificationToken);
      console.log('Verification successful:', result);
      
      setState('success');
      setMessage(result.message || 'Email verified successfully! Welcome to ResXiv.');
      
      // Redirect to login after success
      setTimeout(() => {
        router.push('/login?message=email-verified');
      }, 4000);
      
    } catch (error: any) {
      console.error('Email verification error details:', {
        error,
        message: error?.message,
        type: typeof error,
        stack: error?.stack
      });
      
      let errorMessage = "Failed to verify email";
      
      if (error && error.message) {
        errorMessage = error.message;
      } else if (error && typeof error === 'string') {
        errorMessage = error;
      }

      console.log('Setting error state with message:', errorMessage);
      
      if (errorMessage.includes('token') || errorMessage.includes('expired') || errorMessage.includes('invalid') || errorMessage.includes('link has expired')) {
        setState('invalid_token');
      } else {
        setState('error');
      }
      setMessage(errorMessage);
    }
  };

  const handleRetryVerification = () => {
    if (token) {
      setState('loading');
      verifyEmail(token);
    }
  };

  const renderContent = () => {
    switch (state) {
      case 'loading':
        return (
          <div className="text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-blue-100 rounded-full flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Verifying your email...</h2>
              <p className="text-sm text-gray-600 mt-2">Please wait while we verify your email address.</p>
            </div>
          </div>
        );

      case 'success':
        return (
          <div className="text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Email verified successfully!</h2>
              <p className="text-sm text-gray-600 mt-2">{message}</p>
              <p className="text-xs text-gray-500 mt-3">Redirecting to login in a few seconds...</p>
            </div>
            <Button
              onClick={() => router.push('/login?message=email-verified')}
              className="w-full"
            >
              Continue to Login
            </Button>
          </div>
        );

      case 'invalid_token':
        return (
          <div className="text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-yellow-100 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-yellow-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Invalid verification link</h2>
              <p className="text-sm text-gray-600 mt-2">{message}</p>
              <p className="text-xs text-gray-500 mt-3">
                The verification link may have expired or is invalid.
              </p>
            </div>
            <div className="space-y-2">
              <Button
                onClick={() => router.push('/signup')}
                className="w-full"
              >
                Register Again
              </Button>
              <Button
                variant="outline"
                onClick={() => router.push('/login')}
                className="w-full"
              >
                Back to Login
              </Button>
            </div>
          </div>
        );

      case 'error':
        return (
          <div className="text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center">
              <XCircle className="w-8 h-8 text-red-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Verification failed</h2>
              <p className="text-sm text-gray-600 mt-2">{message}</p>
            </div>
            <div className="space-y-2">
              <Button
                onClick={handleRetryVerification}
                className="w-full"
              >
                Try Again
              </Button>
              <Button
                variant="outline"
                onClick={() => router.push('/login')}
                className="w-full"
              >
                Back to Login
              </Button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <Mail className="mx-auto h-12 w-12 text-primary" />
          <h1 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
            Email Verification
          </h1>
        </div>
        <div className="bg-card rounded-lg border shadow-sm p-6">
          {renderContent()}
        </div>
      </div>
    </div>
  );
} 