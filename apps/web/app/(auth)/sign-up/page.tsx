import { AuthForm } from '@/components/auth-form';
import { Skeleton } from '@taboot/ui/components/skeleton';
import { Suspense } from 'react';

export default function SignUpPage() {
  return (
    <Suspense fallback={<SignUpFormSkeleton />}>
      <AuthForm mode="sign-up" />
    </Suspense>
  );
}

function SignUpFormSkeleton() {
  return (
    <div className="flex min-h-svh items-center justify-center p-6 md:p-10">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <Skeleton className="mx-auto h-9 w-48" />
          <Skeleton className="mx-auto mt-2 h-5 w-64" />
        </div>
        <div className="border-border bg-card text-card-foreground rounded-xl border p-6 shadow-sm">
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
          <Skeleton className="mt-6 h-10 w-full" />
        </div>
        <Skeleton className="mx-auto h-4 w-56" />
      </div>
    </div>
  );
}
