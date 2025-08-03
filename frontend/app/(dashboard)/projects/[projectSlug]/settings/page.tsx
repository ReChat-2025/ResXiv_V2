"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { projectsApi } from "@/lib/api/projects-api";
import { userApi, UserResponse } from "@/lib/api/user-api";
import { settingsApi, ProjectResponse, MemberResponse, TeamInvitation } from "@/lib/api/settings-api";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Settings, 
  Users, 
  HelpCircle, 
  Copy, 
  ArrowUpCircle, 
  Link, 
  UserPlus,
  Shield,
  Trash2,
  MoreVertical,
  Mail,
  Crown,
  User,
  Eye,
  EyeOff
} from "lucide-react";

// Types
interface Project {
  id: string;
  name: string;
  avatar?: string;
  avatarFallback: string;
  slug?: string;
}

interface TeamMember extends MemberResponse {
  permissions?: string[];
  last_active?: string;
  avatar_url?: string;
}

interface PendingInvite {
  id: string;
  email: string;
  role: string;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  invited_at: string;
  expires_at: string;
  invited_by?: {
    id: string;
    name: string;
    email: string;
  };
}

interface AccessControl {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  roles: string[];
}

const PROJECT_ROLES = [
  { value: 'admin', label: 'Admin', description: 'Full access to project settings and management' },
  { value: 'write', label: 'Editor', description: 'Can edit content and invite members' },
  { value: 'read', label: 'Viewer', description: 'Can only view content' }
];

const ACCESS_CONTROLS: AccessControl[] = [
  {
    id: 'require_approval',
    name: 'Require approval for new papers',
    description: 'All new papers must be approved by an admin before being visible',
    enabled: true,
    roles: ['admin']
  },
  {
    id: 'restrict_downloads',
    name: 'Restrict PDF downloads',
    description: 'Only members with write access can download PDFs',
    enabled: false,
    roles: ['admin', 'write']
  },
  {
    id: 'private_comments',
    name: 'Private comments',
    description: 'Comments are only visible to project members',
    enabled: true,
    roles: ['admin', 'write', 'read']
  },
  {
    id: 'external_sharing',
    name: 'External sharing',
    description: 'Allow sharing papers with non-members via links',
    enabled: false,
    roles: ['admin']
  }
];

