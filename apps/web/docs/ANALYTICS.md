# Analytics & Observability

This document describes the analytics and observability implementation for the Taboot web application.

## Overview

The application uses three complementary analytics services:

1. **Sentry** - Error tracking and performance monitoring
2. **PostHog** - Product analytics and feature usage tracking
3. **Vercel Analytics** - Page view analytics (automatic on Vercel deployments)

## Configuration

All analytics are **optional** and gracefully degrade when not configured. This allows development without credentials.

### Environment Variables

Add these to your `.env.local` file (copy from `.env.example`):

```bash
# Sentry Error Tracking
NEXT_PUBLIC_SENTRY_DSN=""           # Get from https://sentry.io
SENTRY_ORG=""                       # Optional: for source map uploads
SENTRY_PROJECT=""                   # Optional: for source map uploads
SENTRY_AUTH_TOKEN=""                # Optional: for source map uploads

# PostHog Product Analytics
NEXT_PUBLIC_POSTHOG_KEY=""          # Get from https://posthog.com
NEXT_PUBLIC_POSTHOG_HOST="https://app.posthog.com"  # Or self-hosted URL
```

**Important:** All client-side env vars **must** have the `NEXT_PUBLIC_` prefix.

## Services

### Sentry

**What it tracks:**
- JavaScript errors and unhandled rejections
- Performance traces (10% sample rate)
- Session replays on errors only (privacy-focused)

**Configuration:**
- Client config: `apps/web/sentry.client.config.ts`
- Server config: `apps/web/sentry.server.config.ts`
- Next.js integration: `apps/web/next.config.mjs`

**Sampling rates:**
- Trace sample: 0.1 (10%)
- Replay on error: 1.0 (100%)
- Replay session: 0.1 (10%)

**Privacy features:**
- PII filtering in `beforeSend` hook
- Masks all text in session replay
- Blocks all media in session replay

**Limitations:**
- **Client-side only** - Sentry is configured for client-side tracking only
- **No Edge Runtime support** - Edge middleware cannot use Sentry
- Works in development and production

### PostHog

**What it tracks:**
- Custom events (user actions, feature usage)
- Page views (automatic)
- User identification and traits
- Session recording (disabled in development)

**Configuration:**
- Initialization: `apps/web/lib/posthog.ts`
- Wrapper: `apps/web/lib/analytics.ts`
- Integrated in: `apps/web/components/providers.tsx`

**Features:**
- Respects "Do Not Track" browser setting
- Debug mode in development
- Type-safe event tracking
- Graceful degradation when not configured

### Vercel Analytics

**What it tracks:**
- Page views
- Web Vitals (Core Web Vitals metrics)

**Configuration:**
- Integrated in: `apps/web/app/layout.tsx`
- No environment variables needed
- Automatic when deployed to Vercel

## Usage

### Tracking Events

```typescript
import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';

// Track a predefined event
analytics.track(ANALYTICS_EVENTS.USER_SIGNED_IN);

// Track with properties
analytics.track(ANALYTICS_EVENTS.SEARCH_PERFORMED, {
  query: 'graph traversal',
  results: 42,
  source: 'dashboard',
});

// Track custom events (use snake_case)
analytics.track('feature_enabled', {
  feature: 'dark_mode',
  enabled: true,
});
```

### User Identification

```typescript
import { analytics } from '@/lib/analytics';

// Identify user (use anonymized/hashed ID)
analytics.identify('user-hash-123', {
  plan: 'pro',
  role: 'admin',
});

// Set user properties
analytics.setUserProperties({
  theme: 'dark',
  notifications: true,
});

// Reset on logout
analytics.reset();
```

### Available Events

All event constants are in `ANALYTICS_EVENTS`:

```typescript
// Authentication
USER_SIGNED_IN
USER_SIGNED_OUT
USER_SIGNED_UP

// Search & Query
SEARCH_PERFORMED
QUERY_EXECUTED
QUERY_FAILED

// Documents
DOCUMENT_VIEWED
DOCUMENT_INGESTED
DOCUMENT_DELETED

// Graph
GRAPH_VIEWED
GRAPH_NODE_SELECTED
GRAPH_FILTER_APPLIED

// Settings
SETTINGS_UPDATED
THEME_CHANGED

// Errors
ERROR_OCCURRED
API_ERROR
```

## Privacy & Security

### No PII Policy

**Never** send personally identifiable information (PII) in analytics events:

- ❌ Email addresses
- ❌ Full names
- ❌ Passwords or tokens
- ❌ IP addresses (handled automatically)
- ❌ Sensitive query content

**Safe to send:**

- ✅ Anonymized/hashed user IDs
- ✅ Feature flags and settings
- ✅ Aggregate metrics (counts, durations)
- ✅ Generic query types (not content)
- ✅ UI interaction patterns

### Sentry Privacy

Sentry automatically filters PII from breadcrumbs in the `beforeSend` hook:

```typescript
beforeSend(event) {
  if (event.breadcrumbs) {
    event.breadcrumbs = event.breadcrumbs.map((breadcrumb) => {
      if (breadcrumb.data) {
        const { email, password, token, ...safeData } = breadcrumb.data;
        return { ...breadcrumb, data: safeData };
      }
      return breadcrumb;
    });
  }
  return event;
}
```

### PostHog Privacy

- Respects "Do Not Track" browser setting
- Session recording disabled in development
- No automatic form capture
- Manual event tracking only (explicit control)

