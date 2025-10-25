'use client';

import { AppSidebar } from '@/components/app-sidebar';
import { logger } from '@/lib/logger';
import { initPostHog } from '@/lib/posthog';
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
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes - data is considered fresh for this duration
            gcTime: 10 * 60 * 1000, // 10 minutes - cache garbage collection time (formerly cacheTime)
            refetchOnWindowFocus: false, // Don't refetch when window regains focus
            refetchOnReconnect: true, // Do refetch when reconnecting to network
            retry: 1, // Retry failed queries once before giving up
          },
        },
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
      import('@axe-core/react')
        .then((axe) => {
          import('react-dom')
            .then((ReactDOM) => {
              axe.default(React, ReactDOM, 1000);
            })
            .catch((error) => {
              logger.error('Failed to load ReactDOM for axe', { error });
            });
        })
        .catch((error) => {
          logger.error('Failed to load @axe-core/react', { error });
        });
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
