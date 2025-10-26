'use client';

import { useEffect } from 'react';

interface CSPScriptsProps {
  nonce?: string;
}

declare global {
  interface Window {
    posthog?: {
      onFeatureFlags: (callback: () => void) => void;
    };
  }
}

/**
 * CSP-compliant scripts for analytics and error tracking
 * All scripts include the CSP nonce to bypass Content-Security-Policy restrictions
 */
export function CSPScripts({ nonce }: CSPScriptsProps) {
  useEffect(() => {
    // Initialize PostHog analytics if key is configured
    if (typeof window !== 'undefined' && window.posthog) {
      window.posthog.onFeatureFlags(() => {
        // Feature flags loaded
      });
    }
  }, []);

  return (
    <>
      {/* Vercel Analytics - uses CSP nonce */}
      {process.env.NEXT_PUBLIC_VERCEL_ANALYTICS_ID && (
        <script
          async
          src="/_vercel/insights/script.js"
          nonce={nonce}
          data-endpoint="/_vercel/insights"
        />
      )}

      {/* PostHog Analytics - loads with script tag */}
      {process.env.NEXT_PUBLIC_POSTHOG_KEY && (
        <script
          nonce={nonce}
          dangerouslySetInnerHTML={{
            __html: `
              !function(t,e){var o,n,p,r,a=e.location,c="script",s="text/javascript",u="https://us-eu.posthog.com/array.js";(o=e.createElement(c)).type=s,o.async=!0,o.src=u,(n=e.getElementsByTagName(c)[0]).parentNode.insertBefore(o,n);var d=e.createElement(c);d.type=s,d.nonce="${nonce}",d.innerHTML='window.posthog=window.posthog||{},window.posthog._l=[],["capture","identify","people","group","retention","debug","reset","get_distinct_id","get_session_id","get_session_replay_url","alias"].forEach(function(e){window.posthog[e]=function(){window.posthog._l.push([e].concat(Array.prototype.slice.call(arguments,0)))}}),posthog.init("${process.env.NEXT_PUBLIC_POSTHOG_KEY}",{api_host:"${process.env.NEXT_PUBLIC_POSTHOG_HOST||'https://app.posthog.com'}",session_recording:{sample_rate:.5},loaded:function(e){e.identify()}});',e.head.appendChild(d)
            `,
          }}
        />
      )}

      {/* Sentry Error Tracking */}
      {process.env.NEXT_PUBLIC_SENTRY_DSN && (
        <script
          nonce={nonce}
          src="https://browser.sentry-cdn.com/8.46.0/bundle.min.js"
          integrity="sha384-1YzVSZWpEZ/QfCC8lhJ+R0+exzvzxGpSIKYO8m2CKl0+Tl+KvLCDlh80TgmxWvXi"
          crossOrigin="anonymous"
        />
      )}
    </>
  );
}
