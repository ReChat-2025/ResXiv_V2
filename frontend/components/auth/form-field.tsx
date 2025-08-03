import React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FormFieldConfig } from "@/lib/auth-config";

interface FormFieldProps {
  field: FormFieldConfig;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  error?: string;
}

export function FormField({ field, value, onChange, disabled, error }: FormFieldProps) {
  return (
    <div 
      className="space-y-2"
      style={field.gridColumn ? { gridColumn: field.gridColumn } : undefined}
    >
      <Label htmlFor={field.id}>
        {field.label}
        {field.required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <Input
        id={field.id}
        name={field.name}
        type={field.type}
        required={field.required}
        value={value}
        onChange={onChange}
        placeholder={field.placeholder}
        disabled={disabled}
        className={error ? "border-destructive" : undefined}
      />
      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
      {field.helpText && !error && (
        <p className="text-xs text-muted-foreground">{field.helpText}</p>
      )}
    </div>
  );
} 