function ProjectSettingsPage() {
  const router = useRouter();
  const params = useParams();
  const projectSlug = params.projectSlug as string;
  
  // Core state
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [projectSettings, setProjectSettings] = useState<ProjectResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeSection, setActiveSection] = useState("general");
  
  // General settings state
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [repoUrl, setRepoUrl] = useState('');
  
  // People management state
  const [activePeopleTab, setActivePeopleTab] = useState("members");
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [pendingInvites, setPendingInvites] = useState<PendingInvite[]>([]);
  const [inviteEmails, setInviteEmails] = useState('');
  const [inviteRole, setInviteRole] = useState('read');
  const [inviteMessage, setInviteMessage] = useState('');
  const [isInviting, setIsInviting] = useState(false);
  
  // Access controls state
  const [accessControls, setAccessControls] = useState<AccessControl[]>(ACCESS_CONTROLS);
  
  // Performance optimizations
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredMembers, setFilteredMembers] = useState<TeamMember[]>([]);

  // Data fetching
  useEffect(() => {
    const fetchData = async () => {
      if (!projectSlug) return;

      try {
        setIsLoading(true);
        const [projectsResponse, userResponse] = await Promise.all([
          projectsApi.getProjects(),
          userApi.getCurrentUser()
        ]);
        
        const project = projectsResponse.projects.find((p: any) => 
          p.slug === projectSlug || p.id === projectSlug
        );
        
        if (!project) {
          router.push('/projects');
          return;
        }

        setCurrentProject({
          id: project.id,
          name: project.name,
          slug: project.slug || undefined,
          avatarFallback: project.name.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase(),
        });
        setCurrentUser(userResponse);

        // Fetch detailed project data
        try {
          const [detailedProject, members] = await Promise.all([
            settingsApi.getProjectSettings(project.id),
            settingsApi.getTeamMembers(project.id)
          ]);

          setProjectSettings(detailedProject);
          setTeamMembers(members);
          setProjectName(detailedProject.name || project.name);
          setProjectDescription(detailedProject.description || '');
          setIsPrivate(detailedProject.is_private || false);
          setRepoUrl(detailedProject.repo_url || '');

          // Fetch invitations
          try {
            const invitations = await settingsApi.getProjectInvitations(project.id);
            setPendingInvites(invitations.invitations || invitations || []);
          } catch (inviteError) {
            console.warn('Invitations not available:', inviteError);
          }
        } catch (apiError) {
          console.error('Failed to fetch project details:', apiError);
          setProjectName(project.name);
        }
      } catch (error) {
        console.error('Failed to fetch data:', error);
        router.push('/projects');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [projectSlug, router]);

  // Filter members based on search
  useEffect(() => {
    if (!searchTerm) {
      setFilteredMembers(teamMembers);
    } else {
      setFilteredMembers(
        teamMembers.filter(member =>
          member.user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          member.user.email.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }
  }, [teamMembers, searchTerm]);

  // Event handlers
  const handleSaveProjectSettings = async () => {
    if (!currentProject) return;

    try {
      const updatedProject = await settingsApi.updateProjectSettings(currentProject.id, {
        name: projectName,
        description: projectDescription,
        is_private: isPrivate,
        repo_url: repoUrl
      });
      
      setProjectSettings(updatedProject);
      setCurrentProject(prev => prev ? { ...prev, name: projectName } : null);
      // Success feedback would go here (toast notification)
    } catch (error) {
      console.error('Failed to update project settings:', error);
      // Error feedback would go here
    }
  };

  const handleInviteUsers = async () => {
    if (!currentProject || !inviteEmails.trim()) return;

    setIsInviting(true);
    try {
      const emails = inviteEmails.split(',').map(email => email.trim()).filter(Boolean);
      
      for (const email of emails) {
        const invitation: TeamInvitation = {
          email,
          role: inviteRole as 'admin' | 'write' | 'read',
          message: inviteMessage || 'You have been invited to join this ResXiv project.',
          expires_in_days: 7
        };

        await settingsApi.createInvitation(currentProject.id, invitation);
      }
      
      // Refresh invitations
      try {
        const invitations = await settingsApi.getProjectInvitations(currentProject.id);
        setPendingInvites(invitations.invitations || invitations || []);
      } catch (refreshError) {
        console.warn('Failed to refresh invitations:', refreshError);
      }
      
      setInviteEmails('');
      setInviteMessage('');
      // Success feedback
    } catch (error) {
      console.error('Failed to send invitations:', error);
      // Error feedback
    } finally {
      setIsInviting(false);
    }
  };

  const handleWithdrawInvite = async (inviteId: string) => {
    if (!currentProject) return;

    try {
      await settingsApi.withdrawInvitation(currentProject.id, inviteId);
      setPendingInvites(prev => prev.filter(invite => invite.id !== inviteId));
    } catch (error) {
      console.error('Failed to withdraw invitation:', error);
    }
  };

  const handleRemoveMember = async (memberUserId: string) => {
    if (!currentProject) return;

    try {
      await settingsApi.removeTeamMember(currentProject.id, memberUserId);
      setTeamMembers(prev => prev.filter(member => member.user_id !== memberUserId));
    } catch (error) {
      console.error('Failed to remove member:', error);
    }
  };

  const handleUpdateMemberRole = async (memberUserId: string, newRole: string) => {
    if (!currentProject) return;

    try {
      await settingsApi.updateMemberRole(currentProject.id, memberUserId, newRole);
      setTeamMembers(prev => prev.map(member => 
        member.user_id === memberUserId ? { ...member, role: newRole } : member
      ));
    } catch (error) {
      console.error('Failed to update member role:', error);
    }
  };

  const copyProjectLink = async () => {
    const projectLink = `${window.location.origin}/projects/${projectSlug}`;
    try {
      await navigator.clipboard.writeText(projectLink);
      // Success feedback
    } catch (error) {
      console.error('Failed to copy link:', error);
    }
  };

  const toggleAccessControl = (controlId: string) => {
    setAccessControls(prev => prev.map(control =>
      control.id === controlId ? { ...control, enabled: !control.enabled } : control
    ));
  };

  // Render functions
  const renderGeneralSection = () => (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-papers-primary mb-6 font-sans">
          General Settings
        </h2>
        
        {/* Project Information Card */}
        <Card className="border-papers-medium bg-papers-sidebar mb-6">
          <CardHeader className="bg-papers-sidebar border-b border-papers-medium">
            <CardTitle className="flex items-center gap-3 text-papers-primary font-sans">
              <Settings size={20} className="text-papers-muted" />
              Project Information
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="project-name" className="text-papers-primary font-medium">
                  Project Name
                </Label>
                <Input
                  id="project-name"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="border-papers-dark bg-papers-sidebar text-papers-secondary"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="repo-url" className="text-papers-primary font-medium">
                  Repository URL
                </Label>
                <Input
                  id="repo-url"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/..."
                  className="border-papers-dark bg-papers-sidebar text-papers-secondary"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="project-description" className="text-papers-primary font-medium">
                Description
              </Label>
              <Textarea
                id="project-description"
                value={projectDescription}
                onChange={(e) => setProjectDescription(e.target.value)}
                rows={3}
                className="border-papers-dark bg-papers-sidebar text-papers-secondary"
              />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-papers-primary font-medium">
                  Private Project
                </Label>
                <p className="text-sm text-papers-muted">
                  Only invited members can access this project
                </p>
              </div>
              <Switch
                checked={isPrivate}
                onCheckedChange={setIsPrivate}
              />
            </div>
            
            <Button 
              onClick={handleSaveProjectSettings}
              className="bg-papers-button-primary text-papers-button-primary hover:bg-papers-button-primary/90"
            >
              Save Changes
            </Button>
          </CardContent>
        </Card>

        {/* Project Stats */}
        {projectSettings && (
          <Card className="border-papers-medium bg-papers-sidebar">
            <CardHeader className="bg-papers-sidebar border-b border-papers-medium">
              <CardTitle className="text-papers-primary font-sans">
                Project Statistics
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-papers-primary font-sans">
                    {projectSettings.member_count}
                  </div>
                  <div className="text-sm text-papers-muted font-sans">Members</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-papers-primary font-sans">
                    {projectSettings.paper_count}
                  </div>
                  <div className="text-sm text-papers-muted font-sans">Papers</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-papers-primary font-sans">
                    {projectSettings.is_private ? 'Private' : 'Public'}
                  </div>
                  <div className="text-sm text-papers-muted font-sans">Visibility</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-papers-primary font-sans">
                    {new Date(projectSettings.created_at).toLocaleDateString()}
                  </div>
                  <div className="text-sm text-papers-muted font-sans">Created</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );

  const renderPeopleSection = () => (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-papers-primary mb-6 font-sans">
          People
        </h2>
        
        {/* Tab Navigation */}
        <div className="flex space-x-1 bg-papers-selected p-1 rounded-xl w-fit mb-6">
          <Button
            variant={activePeopleTab === "members" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActivePeopleTab("members")}
            className={activePeopleTab === "members" 
              ? "bg-white text-papers-muted shadow-sm" 
              : "text-papers-muted hover:bg-white/50"
            }
          >
            Members
          </Button>
          <Button
            variant={activePeopleTab === "invites" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActivePeopleTab("invites")}
            className={activePeopleTab === "invites" 
              ? "bg-white text-papers-muted shadow-sm" 
              : "text-papers-muted hover:bg-white/50"
            }
          >
            Invites
          </Button>
        </div>

        {activePeopleTab === "members" && (
          <div className="space-y-6">
            {/* Search */}
            <div className="flex items-center gap-4">
              <Input
                placeholder="Search members..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="max-w-sm border-papers-dark bg-papers-sidebar"
              />
              <Badge variant="secondary" className="bg-papers-selected text-papers-secondary">
                {filteredMembers.length} member{filteredMembers.length !== 1 ? 's' : ''}
              </Badge>
            </div>

            {/* Members List */}
            <div className="space-y-2">
              {filteredMembers.map((member) => (
                <div key={member.id} className="flex items-center justify-between p-4 border-t border-papers-medium/50 first:border-t-0">
                  <div className="flex items-center gap-4">
                    <Avatar className="h-12 w-12">
                      <AvatarImage src={member.avatar_url} />
                      <AvatarFallback className="bg-papers-selected text-papers-primary">
                        {member.user.name.split(' ').map((n: string) => n[0]).join('').toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-papers-secondary">
                          {member.user.name}
                        </p>
                        {member.is_owner && (
                          <Crown size={16} className="text-yellow-500" />
                        )}
                      </div>
                      <p className="text-sm text-papers-muted">
                        {member.user.email}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Select
                      value={member.role}
                      onValueChange={(value) => handleUpdateMemberRole(member.user_id, value)}
                      disabled={member.is_owner}
                    >
                      <SelectTrigger className="w-32 border-papers-dark">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PROJECT_ROLES.map((role) => (
                          <SelectItem key={role.value} value={role.value}>
                            {role.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    {!member.is_owner && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveMember(member.user_id)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 size={16} />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activePeopleTab === "invites" && (
          <div className="space-y-6">
            {/* Email Invite Section */}
            <Card className="border-papers-medium bg-papers-sidebar">
              <CardHeader className="bg-papers-sidebar border-b border-papers-medium">
                <CardTitle className="text-papers-primary text-base font-bold font-sans">
                  Email Invite
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div className="flex gap-3">
                  <Input
                    placeholder="Enter Email comma separated"
                    value={inviteEmails}
                    onChange={(e) => setInviteEmails(e.target.value)}
                    className="flex-1 border-papers-dark bg-papers-sidebar text-papers-light"
                  />
                  <Button 
                    onClick={handleInviteUsers}
                    disabled={isInviting || !inviteEmails.trim()}
                    className="bg-papers-button-primary text-papers-button-primary hover:bg-papers-button-primary/90 px-5 h-[52px]"
                  >
                    {isInviting ? 'Inviting...' : 'Invite'}
                  </Button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-papers-primary">Role</Label>
                    <Select value={inviteRole} onValueChange={setInviteRole}>
                      <SelectTrigger className="border-papers-dark bg-papers-sidebar">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PROJECT_ROLES.map((role) => (
                          <SelectItem key={role.value} value={role.value}>
                            <div>
                              <div className="font-medium">{role.label}</div>
                              <div className="text-xs text-papers-muted">{role.description}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label className="text-papers-primary">
                      Message (Optional)
                    </Label>
                    <Input
                      placeholder="Personal invitation message"
                      value={inviteMessage}
                      onChange={(e) => setInviteMessage(e.target.value)}
                      className="border-papers-dark bg-papers-sidebar"
                    />
                  </div>
                </div>
                
                <div className="pt-4 border-t border-papers-medium">
                  <Button 
                    variant="outline" 
                    onClick={copyProjectLink}
                    className="flex items-center gap-2 border-papers-dark text-papers-primary hover:bg-papers-selected"
                  >
                    <Link size={16} />
                    Copy project link
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Pending Invites */}
            {pendingInvites.length > 0 && (
              <div className="space-y-4">
                <div className="h-px bg-papers-medium" />
                <h3 className="text-base font-bold text-papers-muted">
                  Pending Invites
                </h3>
                <div className="space-y-2">
                  {pendingInvites.map((invite) => (
                    <div key={invite.id} className="flex items-center justify-between p-3 border-t border-papers-medium/50 first:border-t-0">
                      <div className="flex items-center gap-3">
                        <Avatar className="h-12 w-12">
                          <AvatarFallback className="bg-papers-selected text-papers-primary">
                            {invite.email.charAt(0).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium text-papers-secondary">
                            {invite.email}
                          </p>
                          <div className="flex items-center gap-2 text-sm text-papers-muted">
                            <span>Role: {invite.role}</span>
                            <span>•</span>
                            <span>Expires: {new Date(invite.expires_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="bg-papers-selected text-papers-secondary">
                          {invite.status}
                        </Badge>
                        <Button 
                          variant="outline"
                          size="sm"
                          onClick={() => handleWithdrawInvite(invite.id)}
                          className="bg-papers-button-primary text-papers-button-primary hover:bg-papers-button-primary/90 border-papers-button-primary"
                        >
                          Withdraw
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );

  const renderAccessControlsSection = () => (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-papers-primary mb-6 font-sans">
          Access Controls
        </h2>
        
        <Card className="border-papers-medium bg-papers-sidebar">
          <CardHeader className="bg-papers-sidebar border-b border-papers-medium">
            <CardTitle className="flex items-center gap-3 text-papers-primary font-sans">
              <Shield size={20} className="text-papers-muted" />
              Project Permissions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {accessControls.map((control) => (
              <div key={control.id} className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-papers-primary font-sans">
                      {control.name}
                    </h4>
                    <Badge variant="outline" className="text-xs font-sans">
                      {control.roles.join(', ')}
                    </Badge>
                  </div>
                  <p className="text-sm text-papers-muted font-sans">
                    {control.description}
                  </p>
                </div>
                <Switch
                  checked={control.enabled}
                  onCheckedChange={() => toggleAccessControl(control.id)}
                />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const renderHelpSection = () => (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-papers-primary mb-6 font-sans">
          Help & Support
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Help Resources */}
          <Card className="border-papers-medium bg-papers-sidebar">
            <CardHeader className="bg-papers-sidebar border-b border-papers-medium">
              <CardTitle className="text-papers-primary font-sans">
                Help Resources
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-3">
              {[
                { name: 'Guide', url: 'https://docs.resxiv.com/guide' },
                { name: 'Changelog', url: 'https://docs.resxiv.com/changelog' },
                { name: 'Blogs', url: 'https://blog.resxiv.com' }
              ].map((resource) => (
                <Button
                  key={resource.name}
                  variant="outline"
                  className="w-full justify-between border-papers-dark text-papers-primary hover:bg-papers-selected"
                  onClick={() => window.open(resource.url, '_blank')}
                >
                  {resource.name}
                  <ArrowUpCircle size={16} className="rotate-45" />
                </Button>
              ))}
            </CardContent>
          </Card>

          {/* Support */}
          <Card className="border-papers-medium bg-papers-sidebar">
            <CardHeader className="bg-papers-sidebar border-b border-papers-medium">
              <CardTitle className="text-papers-primary font-sans">
                Support
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div>
                <p className="text-sm font-medium text-papers-primary">
                  Email Support
                </p>
                <p className="text-sm text-papers-muted">
                  contact@resxiv.com
                </p>
                <p className="text-xs text-papers-light mt-1">
                  Response within 24 hours
                </p>
              </div>
              <Button 
                className="w-full bg-papers-button-primary text-papers-button-primary hover:bg-papers-button-primary/90"
              >
                Contact Support
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-papers-primary">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-papers-button-primary mx-auto mb-4"></div>
          <p className="text-papers-muted">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden bg-papers-primary">
      {/* Sidebar - Exact Figma Design */}
      <div className="w-[298px] bg-papers-sidebar border-r border-papers-medium flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-papers-medium">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-normal text-papers-primary">
              Settings
            </h2>
            <div className="w-6 h-6 flex items-center justify-center">
              <Settings size={20} className="text-papers-muted" />
            </div>
          </div>
        </div>

        <div className="h-px bg-papers-medium" />

        {/* Navigation Items */}
        <div className="flex-1 p-6 space-y-0.5">
          {[
            { id: "general", label: "General", icon: Settings },
            { id: "people", label: "People", icon: Users },
            { id: "access", label: "Access Controls", icon: Shield },
            { id: "help", label: "Help", icon: HelpCircle }
          ].map((item) => {
            const isActive = activeSection === item.id;
            const Icon = item.icon;
            
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`
                  w-full flex items-center gap-2 px-5 py-3 rounded-xl text-left transition-colors
                  ${isActive 
                    ? "bg-papers-selected text-papers-primary" 
                    : "text-papers-primary hover:bg-papers-selected/50"
                  }
                `}
              >
                <Icon size={16} className={isActive ? "text-papers-muted" : "text-papers-muted"} />
                <span className="font-normal">{item.label}</span>
              </button>
            );
          })}
        </div>

        <div className="h-px bg-papers-medium" />

        {/* Upgrade Button */}
        <div className="p-6">
          <button 
            onClick={() => window.open('/pricing', '_blank')}
            className="w-full bg-papers-button-primary text-papers-button-primary rounded-xl px-3 py-3 flex items-center justify-center gap-2 hover:bg-papers-button-primary/90 transition-colors"
          >
            <ArrowUpCircle size={16} />
            Upgrade to ResXiv Pro
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="p-8 max-w-4xl mx-auto">
          {activeSection === "general" && renderGeneralSection()}
          {activeSection === "people" && renderPeopleSection()}
          {activeSection === "access" && renderAccessControlsSection()}
          {activeSection === "help" && renderHelpSection()}
        </div>
      </div>
    </div>
  );
}

export default function ProtectedProjectSettingsPage() {
  return (
    <ProtectedRoute>
      <ProjectSettingsPage />
    </ProtectedRoute>
  );
} 