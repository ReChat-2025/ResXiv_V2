# UI Components Usage Guide

This guide explains how to use the reusable UI components throughout the platform for consistency.

## PrimaryButton Component

A reusable button component based on the "New Chat" button style with perfect middle alignment.

### Basic Usage

```tsx
import { PrimaryButton } from '@/components';
import { ChatCircle, Download, Settings } from '@phosphor-icons/react';

// Primary button (default)
<PrimaryButton 
  onClick={() => console.log('clicked')}
  icon={ChatCircle}
>
  New Chat
</PrimaryButton>

// Secondary button
<PrimaryButton 
  onClick={() => console.log('clicked')}
  icon={Download}
  variant="secondary"
>
  Download
</PrimaryButton>

// Without icon
<PrimaryButton onClick={() => console.log('clicked')}>
  Submit
</PrimaryButton>

// Disabled state
<PrimaryButton 
  onClick={() => console.log('clicked')}
  icon={Settings}
  disabled={true}
>
  Settings
</PrimaryButton>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `React.ReactNode` | - | Button text content |
| `onClick` | `() => void` | - | Click handler |
| `icon` | `Icon` | - | Phosphor icon component |
| `iconColor` | `string` | `"#FFFFFF"` | Icon color |
| `iconSize` | `number` | `24` | Icon size |
| `iconWeight` | `IconWeight` | `"regular"` | Icon weight |
| `disabled` | `boolean` | `false` | Disabled state |
| `variant` | `"primary" \| "secondary"` | `"primary"` | Button variant |
| `className` | `string` | `""` | Additional CSS classes |
| `style` | `React.CSSProperties` | `{}` | Additional styles |

## SearchInput Component

A reusable search input component with consistent styling and behavior.

### Basic Usage

```tsx
import { SearchInput } from '@/components';

// Controlled input
const [searchValue, setSearchValue] = useState("");

<SearchInput
  placeholder="Search conversations..."
  value={searchValue}
  onChange={(value) => setSearchValue(value)}
  onSubmit={(value) => console.log('Search:', value)}
/>

// Uncontrolled input
<SearchInput
  placeholder="Search papers..."
  onSubmit={(value) => console.log('Search:', value)}
/>

// Transparent variant
<SearchInput
  placeholder="Search..."
  variant="transparent"
  onSubmit={(value) => console.log('Search:', value)}
/>

// Custom icon size
<SearchInput
  placeholder="Quick search..."
  iconSize={20}
  iconWeight="bold"
/>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `placeholder` | `string` | `"Search"` | Input placeholder text |
| `value` | `string` | - | Controlled input value |
| `onChange` | `(value: string) => void` | - | Value change handler |
| `onSubmit` | `(value: string) => void` | - | Enter key / submit handler |
| `onKeyPress` | `(e: KeyboardEvent) => void` | - | Key press handler |
| `disabled` | `boolean` | `false` | Disabled state |
| `variant` | `"default" \| "transparent"` | `"default"` | Input variant |
| `iconSize` | `number` | `24` | Search icon size |
| `iconWeight` | `IconWeight` | `"regular"` | Search icon weight |
| `className` | `string` | `""` | Additional CSS classes |
| `style` | `React.CSSProperties` | `{}` | Additional styles |

## Design System

Both components follow the platform's design system:

### Colors
- **Primary**: `#0D0D0D` (dark)
- **Secondary**: `#737373` (gray)
- **Border**: `#E7E7E7` (light gray)
- **Hover**: `#F5F5F5` (very light gray)

### Typography
- **Font**: Manrope
- **Size**: 16px
- **Weight**: 400 (regular)
- **Line Height**: 1.75em

### Spacing
- **Padding**: 12px 8px
- **Gap**: 8px (between icon and text)
- **Border Radius**: 12px

### Icons
- **Library**: Phosphor Icons
- **Size**: 24px (default)
- **Weight**: regular (default)

## Integration Examples

### Replace existing buttons

```tsx
// Before - Custom button
<button 
  className="bg-primary text-white px-4 py-2 rounded-lg"
  onClick={handleClick}
>
  Submit
</button>

// After - PrimaryButton component
<PrimaryButton onClick={handleClick}>
  Submit
</PrimaryButton>
```

### Replace existing search inputs

```tsx
// Before - Custom search
<div className="flex items-center border rounded-lg px-3 py-2">
  <SearchIcon />
  <input 
    type="text" 
    placeholder="Search..." 
    className="flex-1 outline-none"
  />
</div>

// After - SearchInput component
<SearchInput 
  placeholder="Search..."
  onSubmit={handleSearch}
/>
```

## Benefits

1. **Consistency**: Same styling across all pages
2. **Maintainability**: Central component updates affect entire app
3. **Accessibility**: Built-in keyboard support and proper ARIA
4. **Performance**: Optimized hover effects and transitions
5. **Type Safety**: Full TypeScript support
6. **Flexibility**: Configurable props for different use cases

## Migration

To migrate existing buttons and search inputs:

1. Import the components: `import { PrimaryButton, SearchInput } from '@/components';`
2. Replace existing implementations with the new components
3. Update props to match the new API
4. Test functionality and styling
5. Remove old custom implementations

The components are fully backward compatible and can be gradually adopted throughout the platform. 