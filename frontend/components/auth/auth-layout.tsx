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
    <div className={`min-h-screen flex items-center justify-center bg-background px-4 sm:px-6 lg:px-8 ${className}`}>
      <div className="w-full max-w-md space-y-8">
        {/* Header */}
        {/* <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            {title}
          </h1>
        </div> */}

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
  );
} 