/**
 * Centralized authentication configuration constants.
 * These must match better-auth configuration.
 */

/** Primary session cookie name (configurable via env) */
export const AUTH_COOKIE_NAME = process.env.AUTH_COOKIE_NAME || 'better-auth.session_token';

/** Legacy cookie name for migration compatibility */
export const AUTH_COOKIE_LEGACY_NAME = 'authjs.session-token';

/** Bearer token prefix for Authorization header */
export const AUTH_BEARER_PREFIX = 'Bearer ';
