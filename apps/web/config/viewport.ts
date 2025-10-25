import { Viewport } from 'next';

export const viewportConfig: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: [
    {
      media: '(prefers-color-scheme: light)',
      color: '#818cf8',
    },
    {
      media: '(prefers-color-scheme: dark)',
      color: '#0f172a',
    },
  ],
  colorScheme: 'light dark',
};
