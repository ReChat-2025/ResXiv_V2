# 📚 ResXiv Frontend - Complete Developer Guide

## 🌟 Welcome to ResXiv!

ResXiv is a modern research management platform built with cutting-edge web technologies. This comprehensive guide covers everything from basic setup to advanced development patterns, troubleshooting, and component examples.

## 📋 Table of Contents

### 🚀 Getting Started
1. [What is ResXiv?](#what-is-resxiv)
2. [Technology Stack](#technology-stack)
3. [Project Architecture](#project-architecture)
4. [Setup Instructions](#setup-instructions)
5. [Folder Structure](#folder-structure)

### 🧩 Core Concepts
6. [Key Concepts](#key-concepts)
7. [State Management](#state-management)
8. [API Integration](#api-integration)
9. [Styling System](#styling-system)

### 🎨 Development
10. [Component Examples](#component-examples)
11. [Advanced Patterns](#advanced-patterns)
12. [Custom Hooks](#custom-hooks)
13. [Form Handling](#form-handling)

### 🔧 Operations
14. [Development Workflow](#development-workflow)
15. [Troubleshooting](#troubleshooting)
16. [Performance](#performance)
17. [Testing & Deployment](#testing--deployment)
18. [Contributing](#contributing)

---

## 🎯 What is ResXiv?

ResXiv is a comprehensive research management platform that helps researchers:
- 📝 Manage research papers and documents
- 🤝 Collaborate with team members
- 💬 Chat and discuss research topics
- 📊 Organize projects and tasks
- 🔍 Search and analyze research content

Think of it as "Google Workspace for Researchers" - a unified platform for all research activities.

---

## 🛠️ Technology Stack

### Core Technologies

| Technology | Purpose | Why We Use It |
|------------|---------|---------------|
| **Next.js 15** | React Framework | Server-side rendering, routing, and performance optimization |
| **React 19** | UI Library | Component-based architecture and reactive updates |
| **TypeScript** | Type Safety | Catch errors early and improve code quality |
| **Tailwind CSS** | Styling | Utility-first CSS for rapid UI development |

### UI & Components

| Library | Purpose | Examples |
|---------|---------|----------|
| **Radix UI** | Accessible UI primitives | Dropdowns, dialogs, forms |
| **Lucide React** | Icon library | Buttons, navigation icons |
| **Phosphor Icons** | Additional icons | Specialty research icons |
| **Monaco Editor** | Code editing | Document editing, code snippets |

### State & Data

| Tool | Purpose | Use Case |
|------|---------|----------|
| **Zustand** | State management | Global app state, user preferences |
| **React Hook Form** | Form handling | Login, signup, settings forms |
| **SWR/React Query** | Data fetching | API calls, caching, synchronization |

---

## 🏗️ Project Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Browser  │────│  Next.js App    │────│  FastAPI Backend│
│                 │    │                 │    │                 │
│  - React UI     │    │  - SSR/SSG      │    │  - REST API     │
│  - State Mgmt   │    │  - API Routes   │    │  - Database     │
│  - Routing      │    │  - Middleware   │    │  - Auth         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Architecture

```
App Layout (Root)
├── Auth Provider (Global)
├── Theme Provider (Global)
├── Router (Next.js App Router)
│   ├── (auth) Route Group
│   │   ├── Login Page
│   │   ├── Signup Page
│   │   └── Password Reset
│   └── (dashboard) Route Group
│       ├── Projects
│       ├── Papers
│       ├── Chat
│       └── Settings
└── Toaster (Global Notifications)
```

---

## 🚀 Setup Instructions

### Prerequisites

Before you begin, make sure you have these installed:

1. **Node.js** (v18 or higher)
   ```bash
   node --version  # Should show v18.x.x or higher
   ```

2. **npm or yarn** (Package manager)
   ```bash
   npm --version  # Should show 8.x.x or higher
   ```

3. **Git** (Version control)
   ```bash
   git --version  # Should show git version 2.x.x
   ```

### Step-by-Step Setup

#### Step 1: Clone the Repository
```bash
git clone https://github.com/ReChat-2025/ResXiv_V2.git
cd ResXiv_V2/frontend
```

#### Step 2: Install Dependencies
```bash
npm install
# or
yarn install
```

#### Step 3: Environment Setup
Create environment files (if not already present):
```bash
# Create local environment file
touch .env.local
```

#### Step 4: Start Development Server
```bash
npm run dev
# or
yarn dev
```

#### Step 5: Open in Browser
Navigate to `http://localhost:3000` in your browser.

### What Happens When You Run `npm run dev`?

1. **Next.js starts** - The development server launches
2. **TypeScript compiles** - Your `.tsx` files are converted to JavaScript
3. **Tailwind processes** - CSS utility classes are generated
4. **Hot reload activates** - Changes auto-refresh the browser
5. **API proxy starts** - Routes `/api/*` to the backend server

---

## 📁 Folder Structure

Here's what each folder contains and why it exists:

```
frontend/
├── 📁 app/                     # Next.js App Router (main application)
│   ├── 📁 (auth)/             # Authentication route group
│   │   ├── 📁 login/          # Login page
│   │   ├── 📁 signup/         # Registration page
│   │   └── 📁 reset-password/ # Password reset
│   ├── 📁 (dashboard)/        # Main application routes
│   │   └── 📁 projects/       # Project management
│   ├── 📄 globals.css         # Global styles
│   ├── 📄 layout.tsx          # Root layout component
│   └── 📄 page.tsx            # Home page
├── 📁 components/             # Reusable UI components
│   ├── 📁 ui/                 # Basic UI primitives (buttons, inputs)
│   ├── 📁 auth/               # Authentication components
│   ├── 📁 forms/              # Form components
│   ├── 📁 layout/             # Layout components (header, sidebar)
│   ├── 📁 navigation/         # Navigation components
│   ├── 📁 papers/             # Paper management components
│   ├── 📁 projects/           # Project components
│   ├── 📁 settings/           # Settings components
│   ├── 📁 chat/               # Chat components
│   └── 📁 shared/             # Shared utility components
├── 📁 lib/                    # Utilities and services
│   ├── 📁 api/                # API service classes
│   ├── 📁 services/           # Business logic services
│   ├── 📁 stores/             # Zustand state stores
│   ├── 📁 config/             # Configuration files
│   ├── 📄 utils.ts            # Utility functions
│   └── 📄 auth-config.ts      # Authentication configuration
├── 📁 hooks/                  # Custom React hooks
│   ├── 📄 useLoginForm.ts     # Login form logic
│   ├── 📄 useSignupForm.ts    # Signup form logic
│   └── 📄 use-toast.ts        # Toast notification hook
├── 📁 public/                 # Static assets (images, icons, etc.)
├── 📄 package.json            # Dependencies and scripts
├── 📄 next.config.ts          # Next.js configuration
├── 📄 tailwind.config.js      # Tailwind CSS configuration
├── 📄 tsconfig.json           # TypeScript configuration
└── 📄 README.md               # This file!
```

### Understanding Route Groups

Next.js App Router uses **route groups** (folders in parentheses) to organize routes without affecting the URL structure:

- `(auth)` - Groups authentication-related pages
- `(dashboard)` - Groups main application pages

**Example:**
- File: `app/(auth)/login/page.tsx`
- URL: `/login` (not `/auth/login`)

---

## 🧩 Key Concepts

### 1. Next.js App Router

Next.js 13+ uses a new routing system based on the file system:

```
app/
├── page.tsx                 # Route: /
├── about/page.tsx          # Route: /about
├── blog/
│   ├── page.tsx            # Route: /blog
│   └── [slug]/page.tsx     # Route: /blog/[anything]
└── (auth)/
    └── login/page.tsx      # Route: /login
```

**Key Files:**
- `page.tsx` - The actual page component
- `layout.tsx` - Wraps pages with common UI
- `loading.tsx` - Loading state while page loads
- `error.tsx` - Error state when something goes wrong

### 2. React Components

Components are the building blocks of React applications:

```tsx
// Basic component
function WelcomeMessage({ name }: { name: string }) {
  return <h1>Hello, {name}!</h1>
}

// Component with state
function Counter() {
  const [count, setCount] = useState(0)
  
  return (
    <button onClick={() => setCount(count + 1)}>
      Count: {count}
    </button>
  )
}
```

### 3. TypeScript Basics

TypeScript adds type safety to JavaScript:

```tsx
// Define types for props
interface UserProps {
  name: string
  age: number
  isActive: boolean
}

// Use the types
function UserCard({ name, age, isActive }: UserProps) {
  return (
    <div>
      <h3>{name}</h3>
      <p>Age: {age}</p>
      <p>Status: {isActive ? 'Active' : 'Inactive'}</p>
    </div>
  )
}
```

---

## 🗃️ State Management

### Global State with Zustand

```tsx
// lib/stores/user-store.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  name: string
  email: string
  avatar?: string
}

interface UserState {
  user: User | null
  isAuthenticated: boolean
  setUser: (user: User) => void
  logout: () => void
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      
      setUser: (user) => set({
        user,
        isAuthenticated: true
      }),
      
      logout: () => set({
        user: null,
        isAuthenticated: false
      }),
    }),
    {
      name: 'user-storage',
    }
  )
)
```

### Local State with useState

```tsx
import { useState } from 'react'

function SearchBox() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  
  const handleSearch = async () => {
    const data = await searchAPI(query)
    setResults(data)
  }
  
  return (
    <div>
      <input 
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
      />
      <button onClick={handleSearch}>Search</button>
      
      {results.map(result => (
        <div key={result.id}>{result.title}</div>
      ))}
    </div>
  )
}
```

---

## 🔌 API Integration

### API Service Classes

```tsx
// lib/api/auth-api.ts
class AuthAPI {
  private baseUrl: string
  
  constructor() {
    // Use Next.js API proxy in development
    if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
      this.baseUrl = '' // Use Next.js proxy
    } else {
      this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    }
  }
  
  async login(email: string, password: string) {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })
    
    if (!response.ok) {
      throw new Error('Login failed')
    }
    
    return response.json()
  }
}

export const authAPI = new AuthAPI()
```

### API Hooks

```tsx
// hooks/useAuth.ts
import { useState } from 'react'
import { authAPI } from '@/lib/api/auth-api'
import { useUserStore } from '@/lib/stores/user-store'

export function useAuth() {
  const [isLoading, setIsLoading] = useState(false)
  const { setUser, logout: clearAuth } = useUserStore()
  
  const login = async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const { user, token } = await authAPI.login(email, password)
      setUser(user)
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    } finally {
      setIsLoading(false)
    }
  }
  
  return { login, isLoading }
}
```

---

## 🎨 Styling System

### Tailwind CSS Basics

Tailwind uses utility classes for styling:

```tsx
// Instead of CSS:
.button {
  background-color: blue;
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
}

// Use Tailwind classes:
<button className="bg-blue-500 text-white px-4 py-2 rounded">
  Click me
</button>
```

### Common Tailwind Patterns

#### Layout
```tsx
// Flexbox
<div className="flex items-center justify-between">
  <span>Left content</span>
  <span>Right content</span>
</div>

// Grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
</div>

// Responsive design
<div className="w-full md:w-1/2 lg:w-1/3">
  Responsive width
</div>
```

#### Colors & Spacing
```tsx
// Colors
<div className="bg-blue-500 text-white">Blue background</div>
<div className="text-gray-700 hover:text-blue-600">Hover effect</div>

// Spacing
<div className="m-4 p-6">        // margin: 16px, padding: 24px
<div className="mt-2 mb-4 px-3">  // margin-top: 8px, etc.
```

---

## 🧩 Component Examples

### Button Component with Variants

```tsx
// components/ui/button.tsx
import { forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        default: "h-10 py-2 px-4",
        sm: "h-9 px-3 rounded-md",
        lg: "h-11 px-8 rounded-md",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean
  icon?: React.ReactNode
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, icon, children, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-transparent border-t-current" />
        ) : icon ? (
          <span className="mr-2">{icon}</span>
        ) : null}
        {children}
      </button>
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

### Input Component with Validation

```tsx
// components/ui/input.tsx
import { forwardRef, useState } from 'react'
import { cn } from '@/lib/utils'
import { Eye, EyeOff, AlertCircle } from 'lucide-react'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: React.ReactNode
  showPasswordToggle?: boolean
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ 
    className, 
    type, 
    label, 
    error, 
    hint, 
    leftIcon, 
    showPasswordToggle,
    id,
    ...props 
  }, ref) => {
    const [showPassword, setShowPassword] = useState(false)
    const [isFocused, setIsFocused] = useState(false)
    
    const inputType = type === 'password' && showPassword ? 'text' : type
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
    
    return (
      <div className="space-y-1">
        {label && (
          <label 
            htmlFor={inputId}
            className="text-sm font-medium leading-none"
          >
            {label}
            {props.required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
              {leftIcon}
            </div>
          )}
          
          <input
            type={inputType}
            id={inputId}
            className={cn(
              "flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
              leftIcon && "pl-10",
              (showPasswordToggle || error) && "pr-10",
              error && "border-red-500 focus-visible:ring-red-500",
              isFocused && !error && "border-primary",
              className
            )}
            ref={ref}
            onFocus={(e) => {
              setIsFocused(true)
              props.onFocus?.(e)
            }}
            onBlur={(e) => {
              setIsFocused(false)
              props.onBlur?.(e)
            }}
            {...props}
          />
          
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center space-x-1">
            {error && (
              <AlertCircle className="h-4 w-4 text-red-500" />
            )}
            
            {showPasswordToggle && type === 'password' && (
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-gray-500 hover:text-gray-700"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            )}
          </div>
        </div>
        
        {(error || hint) && (
          <p className={cn(
            "text-xs",
            error ? "text-red-500" : "text-gray-500"
          )}>
            {error || hint}
          </p>
        )}
      </div>
    )
  }
)
Input.displayName = "Input"

export { Input }
```

---

## 🛠️ Advanced Patterns

### Custom Hooks for Data Fetching

```tsx
// hooks/useApi.ts
import { useState, useEffect, useCallback } from 'react'

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function useApi<T>(
  apiFunction: () => Promise<T>,
  dependencies: any[] = []
) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  })
  
  const execute = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }))
    
    try {
      const result = await apiFunction()
      setState({ data: result, loading: false, error: null })
      return result
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      setState({ data: null, loading: false, error: errorMessage })
      throw error
    }
  }, dependencies)
  
  useEffect(() => {
    execute()
  }, [execute])
  
  return {
    ...state,
    refetch: execute,
  }
}
```

### Compound Components Pattern

```tsx
// components/ui/card.tsx
import { createContext, useContext } from 'react'
import { cn } from '@/lib/utils'

interface CardContextValue {
  variant: 'default' | 'elevated' | 'outlined'
}

const CardContext = createContext<CardContextValue | null>(null)

function Card({ children, variant = 'default', className }: {
  children: React.ReactNode
  variant?: 'default' | 'elevated' | 'outlined'
  className?: string
}) {
  return (
    <CardContext.Provider value={{ variant }}>
      <div
        className={cn(
          'rounded-lg',
          {
            'bg-white shadow-sm border': variant === 'default',
            'bg-white shadow-lg': variant === 'elevated',
            'bg-white border-2': variant === 'outlined',
          },
          className
        )}
      >
        {children}
      </div>
    </CardContext.Provider>
  )
}

function CardHeader({ children, className }: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('px-6 py-4 border-b', className)}>
      {children}
    </div>
  )
}

function CardContent({ children, className }: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('px-6 py-4', className)}>
      {children}
    </div>
  )
}

Card.Header = CardHeader
Card.Content = CardContent

export { Card }
```

---

## 🪝 Custom Hooks

### Form Hook

```tsx
// hooks/useForm.ts
import { useState, useCallback } from 'react'

type ValidationRule<T> = {
  required?: boolean
  minLength?: number
  pattern?: RegExp
  custom?: (value: T) => string | null
}

type ValidationRules<T> = {
  [K in keyof T]?: ValidationRule<T[K]>
}

type FormErrors<T> = {
  [K in keyof T]?: string
}

export function useForm<T extends Record<string, any>>(
  initialValues: T,
  validationRules?: ValidationRules<T>
) {
  const [values, setValues] = useState<T>(initialValues)
  const [errors, setErrors] = useState<FormErrors<T>>({})
  const [touched, setTouched] = useState<Record<keyof T, boolean>>({} as Record<keyof T, boolean>)
  
  const validateField = useCallback((name: keyof T, value: any) => {
    const rules = validationRules?.[name]
    if (!rules) return null
    
    if (rules.required && (!value || value.toString().trim() === '')) {
      return 'This field is required'
    }
    
    if (typeof value === 'string') {
      if (rules.minLength && value.length < rules.minLength) {
        return `Minimum length is ${rules.minLength} characters`
      }
      
      if (rules.pattern && !rules.pattern.test(value)) {
        return 'Invalid format'
      }
    }
    
    if (rules.custom) {
      return rules.custom(value)
    }
    
    return null
  }, [validationRules])
  
  const handleChange = useCallback((name: keyof T, value: any) => {
    setValues(prev => ({ ...prev, [name]: value }))
    
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: undefined }))
    }
  }, [errors])
  
  const handleBlur = useCallback((name: keyof T) => {
    setTouched(prev => ({ ...prev, [name]: true }))
    
    const error = validateField(name, values[name])
    setErrors(prev => ({ ...prev, [name]: error || undefined }))
  }, [values, validateField])
  
  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    isValid: Object.keys(errors).length === 0,
  }
}
```

### Local Storage Hook

```tsx
// hooks/useLocalStorage.ts
import { useState, useEffect } from 'react'

export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return initialValue
    }
    
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error)
      return initialValue
    }
  })
  
  const setValue = (value: T | ((prev: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore))
      }
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error)
    }
  }
  
  return [storedValue, setValue]
}
```

---

## 📝 Form Handling

### Complete Login Form Example

```tsx
// components/auth/login-form.tsx
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/hooks/useAuth'
import { Mail, Lock } from 'lucide-react'

