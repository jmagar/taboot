/**
 * CSRF-Aware API Client
 *
 * Automatically includes CSRF tokens in state-changing requests.
 * The token is retrieved from the cookie set by the middleware.
 */

const CSRF_TOKEN_HEADER_NAME = 'x-csrf-token';
// FIX 1: Match server-side cookie name logic (dev vs prod)
const CSRF_TOKEN_COOKIE_NAME =
  process.env.NODE_ENV === 'production' ? '__Host-taboot.csrf' : 'taboot.csrf';

/**
 * Get CSRF token from cookies
 */
function getCsrfTokenFromCookie(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }

  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const idx = cookie.indexOf('=');
    if (idx === -1) continue;
    const name = cookie.slice(0, idx).trim();
    const value = cookie.slice(idx + 1).trim();
    if (name === CSRF_TOKEN_COOKIE_NAME && value) {
      return decodeURIComponent(value);
    }
  }

  return null;
}

/**
 * Enhance fetch options with CSRF token for state-changing methods
 */
export function withCsrfToken(options: RequestInit = {}): RequestInit {
  const method = options.method?.toUpperCase();

  // Only add CSRF token for state-changing methods
  if (!method || ['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    return options;
  }

  const token = getCsrfTokenFromCookie();
  if (!token) {
    console.warn('CSRF token not found in cookies. Request may be rejected.');
    return options;
  }

  const normalized =
    options.headers instanceof Headers
      ? Object.fromEntries(options.headers.entries())
      : (options.headers ?? {});
  return {
    ...options,
    headers: {
      ...normalized,
      [CSRF_TOKEN_HEADER_NAME]: token,
    },
  };
}

/**
 * Fetch wrapper that automatically includes CSRF tokens
 */
export async function csrfFetch(url: string, options?: RequestInit): Promise<Response> {
  return fetch(url, withCsrfToken(options));
}
