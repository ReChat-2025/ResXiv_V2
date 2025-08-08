import React from "react";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { ErrorMessage } from "@/components/ui/error-message";
import { FormFieldConfig } from "@/lib/auth-config";

interface FormFieldProps {
  field: FormFieldConfig;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  error?: string;
}

export function FormField({ field, value, onChange, disabled, error }: FormFieldProps) {
  const gridColumnClass = field.gridColumn ? "" : "col-span-2";
  
  return (
    <div 
      className={`space-y-2 ${gridColumnClass}`}
      style={field.gridColumn ? { gridColumn: field.gridColumn } : undefined}
    >
      <Label htmlFor={field.id}>
        {field.label}
        {field.required && <span className="text-destructive ml-1">*</span>}
      </Label>
      {field.type === "password" ? (
        <PasswordInput
          id={field.id}
          name={field.name}
          value={value}
          onChange={onChange}
          placeholder={field.placeholder}
          disabled={disabled}
          className={error ? "border-destructive" : undefined}
          required={field.required}
        />
      ) : (
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
      )}
      {error && (
        <ErrorMessage message={error} className="mt-1" showIcon={false} />
      )}
      {field.helpText && !error && (
        <p className="text-xs text-muted-foreground">{field.helpText}</p>
      )}
    </div>
  );
} 