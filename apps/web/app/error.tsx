'use client';

import { Button } from '@taboot/ui/components/button';
import { logger } from '@/lib/logger';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    logger.error('Root error boundary caught error', {
      message: error.message,
      digest: error.digest,
      stack: error.stack,
    });
  }, [error]);

  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
          <div className="w-full max-w-md space-y-8 text-center">
            <div className="space-y-2">
              <h1 className="text-4xl font-bold tracking-tight">Something went wrong</h1>
              <p className="text-muted-foreground">
                We encountered an unexpected error. Our team has been notified and is working on a
                fix.
              </p>
              {error.digest && (
                <p className="text-xs text-muted-foreground">Error ID: {error.digest}</p>
              )}
            </div>

            <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
              <Button onClick={() => reset()} variant="default" size="lg">
                Try Again
              </Button>
              <Button onClick={() => router.push('/')} variant="outline" size="lg">
                Go Home
              </Button>
            </div>

            {process.env.NODE_ENV === 'development' && (
              <details className="mt-8 rounded-lg border bg-card p-4 text-left">
                <summary className="cursor-pointer font-semibold">Technical Details</summary>
                <pre className="mt-4 overflow-auto text-xs">
                  <code>{error.stack || error.message}</code>
                </pre>
              </details>
            )}
          </div>
        </div>
      </body>
    </html>
  );
}
