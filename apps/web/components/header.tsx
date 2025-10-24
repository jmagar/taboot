'use client';

import Logo from '@/components/logo';
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
      <SidebarTrigger />
      <Link href="/">
        <Logo variant="header" />
      </Link>
      <div className="flex items-center gap-2"></div>
    </header>
  );
}

export default Header;
