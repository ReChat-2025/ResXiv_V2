"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/lib/services/auth-service";
import { getValidationMessage, authConfig } from "@/lib/auth-config";

interface FormData {
  email: string;
  password: string;
  confirmPassword: string;
  rememberMe: boolean;
  firstName?: string;
  lastName?: string;
  acceptedTerms?: boolean;
}

interface FormErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
  general?: string;
}

export function useSignupForm() {
  const router = useRouter();
  const config = authConfig.signup;

  const [formData, setFormData] = useState<FormData>({
    email: "",
    password: "",
    confirmPassword: "",
    rememberMe: false,
    firstName: "",
    lastName: "",
    acceptedTerms: false,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);

  // handle field changes
  const handleFieldChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  // handle remember me
  const handleRememberMeChange = (checked: boolean) => {
    setFormData((prev) => ({ ...prev, rememberMe: checked }));
  };

  // validate form
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = getValidationMessage("required");
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = getValidationMessage("email");
    }

    // Password validation - using same validation as reset password for consistency
    if (!formData.password) {
      newErrors.password = getValidationMessage("required");
    } else if (formData.password.length < 8) {
      newErrors.password = getValidationMessage("minLength", 8);
    } else {
      // Check password complexity (same as reset password)
      const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&].{7,}$/;
      if (!passwordRegex.test(formData.password)) {
        newErrors.password = 'Password must contain uppercase, lowercase, number and special character';
      }
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = getValidationMessage("required");
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = getValidationMessage("passwordMismatch");
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // handle submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsLoading(true);
    setErrors({});

    try {
      await authService.register(
        `${formData.firstName || ''} ${formData.lastName || ''}`.trim() || 'User',
        formData.email,
        formData.password,
        formData.confirmPassword,
        formData.acceptedTerms || false
      );
      router.push("/login?message=verification-required");
    } catch (error: any) {
      setErrors({
        general: error.message || getValidationMessage("genericError"),
      });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    formData,
    errors,
    isLoading,
    config,
    handleFieldChange,
    handleRememberMeChange,
    handleSubmit,
    setErrors,
    setIsLoading,
  };
}
