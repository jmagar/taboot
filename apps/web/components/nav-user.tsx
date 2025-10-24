import { useRequiredAuthUser } from '@/hooks/use-auth-user';
import type { ComponentType, SVGProps } from 'react';
import { signOut } from '@taboot/auth/client';
import { Avatar, AvatarFallback, AvatarImage } from '@taboot/ui/components/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@taboot/ui/components/dropdown-menu';
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@taboot/ui/components/sidebar';
import { ChevronsUpDown, LogOut, Settings, Shield, User2 } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

type DropdownItem = {
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  href?: string;
  onClick?: () => void;
};

export function NavUser() {
  const { isMobile } = useSidebar();
  const { user, isLoading, refetch } = useRequiredAuthUser();
  const router = useRouter();

  if (isLoading) return null;

  const dropdownItems: DropdownItem[][] = [
    [
      {
        label: 'Profile',
        href: `/profile`,
        icon: User2,
      },
    ],
    [
      {
        label: 'General',
        href: `/settings/general`,
        icon: Settings,
      },
      {
        label: 'Security',
        href: `/settings/security`,
        icon: Shield,
      },
    ],
    [
      {
        label: 'Log out',
        onClick: async () => {
          await signOut({
            fetchOptions: {
              onSuccess: () => {
                refetch();
                router.push('/');
              },
            },
          });
        },
        icon: LogOut,
      },
    ],
  ];

  const displayName = user.name || user.email?.split('@')[0] || 'User';
  const avatarFallback = displayName.charAt(0).toUpperCase();

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <Avatar className="h-8 w-8 rounded-lg">
                <AvatarImage src={user.image ?? ''} alt={displayName} />
                <AvatarFallback className="rounded-lg">{avatarFallback}</AvatarFallback>
              </Avatar>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">{displayName}</span>
                <span className="truncate text-xs">{user.email}</span>
              </div>
              <ChevronsUpDown className="ml-auto size-4" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
            side={isMobile ? 'bottom' : 'right'}
            align="end"
            sideOffset={4}
          >
            <DropdownMenuLabel className="p-0 font-normal">
              <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                <Avatar className="h-8 w-8 rounded-lg">
                  <AvatarImage src={user.image ?? ''} alt={displayName} />
                  <AvatarFallback className="rounded-lg">{avatarFallback}</AvatarFallback>
                </Avatar>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">{displayName}</span>
                  <span className="truncate text-xs">{user.email}</span>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {renderDropdownItems(dropdownItems)}
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}

function renderDropdownItems(dropdownItems: DropdownItem[][]) {
  return dropdownItems.map((group, groupIdx) => {
    const groupKey = `${groupIdx}-${group.map((item) => item.label).join('-')}`;
    return (
      <div key={groupKey}>
        <DropdownMenuGroup>
          {group.map((item) =>
            item.href ? (
              <DropdownMenuItem asChild key={item.label}>
                <Link href={item.href}>
                  <div className="flex items-center gap-2">
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </div>
                </Link>
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem key={item.label} onClick={item.onClick}>
                <item.icon className="h-4 w-4" />
                {item.label}
              </DropdownMenuItem>
            ),
          )}
        </DropdownMenuGroup>
        {groupIdx < dropdownItems.length - 1 && <DropdownMenuSeparator />}
      </div>
    );
  });
}
