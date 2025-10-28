'use client';

import Logo from '@/components/logo';
import { NavUser } from '@/components/nav-user';
import ThemeSwitcher from '@/components/theme-switcher';
import { config } from '@/config/site';
import { useAuthUser } from '@/hooks/use-auth-user';
import { Button } from '@taboot/ui/components/button';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from '@taboot/ui/components/sidebar';
import { cn } from '@taboot/ui/lib/utils';
import { LogIn, UserPlus } from 'lucide-react';
import Link from 'next/link';
import * as React from 'react';

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { state } = useSidebar();
  const { isAuthenticated } = useAuthUser();
  const isSidebarExpanded = state === 'expanded';

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader className={cn('flex', isSidebarExpanded ? 'flex-row' : 'flex-col')}>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild className="data-[slot=sidebar-menu-button]:p-1!">
              <Link
                href="/"
                className="flex items-center gap-2 self-center font-medium"
                aria-label="Go to home page"
              >
                <Logo variant="sidebar" />
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <SidebarTrigger className="size-11" aria-label="Toggle sidebar" />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {config.nav.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton tooltip={item.title} asChild>
                    <Link href={item.href}>
                      <item.icon aria-hidden="true" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        {isAuthenticated ? (
          <>
            <ThemeSwitcher />
            <NavUser />
          </>
        ) : (
          <div className={cn('flex flex-col gap-2', { 'self-center': !isSidebarExpanded })}>
            <ThemeSwitcher />
            <Button asChild size={isSidebarExpanded ? 'sm' : 'icon'} {...(!isSidebarExpanded && { 'aria-label': 'Sign up' })}>
              <Link
                href="/sign-up"
                className={cn('flex flex-row items-center justify-center', isSidebarExpanded && 'space-x-2')}
              >
                <UserPlus className="h-4 w-4" aria-hidden="true" />
                <span>{isSidebarExpanded ? 'Sign up' : ''}</span>
              </Link>
            </Button>
            <Button
              asChild
              variant="secondary"
              size={isSidebarExpanded ? 'sm' : 'icon'}
              {...(!isSidebarExpanded && { 'aria-label': 'Sign in' })}
            >
              <Link
                href="/sign-in"
                className={cn('flex flex-row items-center justify-center', isSidebarExpanded && 'space-x-2')}
              >
                <LogIn className="h-4 w-4" aria-hidden="true" />
                <span>{isSidebarExpanded ? 'Sign in' : ''}</span>
              </Link>
            </Button>
          </div>
        )}
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
