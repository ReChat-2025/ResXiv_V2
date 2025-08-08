// components/auth/VerifyEmailContent.tsx
"use client";
import { useVerifyEmail } from "@/hooks/useVerifyEmail";
import { Loader } from "@/components/ui/loader";
import VerifyEmailForm from "./VerifyEmailForm";

export function VerifyEmailContent() {
  const { loading, valid, token } = useVerifyEmail();

  if (loading) return <Loader message="Verifying your email..." />;

  if (!valid) {
    return <p className="text-destructive">Invalid or expired link</p>;
  }

  return <VerifyEmailForm token={token!} />;
}
