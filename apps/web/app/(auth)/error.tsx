'use client';

import { Button } from '@taboot/ui/components/button';
import { logger } from '@/lib/logger';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Sanitize error messages to remove PII and sensitive data before logging
 */
function sanitizeErrorMessage(message: string): string {
  return message
    .replace(/[\w.-]+@[\w.-]+\.\w+/g, '[EMAIL]') // Email addresses
    .replace(/token=[\w-]+/gi, 'token=[REDACTED]') // URL tokens
    .replace(/bearer\s+[\w-]+/gi, 'bearer [REDACTED]') // Bearer tokens
    .replace(/[0-9a-f]{32,}/gi, '[SESSION_ID]') // Hex strings (session IDs, hashes)
    .replace(/\b[A-Za-z0-9+/]{40,}={0,2}\b/g, '[TOKEN]'); // Base64 tokens
}

export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    logger.error('Auth error boundary caught error', {
      message: sanitizeErrorMessage(error.message),
      digest: error.digest, // Digest is safe - it's a Next.js error ID
      stack: error.stack ? sanitizeErrorMessage(error.stack) : undefined,
    });
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-8 text-center">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Authentication Error</h1>
          <p className="text-muted-foreground">
            We encountered an error during authentication. Please try again or return to the sign in
            page.
          </p>
          {error.digest && (
            <p className="text-xs text-muted-foreground">Error ID: {error.digest}</p>
          )}
        </div>

        <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
          <Button onClick={() => reset()} variant="default" size="lg">
            Try Again
          </Button>
          <Button onClick={() => router.push('/sign-in')} variant="outline" size="lg">
            Back to Sign In
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
  );
}
