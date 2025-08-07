"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { SimpleNavbar } from "@/components/navigation/simple-navbar";
import { SettingsSidebar } from "@/components/settings/settings-sidebar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { userApi, type UserResponse, type UserStats, type UserProfileUpdate, type PasswordChangeRequest } from "@/lib/api/user-api";

// Settings configuration matching the user profile dropdown
const settingsConfig = {
  title: "Settings",
  items: [
    {
      id: "profile",
      label: "Profile",
      iconName: "User",
      href: "/settings?section=profile"
    },
    {
      id: "security", 
      label: "Password & Security",
      iconName: "Shield",
      href: "/settings?section=security"
    },
    {
      id: "account",
      label: "Account Settings", 
      iconName: "Gear",
      href: "/settings?section=account"
    },
    {
      id: "stats",
      label: "Statistics",
      iconName: "ChartBar", 
      href: "/settings?section=stats"
    }
  ],
  upgradeButton: {
    text: "Upgrade to Pro",
    iconName: "ArrowUp"
  }
};

function SettingsContent() {
  const searchParams = useSearchParams();
  const [activeSection, setActiveSection] = useState(searchParams.get('section') || 'profile');
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form states
  const [profileData, setProfileData] = useState<UserProfileUpdate>({});
  const [passwordData, setPasswordData] = useState<PasswordChangeRequest>({
    current_password: '',
    new_password: ''
  });

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        setLoading(true);
        const [user, stats] = await Promise.all([
          userApi.getCurrentUser(),
          userApi.getUserStats().catch(() => null)
        ]);
        
        setCurrentUser(user);
        setUserStats(stats);
        setProfileData({
          name: user.name,
          email: user.email,
          intro: user.intro,
          interests: user.interests
        });
      } catch (error) {
        console.error('Failed to fetch user data:', error);
        setMessage({ type: 'error', text: 'Failed to load user data' });
      } finally {
        setLoading(false);
      }
    };

    fetchUserData();
  }, []);

  const handleSectionChange = (sectionId: string) => {
    setActiveSection(sectionId);
    setMessage(null);
    // Update URL without page reload
    const url = new URL(window.location.href);
    url.searchParams.set('section', sectionId);
    window.history.pushState({}, '', url.toString());
  };

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const result = await userApi.updateCurrentUser(profileData);
      if (result.success) {
        setCurrentUser(result.user);
        setMessage({ type: 'success', text: result.message || 'Profile updated successfully' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: error instanceof Error ? error.message : 'Failed to update profile' });
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const result = await userApi.changePassword(passwordData);
      if (result.success) {
        setPasswordData({ current_password: '', new_password: '' });
        setMessage({ type: 'success', text: result.message || 'Password changed successfully' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: error instanceof Error ? error.message : 'Failed to change password' });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      return;
    }

    setSaving(true);
    setMessage(null);

    try {
      const result = await userApi.deleteAccount();
      if (result.success) {
        // Clear tokens and redirect to login
        await userApi.completeLogout();
        window.location.href = '/login?message=Account deleted successfully';
      }
    } catch (error) {
      setMessage({ type: 'error', text: error instanceof Error ? error.message : 'Failed to delete account' });
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => {
    setSaving(true);
    setMessage(null);

    try {
      await userApi.completeLogout();
      window.location.href = '/login?message=Logged out successfully';
    } catch (error) {
      setMessage({ type: 'error', text: 'Logout failed, but you will be redirected anyway' });
      // Fallback: redirect anyway after a short delay
      setTimeout(() => {
        window.location.href = '/login?message=Logged out locally';
      }, 1500);
    } finally {
      setSaving(false);
    }
  };

  const renderProfileSection = () => (
    <Card>
      <CardHeader>
        <CardTitle>Profile Information</CardTitle>
        <CardDescription>
          Update your personal information and research interests
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleProfileUpdate} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name"
                value={profileData.name || ''}
                onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                placeholder="Enter your full name"
              />
            </div>
            <div>
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                value={profileData.email || ''}
                onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                placeholder="Enter your email"
              />
            </div>
          </div>
          
          <div>
            <Label htmlFor="intro">Introduction</Label>
            <Textarea
              id="intro"
              value={profileData.intro || ''}
              onChange={(e) => setProfileData({ ...profileData, intro: e.target.value })}
              placeholder="Tell us about yourself and your research"
              rows={3}
            />
          </div>

          <div>
            <Label htmlFor="interests">Research Interests</Label>
            <Input
              id="interests"
              value={profileData.interests?.join(', ') || ''}
              onChange={(e) => setProfileData({ 
                ...profileData, 
                interests: e.target.value.split(',').map(i => i.trim()).filter(i => i) 
              })}
              placeholder="machine learning, nlp, computer vision"
            />
            <p className="text-xs text-muted-foreground mt-1">Separate interests with commas</p>
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
            {currentUser?.email_verified ? (
              <Badge variant="secondary">
                Email Verified
              </Badge>
            ) : (
              <Badge variant="outline">
                Email Not Verified
              </Badge>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );

  const renderSecuritySection = () => (
    <Card>
      <CardHeader>
        <CardTitle>Password & Security</CardTitle>
        <CardDescription>
          Update your password and manage security settings
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handlePasswordChange} className="space-y-4">
          <div>
            <Label htmlFor="current_password">Current Password</Label>
            <Input
              id="current_password"
              type="password"
              value={passwordData.current_password}
              onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
              placeholder="Enter your current password"
            />
          </div>
          
          <div>
            <Label htmlFor="new_password">New Password</Label>
            <Input
              id="new_password"
              type="password"
              value={passwordData.new_password}
              onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
              placeholder="Enter your new password"
            />
          </div>

          <Button type="submit" disabled={saving}>
            {saving ? 'Changing Password...' : 'Change Password'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );

  const renderAccountSection = () => (
    <Card>
      <CardHeader>
        <CardTitle>Account Settings</CardTitle>
        <CardDescription>
          Manage your account settings and data
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h4 className="font-medium mb-2">Account Information</h4>
          <div className="text-sm text-muted-foreground space-y-1">
            <p>Account created: {currentUser ? new Date(currentUser.created_at).toLocaleDateString() : 'N/A'}</p>
            <p>Last login: {currentUser?.last_login ? new Date(currentUser.last_login).toLocaleDateString() : 'Never'}</p>
          </div>
        </div>

        <div className="border-t pt-6 space-y-6">
          <div>
            <h4 className="font-medium mb-2">Session Management</h4>
            <p className="text-sm text-muted-foreground mb-4">
              Sign out of your account on this device.
            </p>
            <Button 
              variant="outline" 
              onClick={handleLogout}
              disabled={saving}
            >
              {saving ? 'Signing Out...' : 'Sign Out'}
            </Button>
          </div>

          <div>
            <h4 className="font-medium text-destructive mb-2">Danger Zone</h4>
            <p className="text-sm text-muted-foreground mb-4">
              Once you delete your account, there is no going back. Please be certain.
            </p>
            <Button 
              variant="destructive" 
              onClick={handleDeleteAccount}
              disabled={saving}
            >
              {saving ? 'Deleting Account...' : 'Delete Account'}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  const renderStatsSection = () => (
    <Card>
      <CardHeader>
        <CardTitle>Your Statistics</CardTitle>
        <CardDescription>
          Overview of your activity and contributions
        </CardDescription>
      </CardHeader>
      <CardContent>
        {userStats ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">{userStats.projects_count}</div>
              <div className="text-sm text-muted-foreground">Projects</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">{userStats.papers_count}</div>
              <div className="text-sm text-muted-foreground">Papers</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">{userStats.interests_count}</div>
              <div className="text-sm text-muted-foreground">Research Interests</div>
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground">Statistics not available</p>
        )}
      </CardContent>
    </Card>
  );

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      );
    }

    switch (activeSection) {
      case 'profile':
        return renderProfileSection();
      case 'security':
        return renderSecuritySection();
      case 'account':
        return renderAccountSection();
      case 'stats':
        return renderStatsSection();
      default:
        return renderProfileSection();
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <SimpleNavbar 
        onSettingClick={(settingId) => handleSectionChange(settingId)}
        onProjectClick={(projectId) => window.location.href = `/projects/${projectId}`}
      />
      
      <div className="flex">
        <SettingsSidebar
          activeSection={activeSection}
          onSectionChange={handleSectionChange}
          config={settingsConfig}
        />
        
        <main className="flex-1 p-8">
          <div className="max-w-4xl mx-auto space-y-6">
            {message && (
              <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
                <AlertDescription>{message.text}</AlertDescription>
              </Alert>
            )}
            
            {renderContent()}
          </div>
        </main>
      </div>
    </div>
  );
}

function SettingsLoadingFallback() {
  return (
    <div className="min-h-screen bg-background">
      <SimpleNavbar 
        onSettingClick={() => {}}
        onProjectClick={() => {}}
      />
      
      <div className="flex">
        <SettingsSidebar
          activeSection="profile"
          onSectionChange={() => {}}
          config={settingsConfig}
        />
        
        <main className="flex-1 p-8">
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center justify-center h-64">
              <div className="text-muted-foreground">Loading...</div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<SettingsLoadingFallback />}>
      <SettingsContent />
    </Suspense>
  );
} 