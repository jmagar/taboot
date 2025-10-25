import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [
    react({
      // Skip tsconfig validation for dependencies
      babel: {
        parserOpts: {
          plugins: ['importAssertions'],
        },
      },
    }),
  ],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        '.next/',
        'vitest.config.ts',
        'vitest.setup.ts',
        '**/*.d.ts',
        '**/*.config.*',
        '**/test/**',
        '**/dist/**',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
      '@taboot/auth': path.resolve(__dirname, '../../packages-ts/auth/src'),
      '@taboot/db': path.resolve(__dirname, '../../packages-ts/db/src'),
      '@taboot/ui': path.resolve(__dirname, '../../packages-ts/ui/src'),
      '@taboot/utils': path.resolve(__dirname, '../../packages-ts/utils/src'),
      '@taboot/api-client': path.resolve(__dirname, '../../packages-ts/api-client/src'),
    },
  },
  esbuild: {
    jsx: 'automatic',
  },
});
