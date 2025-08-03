"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useIsAuthenticated, useIsInitializing } from "@/lib/stores/app-store";

export default function RootPage() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();
  const isInitializing = useIsInitializing();

  useEffect(() => {
    if (!isInitializing) {
      if (isAuthenticated) {
        // User is logged in → redirect to projects
        router.push('/projects');
      } else {
        // User is not logged in → redirect to login
        router.push('/login');
      }
    }
  }, [isAuthenticated, isInitializing, router]);

  // Show loading during initialization
  if (isInitializing) {
    return (
      <div className="bg-background min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Show loading while redirecting
  return (
    <div className="bg-background min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        <p className="text-muted-foreground">Redirecting...</p>
      </div>
    </div>
  );
}
