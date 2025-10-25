import { Geist, Geist_Mono } from 'next/font/google';

import Header from '@/components/header';
import { PrefetchData } from '@/components/prefetch-data';
import { Providers } from '@/components/providers';
import { SkipLink } from '@/components/skip-link';
import { ViewportDebug } from '@/components/viewport-debug';
import { siteConfig } from '@/config/site';
import { viewportConfig } from '@/config/viewport';
import '@taboot/ui/globals.css';
import { Analytics } from '@vercel/analytics/react';
import { Metadata, Viewport } from 'next';

export const metadata: Metadata = siteConfig;

export const viewport: Viewport = viewportConfig;

const fontSans = Geist({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const fontMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${fontSans.variable} ${fontMono.variable} font-sans antialiased`}>
        <SkipLink />
        <Providers>
          <PrefetchData>
            <main id="main-content" className="flex h-screen w-screen flex-col">
              <Header />
              {children}
            </main>
            <ViewportDebug />
          </PrefetchData>
        </Providers>
        <Analytics />
      </body>
    </html>
  );
}
