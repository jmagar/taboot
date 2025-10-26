import * as Sentry from '@sentry/nextjs';

const SENTRY_DSN = process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,

    // Set tracesSampleRate to 1.0 to capture 100% of transactions for performance monitoring.
    // We recommend adjusting this value in production, or using tracesSampler for greater control
    tracesSampleRate: 0.1,

    // Setting this option to true will print useful information to the console while you're setting up Sentry.
    debug: false,

    environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV,

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
        'key',
        'secret',
        'sessionid',
        'phone',
        'address',
        'ssn',
      ]);

      // Helper function to scrub sensitive data from any object (recursive with array support)
      const scrubData = (data: unknown): unknown => {
        if (data === null || data === undefined) return data;
        if (Array.isArray(data)) return data.map((v) => scrubData(v));
        if (typeof data === 'object') {
          const input = data as Record<string, unknown>;
          const out: Record<string, unknown> = {};
          for (const [key, value] of Object.entries(input)) {
            if (scrubKeys.has(key.toLowerCase())) {
              out[key] = '[Filtered]';
            } else {
              out[key] = scrubData(value);
            }
          }
          return out;
        }
        return data;
      };

      // Filter out PII from breadcrumbs
      if (event.breadcrumbs) {
        event.breadcrumbs = event.breadcrumbs.map((breadcrumb) => {
          if (breadcrumb.data) {
            return { ...breadcrumb, data: scrubData(breadcrumb.data) as Record<string, unknown> };
          }
          return breadcrumb;
        });
      }

      // Filter out PII from request data
      if (event.request?.data && typeof event.request.data === 'object') {
        event.request.data = scrubData(event.request.data) as Record<string, unknown>;
      }

      // Filter out PII from request headers
      if (event.request?.headers) {
        event.request.headers = scrubData(event.request.headers) as Record<string, string>;
      }

      // Filter out PII from contexts
      if (event.contexts) {
        for (const [contextKey, contextValue] of Object.entries(event.contexts)) {
          if (contextValue && typeof contextValue === 'object') {
            event.contexts[contextKey] = scrubData(contextValue) as Record<string, unknown>;
          }
        }
      }

      // Filter out PII from extra data
      if (event.extra) {
        event.extra = scrubData(event.extra) as Record<string, unknown>;
      }

      return event;
    },
  });
}

if (!SENTRY_DSN) {
  console.log('Sentry integration disabled (SENTRY_DSN or NEXT_PUBLIC_SENTRY_DSN not configured)');
}
