'use client';

import { Button } from '@taboot/ui/components/button';
import { logger } from '@/lib/logger';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ProtectedRouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    logger.error('Protected route error boundary caught error', {
      message: error.message,
      digest: error.digest,
      stack: error.stack,
    });
  }, [error]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6 text-center">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold tracking-tight">An Error Occurred</h2>
          <p className="text-sm text-muted-foreground">
            Something went wrong while loading this page. Please try again.
          </p>
          {error.digest && (
            <p className="text-xs text-muted-foreground">Error ID: {error.digest}</p>
          )}
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Button onClick={() => reset()} variant="default">
            Try Again
          </Button>
          <Button onClick={() => router.push('/dashboard')} variant="outline">
            Go to Dashboard
          </Button>
        </div>

        {process.env.NODE_ENV === 'development' && (
          <details className="mt-6 rounded-lg border bg-card p-4 text-left">
            <summary className="cursor-pointer text-sm font-semibold">Technical Details</summary>
            <pre className="mt-3 overflow-auto text-xs">
              <code>{error.stack || error.message}</code>
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}
