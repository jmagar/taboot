import { Skeleton } from '@taboot/ui/components/skeleton';

export default function ForgotPasswordLoading() {
  return (
    <div className="from-background to-muted/20 flex min-h-screen items-center justify-center bg-linear-to-b px-4" aria-busy="true" aria-label="Loading forgot password">
      <div className="w-full max-w-md rounded-lg border p-6 shadow-sm">
        <div className="mb-6 space-y-2 text-center" aria-hidden="true">
          <Skeleton className="mx-auto h-7 w-48" />
          <Skeleton className="mx-auto h-4 w-full max-w-sm" />
        </div>
        <div className="space-y-4" aria-hidden="true">
          <div className="space-y-2">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-3 w-64" />
          </div>
          <Skeleton className="h-10 w-full" />
          <Skeleton className="mx-auto h-4 w-32" />
        </div>
      </div>
    </div>
  );
}
