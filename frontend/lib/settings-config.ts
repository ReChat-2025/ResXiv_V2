// Settings page configuration for scalable, production-ready settings management
// All content can be easily customized for different deployments

export interface SettingsSection {
  id: string;
  title: string;
  description?: string;
}

export interface SettingsSidebarItem {
  id: string;
  label: string;
  iconName: string;
  href?: string;
}

export interface SettingsSidebarConfig {
  title: string;
  items: SettingsSidebarItem[];
  upgradeButton: {
    text: string;
    iconName: string;
  };
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: string;
  status: 'active' | 'pending' | 'inactive';
  joinedAt: Date;
}

export interface Invite {
  id: string;
  email: string;
  role: string;
  status: 'pending' | 'accepted' | 'expired';
  invitedAt: Date;
  expiresAt: Date;
}

export interface PeopleSettingsConfig {
  members: TeamMember[];
  invites: Invite[];
  memberCount: number;
  inviteCount: number;
}

export interface Plan {
  id: string;
  name: string;
  price: string;
  monthlyPrice?: string;
  badge?: string;
  features: string[];
  isPopular?: boolean;
  isCurrent?: boolean;
}

export interface PlansSettingsConfig {
  currentPlan: Plan;
  plans: Plan[];
  features: {
    collaborators: number;
    papers: number;
    aiRequests: number;
  };
}

export interface HelpResource {
  id: string;
  name: string;
  url: string;
  description?: string;
}

export interface HelpSettingsConfig {
  resources: HelpResource[];
  support: {
    email: string;
    phone?: string;
    responseTime: string;
  };
}

export interface SettingsPageConfig {
  title: string;
  sidebar: SettingsSidebarConfig;
  sections: Record<string, SettingsSection>;
  people?: PeopleSettingsConfig;
  plans?: PlansSettingsConfig;
  help?: HelpSettingsConfig;
}

// Mock data for People settings
const mockMembers: TeamMember[] = [
  {
    id: "1",
    name: "Paridhi Mundra",
    email: "paridhi.mundra@example.com",
    role: "Member",
    status: "active",
    joinedAt: new Date("2024-01-15")
  },
  {
    id: "2", 
    name: "Paridhi Mundra",
    email: "paridhi.mundra@example.com",
    role: "Member",
    status: "active",
    joinedAt: new Date("2024-01-20")
  },
  {
    id: "3",
    name: "Paridhi Mundra", 
    email: "paridhi.mundra@example.com",
    role: "Member",
    status: "active",
    joinedAt: new Date("2024-02-01")
  }
];

const mockInvites: Invite[] = [];

// Mock data for Plans settings
const mockPlans: Plan[] = [
  {
    id: "free",
    name: "Free",
    price: "$0 per member / month",
    features: ["2 Collaborators", "5 Papers", "15 AI requests"],
    isCurrent: true
  },
  {
    id: "mega",
    name: "Mega",
    price: "$10 per member / month billed annually",
    monthlyPrice: "$12 billed monthly",
    features: ["10 Collaborators", "25 Papers", "100 AI requests"]
  },
  {
    id: "pro",
    name: "Pro",
    price: "$20 per member / month billed annually",
    monthlyPrice: "$24 billed monthly",
    badge: "Popular",
    isPopular: true,
    features: ["Unlimited Collaborators", "Unlimited Papers", "Unlimited AI requests"]
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "$26 per member / month billed annually",
    monthlyPrice: "$32 billed monthly",
    features: ["Everything in Pro", "Priority Support", "Custom Integrations"]
  }
];

// Mock data for Help settings
const mockHelpResources: HelpResource[] = [
  {
    id: "guide",
    name: "Guide",
    url: "https://docs.resxiv.com/guide",
    description: "Complete user guide and tutorials"
  },
  {
    id: "changelog",
    name: "Changelog",
    url: "https://docs.resxiv.com/changelog",
    description: "Latest updates and feature releases"
  },
  {
    id: "blogs",
    name: "Blogs",
    url: "https://blog.resxiv.com",
    description: "Latest news and insights"
  }
];

// Main settings page configuration
export const settingsConfig: SettingsPageConfig = {
  title: "Settings",
  
  sidebar: {
    title: "Settings",
    items: [
      {
        id: "general",
        label: "General",
        iconName: "Gear"
      },
      {
        id: "people",
        label: "People",
        iconName: "Users"
      },
      {
        id: "plans",
        label: "Plans",
        iconName: "ChartBar"
      },
      {
        id: "help",
        label: "Help",
        iconName: "Question"
      }
    ],
    upgradeButton: {
      text: "Upgrade to ResXiv Pro",
      iconName: "ArrowUp"
    }
  },

  sections: {
    general: {
      id: "general",
      title: "General",
      description: "Manage your project settings and preferences"
    },
    people: {
      id: "people",
      title: "People",
      description: "Manage team members and permissions"
    },
    plans: {
      id: "plans",
      title: "Plans",
      description: "Manage subscription and billing"
    },
    help: {
      id: "help",
      title: "Help",
      description: "Get help and contact support"
    }
  },

  people: {
    members: mockMembers,
    invites: mockInvites,
    memberCount: 13,
    inviteCount: 0
  },

  plans: {
    currentPlan: mockPlans[0], // Free plan
    plans: mockPlans,
    features: {
      collaborators: 2,
      papers: 5,
      aiRequests: 15
    }
  },

  help: {
    resources: mockHelpResources,
    support: {
      email: "contact@resxiv.com",
      responseTime: "Within 24 hours"
    }
  }
};

