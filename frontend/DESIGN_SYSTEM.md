# ResXiv Design System

A modern, consistent design system for the ResXiv research platform built with React, TypeScript, and Tailwind CSS.

## 🎨 Design Principles

- **Consistency**: All components follow the same design patterns and use consistent spacing, typography, and colors
- **Modularity**: Components are built to be reusable and composable
- **Accessibility**: All components are built with accessibility in mind
- **Performance**: Optimized for fast loading and smooth interactions
- **Scalability**: Designed to grow with the application

## 🎯 Color Palette

Our design system uses a sophisticated beige color palette that's easy on the eyes and perfect for research work:

### Primary Colors
- **Background**: Light beige (`#EFEFED`)
- **Foreground**: Dark gray (`#262626`)
- **Primary**: Dark gray (`#262626`)
- **Secondary**: Light gray (`#E7E5E3`)

### Semantic Colors
- **Success**: Green (`#22C55E`)
- **Warning**: Yellow (`#F59E0B`)
- **Error**: Red (`#EF4444`)
- **Info**: Blue (`#3B82F6`)

## 📝 Typography

We use Manrope as our primary font family for excellent readability:

```css
font-family: var(--font-manrope), Manrope, system-ui, -apple-system, sans-serif;
```

### Font Sizes
- `xs`: 0.75rem (12px)
- `sm`: 0.875rem (14px)
- `base`: 1rem (16px)
- `lg`: 1.125rem (18px)
- `xl`: 1.25rem (20px)
- `2xl`: 1.5rem (24px)
- `3xl`: 1.875rem (30px)
- `4xl`: 2.25rem (36px)

## 🧩 Core Components

### Icon System

Our centralized icon system uses Phosphor Icons with consistent categorization:

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

### Button Component

Modern button with multiple variants and states:

```tsx
import { Button } from "@/components/ui/button";

// Variants
<Button variant="default">Primary</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link</Button>
<Button variant="destructive">Delete</Button>

// Sizes
<Button size="sm">Small</Button>
<Button size="md">Medium</Button>
<Button size="lg">Large</Button>

// With icons
<Button leftIcon={<ActionIcon variant="add" />}>
  Add Item
</Button>
```

### Card Component

Flexible card component with multiple variants:

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// Variants
<Card variant="default">Default Card</Card>
<Card variant="outline">Outline Card</Card>
<Card variant="ghost">Ghost Card</Card>
<Card variant="elevated">Elevated Card</Card>
<Card variant="interactive">Interactive Card</Card>

// Padding options
<Card padding="none">No padding</Card>
<Card padding="sm">Small padding</Card>
<Card padding="md">Medium padding</Card>
<Card padding="lg">Large padding</Card>
```

### Layout Components

#### PageLayout
Standard page layout with navbar:

```tsx
import { PageLayout } from "@/components/layout/page-layout";

<PageLayout
  currentProject={project}
  showProjectSelector={true}
  userAvatars={userAvatars}
  notifications={notifications}
  onNotificationClick={handleNotificationClick}
>
  {/* Page content */}
</PageLayout>
```

#### SidebarLayout
Layout with collapsible sidebar:

```tsx
import { SidebarLayout } from "@/components/layout/page-layout";

<SidebarLayout
  sidebar={<NavigationSidebar />}
  sidebarWidth="16rem"
  sidebarCollapsed={collapsed}
  onSidebarToggle={toggleSidebar}
>
  {/* Main content */}
</SidebarLayout>
```

#### ThreeColumnLayout
Layout with left and right sidebars:

```tsx
import { ThreeColumnLayout } from "@/components/layout/page-layout";

<ThreeColumnLayout
  leftSidebar={<PapersSidebar />}
  rightSidebar={<ChatSidebar />}
  leftSidebarCollapsed={leftCollapsed}
  rightSidebarCollapsed={rightCollapsed}
  onLeftSidebarToggle={toggleLeft}
  onRightSidebarToggle={toggleRight}
>
  {/* Main content */}
</ThreeColumnLayout>
```

### Empty States

Predefined empty states for common scenarios:

```tsx
import { EmptyStates } from "@/components/ui/empty-state";

// No data
<EmptyStates.NoData />

// No results
<EmptyStates.NoResults />

// No files
<EmptyStates.NoFiles />

// No projects
<EmptyStates.NoProjects />

// Custom empty state
<EmptyState
  iconName="chat"
  iconCategory="ui"
  title="No conversations yet"
  description="Start a new conversation to begin"
  action={{
    label: "New Chat",
    onClick: handleNewChat,
    icon: "add"
  }}
