"use client";

import { useEffect, type ReactNode } from 'react';
import { authService } from '@/lib/services/auth-service';
import { useSetInitializing } from '@/lib/stores/app-store';

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const setInitializing = useSetInitializing();

  useEffect(() => {
    const initAuth = () => {
      try {
        authService.initializeAuth();
      } catch (error) {
        console.error('Auth initialization failed:', error);
      } finally {
        setInitializing(false);
      }
    };

    initAuth();
  }, [setInitializing]);

  return <>{children}</>;
} 