export function LoginForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  
  const { login, isLoading } = useAuth()
  const router = useRouter()
  
  const validateForm = () => {
    const newErrors: typeof errors = {}
    
    if (!email) {
      newErrors.email = 'Email is required'
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = 'Email is invalid'
    }
    
    if (!password) {
      newErrors.password = 'Password is required'
    } else if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) return
    
    const result = await login(email, password)
    if (result.success) {
      router.push('/dashboard')
    }
  }
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md mx-auto">
      <h2 className="text-2xl font-bold text-center mb-6">Sign In</h2>
      
      <Input
        label="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={errors.email}
        leftIcon={<Mail className="h-4 w-4" />}
        placeholder="Enter your email"
        required
      />
      
      <Input
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={errors.password}
        leftIcon={<Lock className="h-4 w-4" />}
        placeholder="Enter your password"
        showPasswordToggle
        required
      />
      
      <Button 
        type="submit" 
        className="w-full" 
        loading={isLoading}
      >
        Sign In
      </Button>
    </form>
  )
}
```

---

## ⚡ Development Workflow

### Daily Development Process

1. **Start the servers**
   ```bash
   # Terminal 1 - Frontend
   cd frontend
   npm run dev
   
   # Terminal 2 - Backend (if needed)
   cd backend/resxiv_backend
   ./start_dev.sh
   ```

2. **Make changes**
   - Edit files in your code editor
   - See changes instantly in the browser (hot reload)

3. **Test your changes**
   - Check the browser for visual changes
   - Test functionality manually
   - Check browser console for errors

4. **Commit your work**
   ```bash
   git add .
   git commit -m "Add new feature: user profile page"
   git push
   ```

### Code Quality Tools

```bash
# Check for type errors
npx tsc --noEmit

