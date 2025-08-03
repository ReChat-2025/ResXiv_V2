"use client";

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { authApi } from '@/lib/api/auth-api';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Loader2, CheckCircle, XCircle, Lock } from 'lucide-react';

type ResetState = 'loading' | 'ready' | 'success' | 'error' | 'invalid_token';

export default function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [state, setState] = useState<ResetState>('loading');
  const [token, setToken] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const tokenParam = searchParams.get('token');
    if (!tokenParam) {
      setState('invalid_token');
      setMessage('No reset token provided');
      return;
    }

    setToken(tokenParam);
    setState('ready');
  }, [searchParams]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!newPassword) {
      newErrors.newPassword = 'Password is required';
    } else if (newPassword.length < 8) {
      newErrors.newPassword = 'Password must be at least 8 characters';
    } else if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/.test(newPassword)) {
      newErrors.newPassword = 'Password must contain uppercase, lowercase, number and special character';
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (newPassword !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm() || !token) {
      return;
    }

    setIsLoading(true);
    setErrors({});
    
    try {
      const result = await authApi.resetPassword(token, newPassword, confirmPassword);
      setState('success');
      setMessage(result.message || 'Password reset successfully!');
      
      // Redirect to login after success
      setTimeout(() => {
        router.push('/Authentication/login?message=password_reset');
      }, 3000);
      
    } catch (error: any) {
      console.error('Reset password error:', error);
      
      let errorMessage = "Failed to reset password";
      
      if (error && typeof error === 'object') {
        if (error.message && typeof error.message === 'string') {
          errorMessage = error.message;
        } else if (error.detail && typeof error.detail === 'string') {
          errorMessage = error.detail;
        } else if (error.error && typeof error.error === 'string') {
          errorMessage = error.error;
        } else if (typeof error === 'string') {
          errorMessage = error;
        }
      }

      if (errorMessage.includes('token') || errorMessage.includes('expired')) {
        setState('invalid_token');
      } else {
        setState('error');
      }
      setMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToLogin = () => {
    router.push('/Authentication/login');
  };

  const handleForgotPassword = () => {
    router.push('/forgot-password');
  };

  const renderContent = () => {
    switch (state) {
      case 'loading':
        return (
          <div className="text-center space-y-4">
            <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
            <h1 className="text-2xl font-semibold text-gray-900">Validating reset token...</h1>
            <p className="text-gray-600">Please wait while we verify your reset link.</p>
          </div>
        );

      case 'ready':
        return (
          <div className="space-y-6">
            <div className="text-center space-y-4">
              <div className="h-12 w-12 mx-auto bg-primary/10 rounded-full flex items-center justify-center">
                <Lock className="h-6 w-6 text-primary" />
              </div>
              <h1 className="text-2xl font-semibold text-gray-900">Reset Your Password</h1>
              <p className="text-gray-600">Enter your new password below.</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="newPassword">New Password</Label>
                <Input
                  id="newPassword"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  disabled={isLoading}
                  required
                />
                {errors.newPassword && (
                  <p className="text-sm text-red-600 mt-1">{errors.newPassword}</p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Must contain uppercase, lowercase, number and special character
                </p>
              </div>

              <div>
                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  disabled={isLoading}
                  required
                />
                {errors.confirmPassword && (
                  <p className="text-sm text-red-600 mt-1">{errors.confirmPassword}</p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Resetting Password...
                  </>
                ) : (
                  "Reset Password"
                )}
              </Button>
            </form>
          </div>
        );

      case 'success':
        return (
          <div className="text-center space-y-4">
            <CheckCircle className="h-12 w-12 mx-auto text-green-500" />
            <h1 className="text-2xl font-semibold text-gray-900">Password Reset Successfully!</h1>
            <p className="text-gray-600">{message}</p>
            <p className="text-sm text-gray-500">Redirecting to login page...</p>
            <Button onClick={handleBackToLogin} className="mt-4">
              Continue to Login
            </Button>
          </div>
        );

      case 'invalid_token':
        return (
          <div className="text-center space-y-4">
            <XCircle className="h-12 w-12 mx-auto text-orange-500" />
            <h1 className="text-2xl font-semibold text-gray-900">Invalid or Expired Link</h1>
            <p className="text-gray-600">{message}</p>
            <p className="text-sm text-gray-500">This password reset link may have expired or is invalid.</p>
            <div className="space-y-2">
              <Button onClick={handleForgotPassword} className="w-full">
                Request New Reset Link
              </Button>
              <Button onClick={handleBackToLogin} variant="outline" className="w-full">
                Back to Login
              </Button>
            </div>
          </div>
        );

      case 'error':
      default:
        return (
          <div className="text-center space-y-4">
            <XCircle className="h-12 w-12 mx-auto text-red-500" />
            <h1 className="text-2xl font-semibold text-gray-900">Reset Failed</h1>
            <p className="text-gray-600">{message}</p>
            <div className="space-y-2">
              <Button onClick={() => setState('ready')} className="w-full">
                Try Again
              </Button>
              <Button onClick={handleBackToLogin} variant="outline" className="w-full">
                Back to Login
              </Button>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-white rounded-lg shadow-md p-8">
          {renderContent()}
        </div>
      </div>
    </div>
  );
} 