## Testing

### Unit Tests

Run analytics tests:

```bash
pnpm --filter @taboot/web test __tests__/analytics.test.ts
```

### Manual Testing

1. **Check PostHog initialization:**

   ```bash
   pnpm --filter @taboot/web dev
   # Open browser console
   # Look for: "[PostHog] Initializing..." (in dev mode)
   ```

2. **Trigger test events:**

   ```typescript
   // In browser console
   import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
   analytics.track(ANALYTICS_EVENTS.USER_SIGNED_IN);
   ```

3. **Check Sentry error tracking:**

   ```typescript
   // Trigger test error
   throw new Error('Test Sentry error');
   // Check Sentry dashboard for error
   ```

4. **Verify Vercel Analytics:**
   - Deploy to Vercel
   - Check Analytics dashboard in Vercel project settings

### Development Mode

Without credentials, analytics will:

- ✅ Not crash or throw errors
- ✅ Log warnings to console (silently fail)
- ✅ Return false from `analytics.isEnabled()`
- ✅ Skip all tracking calls

## Build Considerations

### Known Issue: Middleware Edge Runtime

The application currently has a **pre-existing build issue** with Prisma and Edge Runtime middleware (unrelated to analytics):

```text
Error: A Node.js API is used (setImmediate) which is not supported in the Edge Runtime.
```

**Status:** This is an existing codebase issue with `apps/web/middleware.ts` using Prisma in Edge Runtime.

**Workaround:** Development mode (`pnpm dev`) works fine. Production builds require fixing the middleware/Prisma edge compatibility issue.

**Analytics impact:** None - this issue exists independently of analytics integration.

### Source Maps

Sentry can upload source maps during build for better stack traces:

```bash
# Set these env vars for production builds
SENTRY_ORG="your-org"
SENTRY_PROJECT="your-project"
SENTRY_AUTH_TOKEN="your-token"
```

Source maps are automatically uploaded via `withSentryConfig` in `next.config.mjs`.

## Monitoring Checklist

After deployment:

- [ ] Sentry capturing errors
- [ ] PostHog tracking page views
- [ ] Custom events appearing in PostHog
- [ ] Vercel Analytics showing traffic
- [ ] No PII in any analytics events
- [ ] Session replays only on errors (privacy)
- [ ] "Do Not Track" respected

## Troubleshooting

### PostHog not initializing

- Check `NEXT_PUBLIC_POSTHOG_KEY` in `.env.local`
- Verify env var has `NEXT_PUBLIC_` prefix
- Check browser console for errors
- Verify `analytics.isEnabled()` returns `true`

### Sentry not capturing errors

- Check `NEXT_PUBLIC_SENTRY_DSN` in `.env.local`
- Verify DSN format: `https://key@host/project-id`
- Check browser console for Sentry initialization
- Test with: `throw new Error('Test')`

### Vercel Analytics not working

- Only works on Vercel deployments
- Check project settings → Analytics
- Verify `<Analytics />` in `layout.tsx`

## Architecture

```text
┌─────────────────────────────────────────┐
│          apps/web/app/layout.tsx        │
│  ┌────────────────────────────────┐     │
│  │  <Providers>                   │     │
│  │    - PostHog init              │     │
│  │    - Error boundaries          │     │
│  │  </Providers>                  │     │
│  │  <Analytics /> (Vercel)        │     │
│  └────────────────────────────────┘     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│       Client-side (Browser)             │
│  ┌────────────────────────────────┐     │
│  │  Sentry.init()                 │     │
│  │  - ./sentry.client.config.ts   │     │
│  │  - Error tracking              │     │
│  │  - Performance traces          │     │
│  │  - Session replay              │     │
│  └────────────────────────────────┘     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│   Type-safe Analytics Wrapper           │
│  ┌────────────────────────────────┐     │
│  │  apps/web/lib/analytics.ts     │     │
│  │  - track()                     │     │
│  │  - identify()                  │     │
│  │  - page()                      │     │
│  │  - reset()                     │     │
│  │  - ANALYTICS_EVENTS            │     │
│  └────────────────────────────────┘     │
└─────────────────────────────────────────┘
```

## Files Created/Modified

### Created

- `apps/web/sentry.client.config.ts` - Client-side Sentry configuration
- `apps/web/sentry.server.config.ts` - Server-side Sentry configuration (Node.js only)
- `apps/web/lib/posthog.ts` - PostHog initialization
- `apps/web/lib/analytics.ts` - Type-safe analytics wrapper
- `apps/web/__tests__/analytics.test.ts` - Analytics tests
- `apps/web/ANALYTICS.md` - This documentation

### Modified

- `apps/web/app/layout.tsx` - Added Vercel Analytics
- `apps/web/components/providers.tsx` - Added PostHog initialization
- `apps/web/next.config.mjs` - Wrapped with Sentry config
- `.env.example` - Added analytics environment variables

## Resources

- [Sentry Next.js Documentation](https://docs.sentry.io/platforms/javascript/guides/nextjs/)
- [PostHog Next.js Documentation](https://posthog.com/docs/libraries/next-js)
- [Vercel Analytics Documentation](https://vercel.com/docs/analytics)

## Support

For issues or questions about analytics:

1. Check this documentation
2. Verify environment variables
3. Check browser console for errors
4. Review analytics service dashboards
5. Test with `analytics.isEnabled()` to verify setup