# Check for code style issues
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix
```

---

## 🔧 Troubleshooting

### Common Setup Issues

#### Node.js Version Incompatibility

**Error:**
```bash
Error: The engine "node" is incompatible with this module. Expected version ">=18.0.0".
```

**Solution:**
```bash
# Check your Node.js version
node --version

# If version is below 18, update Node.js
# Using Node Version Manager (nvm)
nvm install 18
nvm use 18
```

#### Package Installation Failures

**Error:**
```bash
npm ERR! peer dep missing: react@^18.0.0
```

**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall packages
npm install
```

#### Port Already in Use

**Error:**
```bash
Error: listen EADDRINUSE :::3000
```

**Solution:**
```bash
# Find what's using port 3000
lsof -ti:3000

# Kill the process (replace PID with actual number)
kill -9 PID

# Or run on a different port
npm run dev -- --port 3001
```

### Runtime Errors

#### Hydration Mismatch

**Error:**
```bash
Warning: Text content did not match. Server: "Loading..." Client: "Welcome, John!"
```

**Solution:**
```tsx
// ❌ Problem: Different content on server/client
function WelcomeMessage() {
  const user = getCurrentUser() // Different on server vs client
  return <div>Welcome, {user?.name || 'Loading...'}</div>
}

// ✅ Solution: Use useEffect for client-only data
function WelcomeMessage() {
  const [user, setUser] = useState(null)
  
  useEffect(() => {
    setUser(getCurrentUser())
  }, [])
  
  return <div>Welcome, {user?.name || 'Loading...'}</div>
}
```

