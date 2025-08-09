// components/auth/VerifyEmailContent.tsx
"use client";
import { useVerifyEmail } from "@/hooks/useVerifyEmail";
import { Loader } from "@/components/ui/loader";
import { ErrorMessage } from "@/components/ui/error-message";
import VerifyEmailForm from "./VerifyEmailForm";

export function VerifyEmailContent() {
  const { loading, valid, token } = useVerifyEmail();

  if (loading) return <Loader message="Verifying your email..." />;

  if (!valid) {
    return <ErrorMessage message="Invalid or expired link" />;
  }

  return <VerifyEmailForm token={token!} />;
}
