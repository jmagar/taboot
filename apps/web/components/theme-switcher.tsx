'use client';

import useMounted from '@/hooks/useMounted';
import { Button } from '@taboot/ui/components/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@taboot/ui/components/dropdown-menu';
import { useSidebar } from '@taboot/ui/components/sidebar';
import { LaptopIcon, MoonIcon, SunIcon } from 'lucide-react';
import { useTheme } from 'next-themes';

const THEMES = [
  { name: 'light', label: 'Light', icon: SunIcon },
  { name: 'dark', label: 'Dark', icon: MoonIcon },
  { name: 'system', label: 'System', icon: LaptopIcon },
] as const;

export default function ThemeSwitcher() {
  const mounted = useMounted();
  const { theme, setTheme } = useTheme();
  const { state } = useSidebar();

  const isSidebarExpanded = state === 'expanded';
  if (!mounted) return null;

  const currentIcon =
    theme === 'light' ? (
      <SunIcon className="h-4 w-4" />
    ) : theme === 'dark' ? (
      <MoonIcon className="h-4 w-4" />
    ) : (
      <LaptopIcon className="h-4 w-4" />
    );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild className={isSidebarExpanded ? '' : 'self-center'}>
        <Button
          variant={'ghost'}
          size={isSidebarExpanded ? 'sm' : 'icon'}
          aria-label="Select theme"
          className="border"
        >
          {currentIcon} {isSidebarExpanded ? <span className="capitalize">{theme}</span> : null}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuRadioGroup value={theme} onValueChange={setTheme}>
          {THEMES.map((opt) => (
            <DropdownMenuRadioItem key={opt.name} value={opt.name}>
              <div className="flex items-center">
                <opt.icon className="mr-2 h-4 w-4" />
                <span>{opt.label}</span>
              </div>
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
