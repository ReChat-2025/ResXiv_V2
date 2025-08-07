// Authentication configuration for scalable, production-ready auth system
// All content can be easily customized for different deployments

export interface AuthPageConfig {
  title: string;
  subtitle?: string;
  cardTitle: string;
  submitButton: {
    idle: string;
    loading: string;
  };
  socialLogin: {
    enabled: boolean;
    providers: SocialProvider[];
    dividerText: string;
  };
  links: AuthLink[];
}

export interface SocialProvider {
  id: string;
  name: string;
  icon: string; // Component name or icon identifier
  buttonText: string;
}

export interface AuthLink {
  text: string;
  linkText: string;
  href: string;
}

export interface FormFieldConfig {
  id: string;
  name: string;
  type: string;
  label: string;
  placeholder: string;
  required: boolean;
  validation?: {
    minLength?: number;
    pattern?: string;
    customMessage?: string;
  };
  helpText?: string;
  gridColumn?: string; // For grid layouts
}

export interface ValidationMessages {
  required: string;
  email: string;
  passwordMismatch: string;
  termsRequired: string;
  minLength: (min: number) => string;
  genericError: string;
}

// Main authentication configuration
export const authConfig = {
  // Routes configuration
  routes: {
    login: "/login",
    signup: "/signup",
    forgotPassword: "/forgot-password",
    resetPassword: "/auth/reset-password",
    verifyEmail: "/auth/verify-email",
    terms: "/terms",
    privacy: "/privacy",
    home: "/"
  },

  // Validation messages
  validation: {
    required: "This field is required",
    email: "Please enter a valid email address",
    passwordMismatch: "Passwords don't match",
    termsRequired: "Please accept the terms and conditions",
    minLength: (min: number) => `Must be at least ${min} characters long`,
    genericError: "Something went wrong. Please try again."
  } as ValidationMessages,

  // Login page configuration
  login: {
    title: "Welcome back",
    cardTitle: "Sign in",
    submitButton: {
      idle: "Sign in",
      loading: "Signing in..."
    },
    socialLogin: {
      enabled: false,
      providers: [
        {
          id: "google",
          name: "Google",
          icon: "GoogleIcon",
          buttonText: "Continue with Google"
        }
      ],
      dividerText: "Or continue with"
    },
    links: [
      {
        text: "Don't have an account?",
        linkText: "Sign up",
        href: "/signup"
      }
    ],
    fields: [
      {
        id: "email",
        name: "email",
        type: "email",
        label: "Email address",
        placeholder: "Enter your email",
        required: true
      },
      {
        id: "password",
        name: "password",
        type: "password",
        label: "Password",
        placeholder: "Enter your password",
        required: true
      }
    ] as FormFieldConfig[],
    features: {
      rememberMe: {
        enabled: true,
        label: "Remember me"
      },
      forgotPassword: {
        enabled: true,
        text: "Forgot password?",
        href: "/forgot-password"
      }
    }
  } as AuthPageConfig & { fields: FormFieldConfig[]; features: any },

  // Signup page configuration
  signup: {
    title: "Create your account",
    cardTitle: "Sign up",
    submitButton: {
      idle: "Create account",
      loading: "Creating account..."
    },
    socialLogin: {
      enabled: true,
      providers: [
        {
          id: "google",
          name: "Google",
          icon: "GoogleIcon",
          buttonText: "Continue with Google"
        }
      ],
      dividerText: "Or continue with"
    },
    links: [
      {
        text: "Already have an account?",
        linkText: "Sign in",
        href: "/login"
      }
    ],
    fields: [
      {
        id: "firstName",
        name: "firstName",
        type: "text",
        label: "First name",
        placeholder: "John",
        required: true,
        gridColumn: "1/2"
      },
      {
        id: "lastName",
        name: "lastName",
        type: "text",
        label: "Last name",
        placeholder: "Doe",
        required: true,
        gridColumn: "2/3"
      },
      {
        id: "email",
        name: "email",
        type: "email",
        label: "Email address",
        placeholder: "john.doe@example.com",
        required: true
      },
      {
        id: "password",
        name: "password",
        type: "password",
        label: "Password",
        placeholder: "Create a strong password",
        required: true,
        validation: {
          minLength: 8,
          pattern: "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&].{7,}$",
          customMessage: "Password must contain at least 8 characters with uppercase, lowercase, number and special character"
        },
        helpText: "Must contain uppercase, lowercase, number and special character"
      },
      {
        id: "confirmPassword",
        name: "confirmPassword",
        type: "password",
        label: "Confirm password",
        placeholder: "Confirm your password",
        required: true
      }
    ] as FormFieldConfig[],
    features: {
      termsAcceptance: {
        enabled: true,
        label: "I agree to the",
        termsLink: {
          text: "Terms of Service",
          href: "/terms"
        },
        privacyLink: {
          text: "Privacy Policy",
          href: "/privacy"
        }
      }
    }
  } as AuthPageConfig & { fields: FormFieldConfig[]; features: any }
} as const;

// Helper functions for configuration
export const getAuthConfig = (page: 'login' | 'signup') => {
  return authConfig[page];
};

export const getValidationMessage = (type: keyof ValidationMessages, ...args: any[]): string => {
  const message = authConfig.validation[type];
  return typeof message === 'function' ? (message as any)(...args) : message as string;
}; 