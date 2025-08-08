// app/verify-email/page.tsx
import { Suspense } from "react";
import { VerifyEmailContent } from "@/components/auth/VerifyEmailContent";
import { Loader } from "@/components/ui/loader";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<Loader message="Loading..." />}>
      <VerifyEmailContent />
    </Suspense>
  );
}
