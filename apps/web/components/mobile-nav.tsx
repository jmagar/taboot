'use client';

import { config } from '@/config/site';
import { useAuthUser } from '@/hooks/use-auth-user';
import { Button } from '@taboot/ui/components/button';
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@taboot/ui/components/sheet';
import { LogIn, Menu, UserPlus } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const { isAuthenticated } = useAuthUser();

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-80">
        <SheetHeader>
          <SheetTitle>{config.name}</SheetTitle>
          <SheetDescription>Navigate to different sections</SheetDescription>
        </SheetHeader>
        <nav className="flex flex-col gap-4 py-6">
          {config.nav.map((item) => (
            <SheetClose asChild key={item.href}>
              <Link
                href={item.href}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-base font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
              >
                <item.icon className="h-5 w-5" aria-hidden="true" />
                {item.title}
              </Link>
            </SheetClose>
          ))}
          {!isAuthenticated && (
            <>
              <div className="my-2 border-t" />
              <SheetClose asChild>
                <Button className="w-full justify-start" size="lg" asChild>
                  <Link href="/sign-up">
                    <UserPlus className="h-5 w-5" aria-hidden="true" />
                    Sign up
                  </Link>
                </Button>
              </SheetClose>
              <SheetClose asChild>
                <Button variant="secondary" className="w-full justify-start" size="lg" asChild>
                  <Link href="/sign-in">
                    <LogIn className="h-5 w-5" aria-hidden="true" />
                    Sign in
                  </Link>
                </Button>
              </SheetClose>
            </>
          )}
        </nav>
      </SheetContent>
    </Sheet>
  );
}
