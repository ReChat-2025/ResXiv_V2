// hooks/useLoginForm.ts

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/lib/services/auth-service";
import { getValidationMessage } from "@/lib/auth-config";

interface FormData {
  email: string;
  password: string;
  rememberMe: boolean;
}

interface FormErrors {
  email?: string;
  password?: string;
  general?: string;
}

export function useLoginForm() {
  const router = useRouter();

  const [formData, setFormData] = useState<FormData>({
    email: "",
    password: "",
    rememberMe: false,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  // Check for query messages (like after registration)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get("message");

    const messageMap: Record<string, string> = {
      "registration-success": "Registration successful! Please log in.",
      "verification-required": "Check your email to verify your account.",
      "password-reset": "Password reset successful!",
      "email-verified": "Email verified successfully!",
    };

    if (message && messageMap[message]) {
      setSuccessMessage(messageMap[message]);
    }
  }, []);

  const handleFieldChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({
        ...prev,
        [name]: undefined,
      }));
    }
  };

  const handleRememberMeChange = (checked: boolean) => {
    setFormData((prev) => ({
      ...prev,
      rememberMe: checked,
    }));
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.email.trim()) {
      newErrors.email = getValidationMessage("required");
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = getValidationMessage("email");
    }

    if (!formData.password) {
      newErrors.password = getValidationMessage("required");
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
      await authService.login(
        formData.email,
        formData.password,
        formData.rememberMe
      );

      const redirectTo =
        new URLSearchParams(window.location.search).get("redirect") ||
        "/projects";
      router.push(redirectTo);
    } catch (error: any) {
      console.error("Login error:", error);
      setErrors({
        general: error.message || getValidationMessage("genericError"),
      });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    formData,
    handleFieldChange,
    handleRememberMeChange,
    handleSubmit,
    isLoading,
    errors,
    successMessage,
    setErrors,
  };
}
