import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',
  
  // API configuration
  async rewrites() {
    // Sanitize API URL to prevent double /api
    let apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    apiUrl = apiUrl.replace(/\/$/, '').replace(/\/api$/, '');
    return [
      // Auth route aliases for backward compatibility with email links
      {
        source: '/auth/verify-email',
        destination: '/verify-email',
      },
      {
        source: '/auth/reset-password',
        destination: '/reset-password',
      },
      {
        source: '/auth/login',
        destination: '/login',
      },
      {
        source: '/auth/signup',
        destination: '/signup',
      },
      // API proxy configuration
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },

  // Environment variables validation
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
  },

  // Image optimization
  images: {
    domains: ['localhost', 'cbeta.resxiv.com', '35.154.171.72'],
  },

  // Webpack configuration for Monaco Editor
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
        crypto: false,
      };
    }
    return config;
  },

  // TypeScript configuration
  typescript: {
    ignoreBuildErrors: false,
  },

  // ESLint configuration
  eslint: {
    ignoreDuringBuilds: false,
  },

  // Experimental features (removed deprecated appDir)
  experimental: {
    // Add any experimental features here when needed
  },
};

export default nextConfig;
