import posthog from 'posthog-js';

export function initPostHog() {
  const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  const posthogHost = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com';

  if (typeof window !== 'undefined' && posthogKey) {
    posthog.init(posthogKey, {
      api_host: posthogHost,
      loaded: (posthog) => {
        if (process.env.NODE_ENV === 'development') {
          posthog.debug();
        }
      },
      // Disable session recording in development
      disable_session_recording: process.env.NODE_ENV === 'development',
      // Respect "Do Not Track" browser setting
      respect_dnt: true,
      // Capture pageviews automatically
      capture_pageview: true,
      // Capture page leaves
      capture_pageleave: true,
    });
  }

  return posthog;
}
