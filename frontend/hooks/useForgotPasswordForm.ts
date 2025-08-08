// hooks/useForgotPasswordForm.ts
"use client";

import { useState } from "react";
import { authApi } from "@/lib/api/auth-api";
import { getValidationMessage } from "@/lib/auth-config";

interface FormData {
  email: string;
}

interface FormErrors {
  email?: string;
  general?: string;
}

export function useForgotPasswordForm() {
  const [formData, setFormData] = useState<FormData>({ email: "" });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleFieldChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    
    // Clear field error when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};
    
    if (!formData.email.trim()) {
      newErrors.email = getValidationMessage("required");
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = getValidationMessage("email");
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    
    setIsLoading(true);
    setErrors({});
    
    try {
      await authApi.forgotPassword(formData.email);
      setIsSuccess(true);
    } catch (error: any) {
      console.error('Forgot password error:', error);
      setErrors({ 
        general: error.message || getValidationMessage("genericError") 
      });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    formData,
    errors,
    isLoading,
    isSuccess,
    handleFieldChange,
    handleSubmit,
    setIsSuccess,
  };
}
