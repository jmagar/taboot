'use client';

import { AppSidebar } from '@/components/app-sidebar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SidebarProvider } from '@taboot/ui/components/sidebar';
import { TooltipProvider } from '@taboot/ui/components/tooltip';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import * as React from 'react';
import { Toaster } from 'sonner';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(() => new QueryClient());

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
            <Toaster richColors />
            {children}
          </TooltipProvider>
        </SidebarProvider>
      </QueryClientProvider>
    </NextThemesProvider>
  );
}