#### API Connection Issues

**Error:**
```bash
Failed to fetch
```

**Solutions:**
1. Check if backend is running
2. Verify API URLs in configuration
3. Check CORS settings
4. Inspect network tab in browser

### Debugging Techniques

#### Browser DevTools
1. **Console** - View errors and logs
2. **Network** - Check API requests
3. **Elements** - Inspect HTML and CSS
4. **Sources** - Set breakpoints in code

#### Strategic Console Logging
```tsx
function MyComponent({ user }) {
  console.log('MyComponent render:', { user })
  
  useEffect(() => {
    console.log('MyComponent mounted')
    return () => console.log('MyComponent unmounted')
  }, [])
  
  return <div>Hello {user.name}</div>
}
```

---

## ⚡ Performance

### Optimization Techniques

#### React.memo for Expensive Components
```tsx
const ExpensiveComponent = React.memo(function ExpensiveComponent({ data }) {
  const processedData = useMemo(() => {
    return data.map(item => ({
      ...item,
      processed: heavyCalculation(item)
    }))
  }, [data])
  
  return <div>{processedData.map(item => <div key={item.id}>{item.name}</div>)}</div>
})
```

#### Dynamic Imports for Code Splitting
```tsx
// ❌ Static import
import HeavyComponent from './HeavyComponent'

// ✅ Dynamic import
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <div>Loading...</div>,
  ssr: false
})
```

