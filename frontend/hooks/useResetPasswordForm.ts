"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api/auth-api";
import { authConfig, getValidationMessage } from "@/lib/auth-config";

interface FormData {
  newPassword: string;
  confirmNewPassword: string;
}

interface FormErrors {
  newPassword?: string;
  confirmNewPassword?: string;
  general?: string;
}

export function useResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resetToken = searchParams.get("token");

  const [formData, setFormData] = useState<FormData>({
    newPassword: "",
    confirmNewPassword: "",
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);

  useEffect(() => {
    if (!resetToken) {
      setTokenValid(false);
      setErrors({ general: "Invalid or missing reset token" });
    } else {
      setTokenValid(true);
    }
  }, [resetToken]);

  const handleFieldChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.newPassword) {
      newErrors.newPassword = getValidationMessage("required");
    } else if (formData.newPassword.length < 8) {
      newErrors.newPassword = getValidationMessage("minLength", 8);
    } else {
      const passwordRegex =
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&].{7,}$/;
      if (!passwordRegex.test(formData.newPassword)) {
        newErrors.newPassword =
          "Password must contain uppercase, lowercase, number and special character";
      }
    }

    if (!formData.confirmNewPassword) {
      newErrors.confirmNewPassword = getValidationMessage("required");
    } else if (formData.newPassword !== formData.confirmNewPassword) {
      newErrors.confirmNewPassword = getValidationMessage("passwordMismatch");
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm() || !resetToken) return;

    setIsLoading(true);
    setErrors({});
    try {
      await authApi.resetPassword(
        resetToken,
        formData.newPassword,
        formData.confirmNewPassword
      );
      setIsSuccess(true);
    } catch (error: any) {
      console.error("Reset password error:", error);
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
    isSuccess,
    tokenValid,
    handleFieldChange,
    handleSubmit,
    router,
  };
}
