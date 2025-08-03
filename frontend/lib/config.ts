// Configuration for application content and routes
// This makes the app easily configurable for different deployments

export interface AppConfig {
  metadata: {
    title: string;
    description: string;
  };
  homepage: {
    title: string;
    subtitle: string;
    features: FeatureConfig[];
  };
}

export interface FeatureConfig {
  id: string;
  title: string;
  description: string;
  icon: string; // Lucide icon name
  href: string;
  variant: "default" | "outline";
  primary?: boolean;
}

// Main application configuration
export const appConfig: AppConfig = {
  metadata: {
    title: process.env.NEXT_PUBLIC_APP_NAME || "ResXiv",
    description: process.env.NEXT_PUBLIC_APP_DESCRIPTION || "Your research hub"
  },
  homepage: {
    title: "Welcome",
    subtitle: "Access your account or explore your projects",
    features: [
      {
        id: "signin",
        title: "Sign In",
        description: "Access your existing account",
        icon: "LogIn",
        href: "/Authentication/login",
        variant: "default",
        primary: true
      },
      {
        id: "signup", 
        title: "Sign Up",
        description: "Create a new account",
        icon: "UserPlus",
        href: "/Authentication/signup",
        variant: "outline"
      },
      {
        id: "projects",
        title: "Projects", 
        description: "Manage and organize your work",
        icon: "FolderOpen",
        href: "/Project/projects",
        variant: "outline"
      }
    ]
  }
};

// Route configuration
export const routes = {
  auth: {
    login: "/Authentication/login",
    signup: "/Authentication/signup"
  },
  projects: {
    main: "/Project/projects",
    ai: "/Project/projects/resxiv-ai"
  },
  home: "/"
} as const; 