#### Image Optimization
```tsx
import Image from 'next/image'

<Image
  src="/large-image.jpg"
  alt="Description"
  width={500}
  height={300}
  loading="lazy"
  placeholder="blur"
/>
```

---

## 🧪 Testing & Deployment

### Manual Testing Checklist

#### Authentication Flow
- [ ] User can sign up with valid email
- [ ] User can log in with correct credentials
- [ ] User sees error with wrong credentials
- [ ] User can reset password

#### Navigation
- [ ] All menu items work
- [ ] Back button works correctly
- [ ] URLs are correct
- [ ] Page refreshes don't break

#### Responsive Design
- [ ] App works on mobile (375px width)
- [ ] App works on tablet (768px width)
- [ ] App works on desktop (1200px+ width)

### Building for Production

```bash
# Build the application
npm run build

# Test the production build locally
npm run start
```

### Environment Variables for Production

```bash
# .env.production
NEXT_PUBLIC_API_URL=https://api.resxiv.com
NEXT_PUBLIC_APP_NAME=ResXiv
NEXT_PUBLIC_ENVIRONMENT=production
```

---

## 🤝 Contributing

### Code Style Guidelines

#### File Naming
- Components: `PascalCase.tsx` (e.g., `UserProfile.tsx`)
- Hooks: `camelCase.ts` (e.g., `useAuth.ts`)
- Utilities: `kebab-case.ts` (e.g., `api-client.ts`)
- Pages: `page.tsx` (Next.js convention)

