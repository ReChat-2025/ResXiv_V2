import React from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AuthLink } from "@/lib/auth-config";

interface AuthLayoutProps {
  title?: string;
  cardTitle: string;
  children: React.ReactNode;
  links: AuthLink[];
  className?: string;
}

export function AuthLayout({ 
  //  title,
  cardTitle, 
  children, 
  links, 
  className = "" 
}: AuthLayoutProps) {
  return (
    <div className={`min-h-screen bg-background ${className}`}>
      {/* Logo Header */}
      <div className="flex justify-start p-6">
        <Link href="/projects" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center">
            <span className="text-primary-foreground text-sm font-bold">R</span>
          </div>
          <span className="font-bold text-lg">ResXiv</span>
        </Link>
      </div>

      {/* Centered Auth Content */}
      <div className="flex items-center justify-center px-4 sm:px-6 lg:px-8" style={{ minHeight: 'calc(100vh - 120px)' }}>
        <div className="w-full max-w-md space-y-8">

        {/* Main Card */}
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">{cardTitle}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {children}
          </CardContent>
        </Card>

        {/* Footer Links */}
        {links.length > 0 && (
          <div className="text-center space-y-2">
            {links.map((link, index) => (
              <p key={index} className="text-sm text-muted-foreground">
                {link.text}{" "}
                <Link 
                  href={link.href}
                  className="font-medium text-primary hover:underline"
                >
                  {link.linkText}
                </Link>
              </p>
            ))}
          </div>
        )}
        </div>
      </div>
    </div>
  );
} 