import { withSentryConfig } from '@sentry/nextjs';

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@taboot/ui'],
  output: 'standalone',
  async headers() {
    return [
      {
        // Default cache control for API routes
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

  // Export with Sentry configuration
  export default withSentryConfig(nextConfig, sentryWebpackPluginOptions, sentryOptions);
} else {
  // Export plain config when Sentry is disabled
  export default nextConfig;
}