#### Component Structure
```tsx
// 1. Imports (external libraries first, then internal)
import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'

// 2. Types/Interfaces
interface UserProfileProps {
  userId: string
  onUpdate?: (user: User) => void
}

// 3. Component
export function UserProfile({ userId, onUpdate }: UserProfileProps) {
  // 4. State and hooks
  const [user, setUser] = useState<User | null>(null)
  
  // 5. Effects
  useEffect(() => {
    loadUser()
  }, [userId])
  
  // 6. Functions
  const loadUser = async () => {
    // Implementation
  }
  
  // 7. Render
  return (
    <div className="p-4">
      <h1>{user?.name}</h1>
    </div>
  )
}
```

#### Git Workflow
```bash
# 1. Create feature branch
git checkout -b feature/user-profile-page

# 2. Make changes and commit
git add .
git commit -m "feat: add user profile page with edit functionality"

# 3. Push and create pull request
git push origin feature/user-profile-page
```

---

## 📚 Learning Resources

### Documentation
- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

### Tools and Extensions

#### VS Code Extensions
- **ES7+ React/Redux/React-Native snippets** - Code snippets
- **TypeScript Importer** - Auto import suggestions
- **Tailwind CSS IntelliSense** - Tailwind class completion
- **Prettier** - Code formatting
- **ESLint** - Code linting

