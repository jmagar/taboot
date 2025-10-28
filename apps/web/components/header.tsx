'use client';

import Logo from '@/components/logo';
import { MobileNav } from '@/components/mobile-nav';
import { SidebarTrigger, useSidebar } from '@taboot/ui/components/sidebar';
import { cn } from '@taboot/ui/lib/utils';
import Link from 'next/link';

function Header() {
  const { isMobile } = useSidebar();
  return (
    <header
      className={cn(
        'bg-background h-12 w-screen items-center justify-between px-4 py-2',
        isMobile ? 'flex' : 'hidden',
      )}
    >
      <SidebarTrigger aria-label="Toggle navigation menu" />
      <Link href="/" aria-label="Go to home page">
        <Logo variant="header" />
      </Link>
      <div className="flex items-center gap-2">
        <MobileNav />
      </div>
    </header>
  );
}

export default Header;
