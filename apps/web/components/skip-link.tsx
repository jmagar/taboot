'use client';

import { cn } from '@taboot/ui/lib/utils';

interface SkipLinkProps {
  targetId?: string;
  className?: string;
  children?: React.ReactNode;
}

/**
 * Skip link component for keyboard navigation accessibility.
 * Allows keyboard users to skip directly to main content.
 *
 * Should be the first focusable element on the page.
 * Visually hidden by default, becomes visible when focused.
 */
export function SkipLink({
  targetId = 'main-content',
  className,
  children = 'Skip to main content',
}: SkipLinkProps) {
  return (
    <a
      href={`#${targetId}`}
      aria-label="Skip to main content"
      className={cn(
        // Screen reader only by default
        'sr-only',
        // Visible and styled when focused
        'focus:not-sr-only',
        'focus:absolute focus:top-4 focus:left-4 focus:z-50',
        'focus:px-4 focus:py-2',
        'focus:bg-primary focus:text-primary-foreground',
        'focus:rounded-md focus:shadow-lg',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        className,
      )}
    >
      {children}
    </a>
  );
}
