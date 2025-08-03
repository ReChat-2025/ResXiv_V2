# SearchInput Component Guide

## Overview

The `SearchInput` component is a unified, reusable search component used consistently across all pages in the ResXiv application. It provides a standardized search experience with proper styling, configuration, and functionality.

## Component Location

```
components/ui/SearchInput.tsx
```

## Usage

### Basic Import

```typescript
import SearchInput from "@/components/ui/SearchInput";
// or
import { SearchInput } from "@/components";
```

### Basic Implementation

```typescript
import SearchInput from "@/components/ui/SearchInput";

function MyComponent() {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <SearchInput
      placeholder="Search items..."
      value={searchQuery}
      onChange={setSearchQuery}
    />
  );
}
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `placeholder` | `string` | `"Search"` | Placeholder text for the input |
| `value` | `string` | `undefined` | Controlled value (optional) |
| `onChange` | `(value: string) => void` | `undefined` | Callback when input changes |
| `onSubmit` | `(value: string) => void` | `undefined` | Callback when Enter is pressed |
| `onKeyPress` | `(e: KeyboardEvent) => void` | `undefined` | Custom key press handler |
| `disabled` | `boolean` | `false` | Whether the input is disabled |
| `className` | `string` | `""` | Additional CSS classes |
| `style` | `React.CSSProperties` | `{}` | Custom inline styles |
| `iconSize` | `number` | `24` | Size of the search icon |
| `iconWeight` | `"thin" \| "light" \| "regular" \| "bold" \| "fill" \| "duotone"` | `"light"` | Weight of the search icon |
| `variant` | `"default" \| "transparent"` | `"default"` | Visual variant of the component |

## Variants

### Default Variant
- Has a visible border
- Standard padding and styling
- Suitable for most use cases

```typescript
<SearchInput variant="default" placeholder="Search papers..." />
```

### Transparent Variant
- No visible border
- Minimal styling
- Good for integration within other components

```typescript
<SearchInput variant="transparent" placeholder="Search..." />
```

## Configuration

The component uses the `searchInputConfig` from `lib/config/ui-config.ts` for styling consistency:

```typescript
// Automatic configuration based on variant
const config = variant === "transparent" 
  ? searchInputConfig.transparent 
  : searchInputConfig.default;
```

## Current Implementation Across Pages

### ✅ Standardized Pages

1. **ChatSidebar** (`components/chat/ChatSidebar.tsx`)
   ```typescript
   <SearchInput
     placeholder="Search conversations..."
     value={searchQuery}
     onChange={handleSearchChange}
     variant="default"
   />
   ```

2. **Papers Sidebar** (`components/papers/PapersSidebar.tsx`)
   ```typescript
   // Uses a search button style, but imports SearchInput
   import SearchInput from "@/components/ui/SearchInput";
   ```

3. **Journals Page** (`components/journals/JournalsArea.tsx`)
   ```typescript
   <SearchInput
     placeholder="Search journals..."
     value={searchQuery}
     onChange={handleSearchChange}
     variant="default"
   />
   ```

4. **Projects Page** (`app/projects/page.tsx`)
   ```typescript
   <SearchInput
     placeholder={config.actions.search.placeholder}
     value={searchQuery}
     onChange={setSearchQuery}
   />
   ```

### Pages Without Search (Currently)

- **Tasks Page** - Could be added if needed
- **Settings Page** - No search functionality required
- **Collaborate Page** - Uses chat input instead

## Design Guidelines

### Visual Consistency
- Always use Phosphor icons with 24px size and "light" weight
- Consistent padding, border radius, and spacing
- Manrope font family throughout
- Proper focus and hover states

### Color Scheme
- Icon color: `#737373` (muted gray)
- Text color: `#0D0D0D` (primary)
- Placeholder color: `#737373` (muted gray)
- Border color: `#E7E7E7` (light gray)
- Focus border: `#737373` (darker gray)
- Hover border: `#D9D9D9` (medium gray)

### Responsive Behavior
- Full width by default (`width: 100%`)
- Proper text overflow handling
- Flexible with container constraints

## Advanced Usage

### With Form Submission

```typescript
const handleSubmit = (query: string) => {
  // Perform search operation
  console.log("Searching for:", query);
};

<SearchInput
  placeholder="Search..."
  onSubmit={handleSubmit}
  onKeyPress={(e) => {
    if (e.key === 'Escape') {
      // Clear search or close
    }
  }}
/>
```

### With Custom Styling

```typescript
<SearchInput
  placeholder="Custom search..."
  className="my-custom-class"
  style={{ 
    maxWidth: '300px',
    margin: '0 auto'
  }}
  iconSize={20}
  iconWeight="bold"
/>
```

### Controlled vs Uncontrolled

```typescript
// Controlled (recommended)
const [query, setQuery] = useState("");
<SearchInput value={query} onChange={setQuery} />

// Uncontrolled
<SearchInput onChange={(value) => console.log(value)} />
```

## Migration Guide

### From Custom Implementation

**Before:**
```typescript
<div className="relative">
  <Search className="absolute left-3 top-1/2 -translate-y-1/2" />
  <Input
    placeholder="Search..."
    value={searchQuery}
    onChange={(e) => setSearchQuery(e.target.value)}
    className="pl-10"
  />
</div>
```

**After:**
```typescript
<SearchInput
  placeholder="Search..."
  value={searchQuery}
  onChange={setSearchQuery}
/>
```

### Migration Steps

1. Import SearchInput component
2. Replace custom search implementation
3. Update onChange handler (no need for `e.target.value`)
4. Remove custom styling classes
5. Test functionality

## Best Practices

### ✅ Do's
- Use consistent placeholder text patterns
- Implement proper state management
- Use the onChange callback correctly
- Leverage the configuration system
- Test keyboard interactions (Enter, Escape)

### ❌ Don'ts
- Don't create custom search implementations
- Don't hardcode colors or dimensions
- Don't forget to handle empty states
- Don't ignore accessibility requirements
- Don't mix different search component styles

## Accessibility

The SearchInput component includes:
- Proper semantic HTML structure
- Keyboard navigation support
- Focus management
- ARIA attributes (automatically handled)
- Screen reader friendly

## Performance

- Lightweight component with minimal re-renders
- Efficient state management
- Optimized icon rendering
- Proper cleanup of event listeners

## Future Enhancements

Potential improvements for the SearchInput component:
- Autocomplete/suggestions support
- Debounced search functionality
- Search history
- Advanced filtering options
- Voice search integration

## Troubleshooting

### Common Issues

1. **Styling not applied correctly**
   - Ensure `ui-config.ts` is properly configured
   - Check if custom styles are overriding defaults

2. **onChange not working**
   - Verify the onChange prop receives a string, not an event
   - Check if the component is controlled properly

3. **Icon not displaying**
   - Ensure Phosphor icons are installed
   - Check if the iconSize and iconWeight props are valid

### Debug Tips

```typescript
// Add debugging to onChange
<SearchInput
  onChange={(value) => {
    console.log("Search value:", value);
    setSearchQuery(value);
  }}
/>
```

---

**Last Updated:** 2024
**Component Version:** 1.0.0 