// Helper functions for settings management
export const getSettingsSection = (sectionId: string): SettingsSection | undefined => {
  return settingsConfig.sections[sectionId];
};

export const getAllSettingsSections = (): SettingsSection[] => {
  return Object.values(settingsConfig.sections);
};

export const getSettingsSidebarItems = (): SettingsSidebarItem[] => {
  return settingsConfig.sidebar.items;
};

export const getPeopleSettings = (): PeopleSettingsConfig | undefined => {
  return settingsConfig.people;
};

export const getPlansSettings = (): PlansSettingsConfig | undefined => {
  return settingsConfig.plans;
};

export const getHelpSettings = (): HelpSettingsConfig | undefined => {
  return settingsConfig.help;
};

export const getTeamMembers = (): TeamMember[] => {
  return settingsConfig.people?.members || [];
};

export const getInvites = (): Invite[] => {
  return settingsConfig.people?.invites || [];
};

export const getMemberCount = (): number => {
  return settingsConfig.people?.memberCount || 0;
};

export const getInviteCount = (): number => {
  return settingsConfig.people?.inviteCount || 0;
};

export const getCurrentPlan = (): Plan | undefined => {
  return settingsConfig.plans?.currentPlan;
};

export const getAllPlans = (): Plan[] => {
  return settingsConfig.plans?.plans || [];
};

export const getPlanFeatures = () => {
  return settingsConfig.plans?.features || {
    collaborators: 0,
    papers: 0,
    aiRequests: 0
  };
};

export const getHelpResources = (): HelpResource[] => {
  return settingsConfig.help?.resources || [];
};

export const getSupportInfo = () => {
  return settingsConfig.help?.support || {
    email: "contact@resxiv.com",
    responseTime: "Within 24 hours"
  };
};

export const validateProjectName = (name: string): boolean => {
  return name.trim().length >= 3 && name.trim().length <= 50;
};

export const validateProjectLink = (link: string): boolean => {
  try {
    new URL(link);
    return true;
  } catch {
    return false;
  }
};

export const formatProjectLink = (projectId: string): string => {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "https://resxiv.com";
  return `${baseUrl}/project/${projectId}`;
};

export const getLogoUploadRequirements = () => {
  return {
    minSize: { width: 200, height: 200 },
    maxSize: 5 * 1024 * 1024, // 5MB
    allowedTypes: ["image/png", "image/jpeg", "image/jpg"],
    aspectRatio: "1:1"
  };
};

export const getProjectSettings = (projectId: string) => {
  return {
    id: projectId,
    name: "PhD Research Thesis",
    description: "Research project for PhD thesis",
    visibility: "private" as const,
    createdAt: new Date(),
    updatedAt: new Date(),
    owner: {
      id: "user1",
      name: "John Smith",
      email: "john@example.com"
    }
  };
};

// People management functions
export const addTeamMember = (member: Omit<TeamMember, 'id' | 'joinedAt'>): TeamMember => {
  const newMember: TeamMember = {
    ...member,
    id: Date.now().toString(),
    joinedAt: new Date()
  };
  
  // In production, this would call an API
  console.log("Adding team member:", newMember);
  return newMember;
};

export const removeTeamMember = (memberId: string): void => {
  // In production, this would call an API
  console.log("Removing team member:", memberId);
};

export const sendInvite = (email: string, role: string): Invite => {
  const invite: Invite = {
    id: Date.now().toString(),
    email,
    role,
    status: "pending",
    invitedAt: new Date(),
    expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) // 7 days
  };
  
  // In production, this would call an API
  console.log("Sending invite:", invite);
  return invite;
};

export const cancelInvite = (inviteId: string): void => {
  // In production, this would call an API
  console.log("Canceling invite:", inviteId);
};

// Plans management functions
export const upgradePlan = (planId: string): void => {
  // In production, this would redirect to billing
  console.log("Upgrading to plan:", planId);
};

export const comparePlans = (): void => {
  // In production, this would redirect to comparison page
  console.log("Opening plan comparison");
};

export const contactSupport = (): void => {
  // In production, this would open support modal
  console.log("Opening support contact");
};

export const openFAQs = (): void => {
  // In production, this would redirect to FAQs page
  console.log("Opening FAQs");
};

// Help management functions
export const openHelpResource = (resourceId: string): void => {
  const resource = getHelpResources().find(r => r.id === resourceId);
  if (resource) {
    // In production, this would redirect to the resource URL
    console.log("Opening help resource:", resource.url);
  }
};

export const contactTeam = (): void => {
  // In production, this would open contact modal or redirect
  console.log("Opening contact team");
};

export const getSupportEmail = (): string => {
  return getSupportInfo().email;
}; 