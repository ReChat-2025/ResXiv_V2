import { Suspense } from "react";
import { ResetPasswordForm } from "@/components/forms/ResetPasswordForm";
import { AuthLayout } from "@/components/auth/auth-layout";

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <AuthLayout title="Loading..." cardTitle="Loading..." links={[]}>
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </AuthLayout>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
