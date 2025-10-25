'use client';

import { AppSidebar } from '@/components/app-sidebar';
import { logger } from '@/lib/logger';
import { initPostHog } from '@/lib/posthog';
import { queryClientConfig } from '@/lib/query-client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SidebarProvider } from '@taboot/ui/components/sidebar';
import { TooltipProvider } from '@taboot/ui/components/tooltip';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import * as React from 'react';
import { Toaster } from 'sonner';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: queryClientConfig,
      }),
  );

  React.useEffect(() => {
    // Initialize PostHog analytics
    initPostHog();

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      logger.error('Unhandled promise rejection', {
        reason: event.reason,
        promise: event.promise,
      });
    };

    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, []);

  // Axe accessibility testing in development
  React.useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      (async () => {
        try {
          const axe = await import('@axe-core/react');
          const ReactDOM = await import('react-dom');
          axe.default(React, ReactDOM, 1000);
        } catch (error) {
          logger.error('Failed to load accessibility tools', { error });
        }
      })();
    }
  }, []);

  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      enableColorScheme
    >
      <QueryClientProvider client={queryClient}>
        <SidebarProvider>
          <TooltipProvider>
            <AppSidebar />
            <Toaster richColors aria-live="polite" aria-atomic="true" />
            {children}
          </TooltipProvider>
        </SidebarProvider>
      </QueryClientProvider>
    </NextThemesProvider>
  );
}
