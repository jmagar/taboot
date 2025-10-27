import * as Sentry from '@sentry/nextjs';
import { parseSampleRate, resolveSentryEnvironment, scrubData } from '@/lib/sentry-utils';

const SENTRY_DSN = process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN;
const IS_PRODUCTION = process.env.NODE_ENV === 'production';

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,

    // Environment-driven sampling rates with production/dev defaults
    tracesSampleRate: parseSampleRate(
      process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE,
      IS_PRODUCTION ? 0.1 : 1.0,
    ),

    // Setting this option to true will print useful information to the console while you're setting up Sentry.
    debug: false,

    replaysOnErrorSampleRate: parseSampleRate(
      process.env.NEXT_PUBLIC_SENTRY_REPLAYS_ON_ERROR_RATE,
      1.0,
    ),

    // Environment-driven session replay rate
    replaysSessionSampleRate: parseSampleRate(
      process.env.NEXT_PUBLIC_SENTRY_REPLAYS_SESSION_RATE,
      IS_PRODUCTION ? 0.1 : 1.0,
    ),

    // You can remove this option if you're not planning to use the Sentry Session Replay feature:
    integrations: [
      Sentry.replayIntegration({
        // Additional Replay configuration goes in here, for example:
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],

    // Deployment-aware environment detection (Vercel-compatible)
    environment: resolveSentryEnvironment(),

    // Configure beforeSend to filter sensitive data
    beforeSend(event, hint) {
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