#### Browser Extensions
- **React Developer Tools** - Debug React components
- **Redux DevTools** - Debug state management

---

## 🎯 Quick Reference

### Essential Commands
```bash
# Start development
npm run dev

# Build for production
npm run build

# Run linting
npm run lint

# Type checking
npx tsc --noEmit
```

### Common Imports
```tsx
// React essentials
import { useState, useEffect } from 'react'

// Next.js
import Link from 'next/link'
import { useRouter } from 'next/navigation'

// UI components
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// Icons
import { Search, User, Settings } from 'lucide-react'

// Utilities
import { cn } from '@/lib/utils'
```

---

## 🆘 Getting Help

### Self-Help Checklist
1. **Check the error message** - Often tells you exactly what's wrong
2. **Search this documentation** - Use Ctrl+F to find relevant sections
3. **Check browser console** - Look for JavaScript errors
4. **Verify file paths** - Ensure imports are correct
5. **Restart dev server** - Sometimes fixes caching issues

### When to Ask for Help
- After trying solutions in the troubleshooting section
- When you need clarification on architecture decisions
- For complex feature implementation guidance

### How to Ask for Help
Include this information:
1. **What you're trying to do** - Brief description
2. **What's happening** - Exact error message or behavior
3. **What you've tried** - Solutions you've attempted
4. **Environment** - OS, Node version, browser
5. **Code sample** - Minimal example that reproduces the issue

---

## 🎉 Welcome to the Team!

Whether you're just starting your coding journey or you're an experienced developer, this documentation is designed to help you succeed with the ResXiv frontend.

**Remember:**
- 🚀 Start small and build up your knowledge
- 🔍 Don't hesitate to explore the codebase
- 💬 Ask questions when you're stuck
- 🤝 Help improve the documentation for others
- 🎯 Focus on learning, not perfection

**Happy coding!** 🚀

---

*Last updated: 2025-01-08*
*Documentation maintained by the ResXiv development team*