/>
```

### Loading States

Comprehensive loading components:

```tsx
import { LoadingSpinner, PageLoading, SkeletonComponents } from "@/components/ui/loading-spinner";

// Basic spinner
<LoadingSpinner size="md" variant="primary" />

// Page loading
<PageLoading 
  title="Loading papers..."
  description="Please wait while we fetch your research papers"
/>

// Skeleton loading
<SkeletonComponents.Card />
<SkeletonComponents.ListItem />
<SkeletonComponents.Table rows={5} />
```

## 🎨 Component Patterns

### Feature Cards

Reusable feature cards for showcasing functionality:

```tsx
import { FeatureCard, FeatureGrid } from "@/components/home/feature-card";

// Single feature card
<FeatureCard feature={featureConfig} />

// Grid of features
<FeatureGrid features={features} columns={3} />
```

### Navigation

Consistent navigation patterns:

```tsx
import { Navbar } from "@/components/navigation/navbar";

<Navbar
  currentProject={project}
  showProjectSelector={true}
  userAvatars={userAvatars}
  notifications={notifications}
  onNotificationClick={handleNotificationClick}
/>
```

## 📱 Responsive Design

All components are built with responsive design in mind:

- **Mobile-first**: Components start with mobile layouts
- **Breakpoints**: Uses Tailwind's responsive breakpoints
- **Flexible layouts**: Sidebars collapse on smaller screens
- **Touch-friendly**: Proper touch targets for mobile devices

## ♿ Accessibility

- **Keyboard navigation**: All interactive elements are keyboard accessible
- **Screen readers**: Proper ARIA labels and semantic HTML
- **Color contrast**: Meets WCAG AA standards
- **Focus management**: Clear focus indicators

## 🚀 Performance

- **Tree-shaking**: Only import what you need
- **Lazy loading**: Components load when needed
- **Optimized icons**: Icon system prevents unused imports
- **CSS-in-JS**: Minimal runtime overhead

## 🛠️ Development Guidelines

### Adding New Components

1. **Create the component** in `components/ui/`
2. **Add TypeScript types** for props
3. **Use design system tokens** for colors, spacing, etc.
4. **Add variants** using `class-variance-authority`
5. **Document the component** in this file

### Icon Guidelines

1. **Use Phosphor Icons** exclusively
2. **Categorize icons** properly (navigation, actions, ui, content)
3. **Add to icon system** in `lib/design-system.ts`
4. **Use consistent sizes** (16, 20, 24, 32, 48)

### Styling Guidelines

1. **Use Tailwind classes** for styling
2. **Leverage design tokens** from `lib/design-system.ts`
3. **Follow spacing scale** (xs, sm, md, lg, xl)
4. **Use semantic color names** (primary, secondary, muted, etc.)

## 📚 Usage Examples

### Creating a New Page

```tsx
import { PageLayout } from "@/components/layout/page-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ActionIcon } from "@/components/ui/icon";

export default function MyPage() {
  return (
    <PageLayout
      currentProject={project}
      showProjectSelector={true}
      userAvatars={userAvatars}
      notifications={notifications}
    >
      <div className="p-6">
        <Card>
          <CardHeader>
            <CardTitle>My Page</CardTitle>
          </CardHeader>
          <CardContent>
            <Button leftIcon={<ActionIcon variant="add" />}>
              Add Item
            </Button>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}
```

### Creating a Sidebar

```tsx
import { SidebarLayout } from "@/components/layout/page-layout";
import { Sidebar } from "@/components/ui/sidebar";

export default function MyPage() {
  const sections = [
    {
      id: "main",
      title: "Main Navigation",
      items: [
        { id: "home", label: "Home", href: "/home" },
        { id: "papers", label: "Papers", href: "/papers" },
      ],
    },
  ];

  return (
    <SidebarLayout
      sidebar={<Sidebar sections={sections} />}
      sidebarCollapsed={collapsed}
      onSidebarToggle={toggleSidebar}
    >
      {/* Main content */}
    </SidebarLayout>
  );
}
```

## 🔧 Configuration

The design system is configured in `lib/design-system.ts`:

- **Colors**: Semantic color definitions
- **Typography**: Font families, sizes, weights
- **Spacing**: Consistent spacing scale
- **Icons**: Centralized icon definitions
- **Layout**: Layout constants and breakpoints

## 📖 Further Reading

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Phosphor Icons](https://phosphoricons.com/)
- [Radix UI](https://www.radix-ui.com/)
- [Class Variance Authority](https://cva.style/docs)

---

This design system ensures consistency, maintainability, and scalability across the ResXiv platform. All components are built with modern React patterns and TypeScript for type safety. 