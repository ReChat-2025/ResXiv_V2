"use client";

import React, { useState } from "react";
import { SimpleNavbar } from "@/components/navigation/simple-navbar";
import { Navbar } from "@/components/navigation/navbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Mock data for demonstration
const mockNotifications = [
  {
    id: "1",
    title: "New Paper Added",
    message: "John Doe added a new paper to Machine Learning Project",
    timestamp: "2 minutes ago",
    read: false,
    type: "info" as const
  },
  {
    id: "2", 
    title: "Collaboration Request",
    message: "Sarah Wilson wants to collaborate on your research",
    timestamp: "1 hour ago",
    read: false,
    type: "success" as const
  },
  {
    id: "3",
    title: "Project Update", 
    message: "Your project 'AI Research' has been updated",
    timestamp: "3 hours ago",
    read: true,
    type: "info" as const
  }
];

const mockProjects = [
  {
    id: "1",
    name: "Machine Learning Research",
    slug: "ml-research",
    avatarFallback: "ML"
  },
  {
    id: "2",
    name: "AI Ethics Study", 
    slug: "ai-ethics",
    avatarFallback: "AE"
  }
];

export default function NavbarDemoPage() {
  const [selectedNavbar, setSelectedNavbar] = useState<"simple" | "full">("simple");
  const [logs, setLogs] = useState<string[]>([]);

  const addLog = (message: string) => {
    setLogs(prev => [`${new Date().toLocaleTimeString()}: ${message}`, ...prev.slice(0, 9)]);
  };

  const handleNotificationClick = (notification: any) => {
    addLog(`Notification clicked: ${notification.title}`);
  };

  const handleSettingClick = (settingId: string) => {
    addLog(`Settings section clicked: ${settingId}`);
  };

  const handleProjectClick = (projectId: string) => {
    addLog(`Project clicked: ${projectId}`);
  };

  const handleProjectChange = (projectId: string) => {
    addLog(`Project changed to: ${projectId}`);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Demo Navbar */}
      {selectedNavbar === "simple" ? (
        <SimpleNavbar 
          notifications={mockNotifications}
          onNotificationClick={handleNotificationClick}
          onSettingClick={handleSettingClick}
          onProjectClick={handleProjectClick}
        />
      ) : (
        <Navbar
          currentProject={mockProjects[0]}
          projects={mockProjects}
          showProjectSelector={true}
          notifications={mockNotifications}
          onNotificationClick={(notificationId) => {
            const notification = mockNotifications.find(n => n.id === notificationId);
            if (notification) handleNotificationClick(notification);
          }}
          onProjectChange={handleProjectChange}
          onSettingClick={handleSettingClick}
          onUserProjectClick={handleProjectClick}
        />
      )}

      {/* Demo Content */}
      <div className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-4">Navbar User Profile Demo</h1>
          <p className="text-muted-foreground mb-6">
            This page demonstrates the new user profile dropdown functionality in both navbar variants.
            Click on the profile icon in the navbar to see the user settings and projects list.
          </p>
          
          {/* Navbar Selector */}
          <div className="flex gap-4 mb-6">
            <Button 
              variant={selectedNavbar === "simple" ? "default" : "outline"}
              onClick={() => setSelectedNavbar("simple")}
            >
              Simple Navbar
            </Button>
            <Button 
              variant={selectedNavbar === "full" ? "default" : "outline"}
              onClick={() => setSelectedNavbar("full")}
            >
              Full Navbar
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Features Card */}
          <Card>
            <CardHeader>
              <CardTitle>User Profile Dropdown Features</CardTitle>
              <CardDescription>
                The new dropdown includes all user settings from the auth API and a scrollable projects list
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">User Settings</h4>
                <div className="space-y-1 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">Profile</Badge>
                    Update profile information
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">Security</Badge>
                    Change password and security settings
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">Preferences</Badge>
                    App preferences and settings
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">Statistics</Badge>
                    View your activity statistics
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">Sign Out</Badge>
                    Sign out of your account
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium mb-2">Projects Section</h4>
                <div className="text-sm text-muted-foreground space-y-1">
                  <p>• Scrollable list of user's projects</p>
                  <p>• Project avatars with fallback initials</p>
                  <p>• Privacy status (Private/Public)</p>
                  <p>• Member count and user role</p>
                  <p>• Quick access to create new project</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Action Log */}
          <Card>
            <CardHeader>
              <CardTitle>Action Log</CardTitle>
              <CardDescription>
                Interactions with the navbar will be logged here
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-muted/50 rounded-lg p-4 h-64 overflow-y-auto">
                {logs.length === 0 ? (
                  <p className="text-muted-foreground text-sm">
                    No actions yet. Try clicking on notifications or the profile dropdown!
                  </p>
                ) : (
                  <div className="space-y-2">
                    {logs.map((log, index) => (
                      <div key={index} className="text-sm font-mono">
                        {log}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

                  {/* Technical Details */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Backend Integration</CardTitle>
            <CardDescription>
              Real API endpoints - no dummy data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-sm space-y-4">
              <div>
                <h4 className="font-medium mb-2">Auth Endpoints Used</h4>
                <div className="space-y-1 text-muted-foreground font-mono text-xs">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">GET</Badge>
                    <code>/api/v1/auth/me</code> - User profile
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">GET</Badge>
                    <code>/api/v1/auth/me/stats</code> - User statistics  
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">PUT</Badge>
                    <code>/api/v1/auth/me</code> - Update profile
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">POST</Badge>
                    <code>/api/v1/auth/me/change-password</code> - Change password
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">DELETE</Badge>
                    <code>/api/v1/auth/me</code> - Delete account
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">POST</Badge>
                    <code>/api/v1/auth/logout</code> - Logout user
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium mb-2">Project Endpoints</h4>
                <div className="space-y-1 text-muted-foreground font-mono text-xs">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">GET</Badge>
                    <code>/api/v1/projects/</code> - User projects (paginated)
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium mb-2">Features</h4>
                <ul className="list-disc list-inside ml-4 space-y-1 text-muted-foreground">
                  <li>Real-time user profile and statistics display</li>
                  <li>Email verification status from backend</li>
                  <li>Live project count and paper count from database</li>
                  <li>Scrollable projects list with actual project data</li>
                  <li>Loading states and error handling</li>
                  <li>Consistent styling with settings sidebar</li>
                  <li>Customizable click handlers for all actions</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 