import { withSentryConfig } from '@sentry/nextjs';

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@taboot/ui'],
  output: 'standalone',
  async headers() {
    return [
      {
        // Stricter cache control for auth endpoints - no-store prevents any caching
        source: '/api/auth/:path*',
        headers: [
          {
            key: 'Cache-Control',
            // Private (user-specific), no-store (never cache), no-cache (must revalidate), must-revalidate
            value: 'private, no-store, no-cache, must-revalidate',
          },
        ],
      },
      {
        // Default cache control for other API routes
        source: '/api/:path*',
        headers: [
          {
            key: 'Cache-Control',
            // Private (user-specific), no-cache (must revalidate), must-revalidate
            // Individual routes can override with more specific caching
            value: 'private, no-cache, must-revalidate',
          },
        ],
      },
    ];
  },
};

// Only enable Sentry if both SENTRY_ORG and SENTRY_PROJECT are configured
const sentryEnabled = process.env.SENTRY_ORG && process.env.SENTRY_PROJECT;

// Use variable assignment pattern to avoid illegal export inside if/else blocks
let config = nextConfig;

if (sentryEnabled) {
  // Sentry configuration options
  const sentryWebpackPluginOptions = {
    // For all available options, see:
    // https://github.com/getsentry/sentry-webpack-plugin#options

    // Suppresses source map uploading logs during build
    silent: true,
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
  };

  const sentryOptions = {
    // For all available options, see:
    // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

    // Upload a larger set of source maps for prettier stack traces (increases build time)
    widenClientFileUpload: true,

    // Hides source maps from generated client bundles
    hideSourceMaps: true,

    // Automatically tree-shake Sentry logger statements to reduce bundle size
    disableLogger: true,

    // Enables automatic instrumentation of Vercel Cron Monitors.
    automaticVercelMonitors: true,
  };

  // Apply Sentry configuration when enabled
  config = withSentryConfig(nextConfig, sentryWebpackPluginOptions, sentryOptions);
}

// Export the final config (with or without Sentry)
export default config;
