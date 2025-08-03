# ResXiv Frontend

A modern, research-focused platform built with Next.js, TypeScript, and a comprehensive design system.

## 🚀 Features

- **Modern Design System**: Consistent, accessible, and scalable components
- **Research-Focused**: Specialized tools for academic research and collaboration
- **AI-Powered**: Intelligent paper analysis and research assistance
- **Real-time Collaboration**: Team-based research workflows
- **Responsive Design**: Works seamlessly across all devices

## 🛠️ Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom design tokens
- **Icons**: Phosphor Icons
- **UI Components**: Radix UI primitives with custom components
- **State Management**: Zustand
- **Design System**: Custom built with CVA (Class Variance Authority)

## 🎨 Design System

We've built a comprehensive design system that ensures consistency across the platform:

- **Centralized Icon System**: Categorized Phosphor icons for consistent usage
- **Component Variants**: Flexible components with multiple variants
- **Layout Components**: Reusable layout patterns (PageLayout, SidebarLayout, ThreeColumnLayout)
- **Empty States**: Predefined empty states for common scenarios
- **Loading States**: Comprehensive loading and skeleton components

See [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) for detailed documentation.

## 📁 Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── globals.css        # Global styles and design tokens
│   ├── layout.tsx         # Root layout
│   └── (routes)/          # Page routes
├── components/            # Reusable components
│   ├── ui/               # Base UI components
│   ├── layout/           # Layout components
│   ├── navigation/       # Navigation components
│   └── (feature)/        # Feature-specific components
├── lib/                  # Utilities and configurations
│   ├── design-system.ts  # Design system configuration
│   └── utils.ts          # Utility functions
└── hooks/                # Custom React hooks
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ResXiv_V2/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## 🧩 Core Components

### Icon System

Our centralized icon system provides type-safe, categorized icons:

```tsx
import { NavigationIcon, ActionIcon, UIIcon, ContentIcon } from "@/components/ui/icon";

// Navigation icons
<NavigationIcon variant="home" size={24} />

// Action icons  
<ActionIcon variant="add" size={16} />

// UI icons
<UIIcon variant="search" size={20} />

// Content icons
<ContentIcon variant="fileText" size={24} />
```

### Layout Components

Standardized layout patterns for consistent page structure:

```tsx
import { PageLayout, SidebarLayout, ThreeColumnLayout } from "@/components/layout/page-layout";

// Basic page layout
<PageLayout currentProject={project} userAvatars={avatars}>
  {/* Page content */}
</PageLayout>

// Sidebar layout
<SidebarLayout sidebar={<NavigationSidebar />}>
  {/* Main content */}
</SidebarLayout>

// Three-column layout
<ThreeColumnLayout 
  leftSidebar={<PapersSidebar />}
  rightSidebar={<ChatSidebar />}
>
  {/* Main content */}
</ThreeColumnLayout>
```

### UI Components

Modern, accessible components built with Radix UI:

```tsx
import { Button, Card, Badge } from "@/components/ui";

// Button with variants
<Button variant="default" size="md">
  Primary Action
</Button>

// Card with variants
<Card variant="interactive" padding="lg">
  <CardContent>Content</CardContent>
</Card>

// Badge with variants
<Badge variant="secondary" size="sm">
  Status
</Badge>
```

## 📱 Pages

### Home (`/home`)
AI-powered research assistant with conversation interface and quick actions.

### Papers (`/papers`)
Paper management with PDF viewer, chat interface, and organization tools.

### Draft (`/draft`)
LaTeX editor with real-time preview and AI assistance.

### Collaborate (`/collaborate`)
Team collaboration with chat, file sharing, and project management.

### Tasks (`/tasks`)
Task management with kanban boards and progress tracking.

### Journals (`/journals`)
Research journal organization and note-taking.

### Settings (`/settings`)
User preferences, project management, and account settings.

## 🎯 Key Features

### Research-Focused Design
- **Paper Management**: Organize and analyze research papers
- **AI Assistance**: Intelligent insights and recommendations
- **Collaboration**: Team-based research workflows
- **Writing Tools**: LaTeX editor with real-time preview

### Modern UX
- **Responsive Design**: Works on all devices
- **Accessibility**: WCAG AA compliant
- **Performance**: Optimized for fast loading
- **Consistency**: Unified design system

### Developer Experience
- **Type Safety**: Full TypeScript coverage
- **Component Library**: Reusable, documented components
- **Design System**: Consistent patterns and tokens
- **Hot Reload**: Fast development iteration

## 🛠️ Development

### Adding New Components

1. **Create component** in appropriate directory
2. **Add TypeScript types** for props
3. **Use design system tokens** for styling
4. **Add variants** using CVA
5. **Document** in DESIGN_SYSTEM.md

### Styling Guidelines

- Use Tailwind CSS classes
- Leverage design tokens from `lib/design-system.ts`
- Follow spacing scale (xs, sm, md, lg, xl)
- Use semantic color names

### Icon Guidelines

- Use Phosphor Icons exclusively
- Categorize properly (navigation, actions, ui, content)
- Add to icon system in `lib/design-system.ts`
- Use consistent sizes (16, 20, 24, 32, 48)

## 🚀 Deployment

### Build for Production

```bash
npm run build
```

### Start Production Server

```bash
npm start
```

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=your-api-url
NEXT_PUBLIC_APP_NAME=ResXiv
```

## 📚 Documentation

- [Design System](./DESIGN_SYSTEM.md) - Comprehensive design system documentation
- [Component Usage](./COMPONENT_USAGE.md) - Component usage examples
- [Deployment Guide](./DEPLOYMENT_READY.md) - Deployment instructions

## 🤝 Contributing

1. Follow the design system guidelines
2. Use TypeScript for all new code
3. Add proper documentation
4. Test on multiple devices
5. Ensure accessibility compliance

## 📄 License

This project is licensed under the MIT License.

---

Built with ❤️ for the research community.
