"use client";

import { useEffect, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useIsAuthenticated, useIsInitializing } from '@/lib/stores/app-store';

interface ProtectedRouteProps {
  children: ReactNode;
  redirectTo?: string;
}

export function ProtectedRoute({ 
  children, 
  redirectTo = '/login' 
}: ProtectedRouteProps) {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();
  const isInitializing = useIsInitializing();

  useEffect(() => {
    if (!isInitializing && !isAuthenticated) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, isInitializing, router, redirectTo]);

  // Show loading during initialization
  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Don't render children if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
} 