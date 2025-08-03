import { FormFieldConfig, ValidationMessages, getValidationMessage } from "./auth-config";

export interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

export interface FormValidatorConfig {
  fields: FormFieldConfig[];
  customValidations?: Record<string, (value: string, formData: Record<string, string>) => string | null>;
}

export class FormValidator {
  private fields: FormFieldConfig[];
  private customValidations: Record<string, (value: string, formData: Record<string, string>) => string | null>;

  constructor(config: FormValidatorConfig) {
    this.fields = config.fields;
    this.customValidations = config.customValidations || {};
  }

  validate(formData: Record<string, string>): ValidationResult {
    const errors: Record<string, string> = {};

    // Validate each field
    this.fields.forEach(field => {
      const value = formData[field.name] || "";
      const error = this.validateField(field, value, formData);
      if (error) {
        errors[field.name] = error;
      }
    });

    // Run custom validations
    Object.entries(this.customValidations).forEach(([fieldName, validator]) => {
      const value = formData[fieldName] || "";
      const error = validator(value, formData);
      if (error) {
        errors[fieldName] = error;
      }
    });

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  }

  private validateField(field: FormFieldConfig, value: string, formData: Record<string, string>): string | null {
    // Required validation
    if (field.required && !value.trim()) {
      return getValidationMessage('required');
    }

    // Skip other validations if field is empty and not required
    if (!value.trim()) {
      return null;
    }

    // Email validation
    if (field.type === 'email') {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(value)) {
        return getValidationMessage('email');
      }
    }

    // Min length validation
    if (field.validation?.minLength && value.length < field.validation.minLength) {
      return getValidationMessage('minLength', field.validation.minLength);
    }

    // Pattern validation
    if (field.validation?.pattern) {
      const regex = new RegExp(field.validation.pattern);
      if (!regex.test(value)) {
        return field.validation.customMessage || getValidationMessage('genericError');
      }
    }

    return null;
  }
}

// Common validation functions
export const commonValidations = {
  passwordMatch: (confirmPassword: string, formData: Record<string, string>) => {
    if (confirmPassword && formData.password && confirmPassword !== formData.password) {
      return getValidationMessage('passwordMismatch');
    }
    return null;
  },

  termsAcceptance: (value: string) => {
    if (value !== 'true') {
      return getValidationMessage('termsRequired');
    }
    return null;
  }
};

// Hook for form validation
export function useFormValidation(config: FormValidatorConfig) {
  const validator = new FormValidator(config);

  const validateForm = (formData: Record<string, string>) => {
    return validator.validate(formData);
  };

  const validateField = (fieldName: string, value: string, formData: Record<string, string>) => {
    const field = config.fields.find(f => f.name === fieldName);
    if (!field) return null;

    const fieldErrors = validator.validate({ ...formData, [fieldName]: value }).errors;
    return fieldErrors[fieldName] || null;
  };

  return {
    validateForm,
    validateField
  };
} 