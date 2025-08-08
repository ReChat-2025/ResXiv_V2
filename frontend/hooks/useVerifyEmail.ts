// hooks/useVerifyEmail.ts
"use client";
import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { authApi } from "@/lib/api/auth-api";

export function useVerifyEmail() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [loading, setLoading] = useState(true);
  const [valid, setValid] = useState<boolean | null>(null);

  useEffect(() => {
    if (!token) {
      setValid(false);
      setLoading(false);
      return;
    }
    // Simulate delay for UX
    setTimeout(async () => {
      try {
        const res = await authApi.verifyEmail(token);
        setValid(res.success);
      } catch {
        setValid(false);
      } finally {
        setLoading(false);
      }
    }, 500);
  }, [token]);

  return { loading, valid, token, router };
}
