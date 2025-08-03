"use client"

import * as React from "react"
import { Search, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Input } from "./input"
import { Button } from "./button"

export interface SearchInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  onSearch?: (value: string) => void
  onClear?: () => void
  showClearButton?: boolean
  containerClassName?: string
}

const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({ 
    className, 
    onSearch, 
    onClear, 
    showClearButton = true,
    containerClassName,
    onChange,
    value,
    ...props 
  }, ref) => {
    const [internalValue, setInternalValue] = React.useState(value || "")
    
    React.useEffect(() => {
      setInternalValue(value || "")
    }, [value])
    
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value
      setInternalValue(newValue)
      onChange?.(e)
    }
    
    const handleSearch = () => {
      onSearch?.(internalValue as string)
    }
    
    const handleClear = () => {
      setInternalValue("")
      onClear?.()
    }
    
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault()
        handleSearch()
      }
    }
    
    const showClear = showClearButton && internalValue && String(internalValue).length > 0
    
    return (
      <div className={cn("relative flex items-center", containerClassName)}>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            ref={ref}
            className={cn("pl-9", showClear && "pr-9", className)}
            value={internalValue}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Search..."
            {...props}
          />
          {showClear && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
              onClick={handleClear}
            >
              <X className="h-4 w-4" />
              <span className="sr-only">Clear search</span>
            </Button>
          )}
        </div>
      </div>
    )
  }
)
SearchInput.displayName = "SearchInput"

export { SearchInput } 