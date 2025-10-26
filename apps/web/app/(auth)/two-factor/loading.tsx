import { Skeleton } from '@taboot/ui/components/skeleton';

export default function TwoFactorLoading() {
  return (
    <div className="flex min-h-svh items-center justify-center p-6 md:p-10" role="status" aria-live="polite" aria-busy="true" aria-label="Loading two-factor verification">
      <div className="w-full max-w-md">
        <div className="rounded-xl border shadow" aria-hidden="true">
          <div className="flex flex-col space-y-1.5 p-6 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Skeleton className="h-6 w-6 rounded" />
            </div>
            <Skeleton className="mx-auto h-6 w-3/4" />
            <Skeleton className="mx-auto mt-2 h-4 w-full" />
          </div>
          <div className="p-6 pt-0">
            <div className="space-y-6">
              <div className="space-y-3">
                <Skeleton className="mx-auto h-4 w-32" />
                <div className="flex justify-center">
                  <div className="flex gap-2">
                    {Array.from({ length: 6 }, (_, i) => (
                      <Skeleton key={i} className="h-12 w-10 rounded-md" />
                    ))}
                  </div>
                </div>
                <Skeleton className="mx-auto h-3 w-48" />
              </div>
              <Skeleton className="h-10 w-full" />
              <Skeleton className="mx-auto h-4 w-40" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
