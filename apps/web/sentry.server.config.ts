import * as Sentry from '@sentry/nextjs';

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,

    // Set tracesSampleRate to 1.0 to capture 100% of transactions for performance monitoring.
    // We recommend adjusting this value in production, or using tracesSampler for greater control
    tracesSampleRate: 0.1,

    // Setting this option to true will print useful information to the console while you're setting up Sentry.
    debug: false,

    environment: process.env.NODE_ENV,

    // Configure beforeSend to filter sensitive data
    beforeSend(event, hint) {
      // Fix #3: Comprehensive PII scrubbing with case-insensitive matching
      const scrubKeys = new Set([
        'email',
        'password',
        'pass',
        'token',
        'access_token',
        'refresh_token',
        'authorization',
        'auth',
        'apikey',
        'apikey',
        'key',
        'secret',
        'sessionid',
        'phone',
        'address',
        'ssn',
      ]);

      // Helper function to scrub sensitive data from any object
      const scrubData = (data: Record<string, unknown>): Record<string, unknown> => {
        const scrubbed: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(data)) {
          if (scrubKeys.has(key.toLowerCase())) {
            scrubbed[key] = '[Filtered]';
          } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            scrubbed[key] = scrubData(value as Record<string, unknown>);
          } else {
            scrubbed[key] = value;
          }
        }
        return scrubbed;
      };

      // Filter out PII from breadcrumbs
      if (event.breadcrumbs) {
        event.breadcrumbs = event.breadcrumbs.map((breadcrumb) => {
          if (breadcrumb.data) {
            return { ...breadcrumb, data: scrubData(breadcrumb.data) };
          }
          return breadcrumb;
        });
      }

      // Filter out PII from request data
      if (event.request?.data && typeof event.request.data === 'object') {
        event.request.data = scrubData(event.request.data as Record<string, unknown>);
      }

      // Filter out PII from request headers
      if (event.request?.headers) {
        event.request.headers = scrubData(event.request.headers as Record<string, unknown>);
      }

      // Filter out PII from contexts
      if (event.contexts) {
        for (const [contextKey, contextValue] of Object.entries(event.contexts)) {
          if (contextValue && typeof contextValue === 'object') {
            event.contexts[contextKey] = scrubData(contextValue as Record<string, unknown>);
          }
        }
      }

      // Filter out PII from extra data
      if (event.extra) {
        event.extra = scrubData(event.extra as Record<string, unknown>);
      }

      return event;
    },
  });
}
