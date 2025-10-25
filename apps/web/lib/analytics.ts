import posthog from 'posthog-js';

/**
 * Analytics event properties
 */
export type EventProperties = Record<string, string | number | boolean | null | undefined>;

/**
 * User traits for identification
 */
export type UserTraits = Record<string, string | number | boolean | null | undefined>;

/**
 * Analytics wrapper for PostHog
 * Provides type-safe event tracking and graceful degradation when not configured
 */
export const analytics = {
  /**
   * Track a custom event
   * @param event - Event name (use snake_case convention)
   * @param properties - Event properties (no PII)
   */
  track(event: string, properties?: EventProperties): void {
    if (typeof window === 'undefined') return;

    try {
      if (posthog.__loaded) {
        posthog.capture(event, properties);
      }
    } catch (error) {
      console.warn('[Analytics] Failed to track event:', event, error);
    }
  },

  /**
   * Identify a user
   * @param userId - Unique user identifier (hashed/anonymized)
   * @param traits - User traits (no PII)
   */
  identify(userId: string, traits?: UserTraits): void {
    if (typeof window === 'undefined') return;

    try {
      if (posthog.__loaded) {
        posthog.identify(userId, traits);
      }
    } catch (error) {
      console.warn('[Analytics] Failed to identify user:', userId, error);
    }
  },

  /**
   * Track a page view
   */
  page(): void {
    if (typeof window === 'undefined') return;

    try {
      if (posthog.__loaded) {
        posthog.capture('$pageview');
      }
    } catch (error) {
      console.warn('[Analytics] Failed to track page view:', error);
    }
  },

  /**
   * Reset user identity (on logout)
   */
  reset(): void {
    if (typeof window === 'undefined') return;

    try {
      if (posthog.__loaded) {
        posthog.reset();
      }
    } catch (error) {
      console.warn('[Analytics] Failed to reset user:', error);
    }
  },

  /**
   * Set user properties
   * @param properties - User properties to set (no PII)
   */
  setUserProperties(properties: UserTraits): void {
    if (typeof window === 'undefined') return;

    try {
      if (posthog.__loaded) {
        posthog.people.set(properties);
      }
    } catch (error) {
      console.warn('[Analytics] Failed to set user properties:', error);
    }
  },

  /**
   * Check if analytics is enabled and loaded
   */
  isEnabled(): boolean {
    if (typeof window === 'undefined') return false;
    return posthog.__loaded || false;
  },
};

/**
 * Standard event names (use these for consistency)
 */
export const ANALYTICS_EVENTS = {
  // Authentication
  USER_SIGNED_IN: 'user_signed_in',
  USER_SIGNED_OUT: 'user_signed_out',
  USER_SIGNED_UP: 'user_signed_up',

  // Search & Query
  SEARCH_PERFORMED: 'search_performed',
  QUERY_EXECUTED: 'query_executed',
  QUERY_FAILED: 'query_failed',

  // Documents
  DOCUMENT_VIEWED: 'document_viewed',
  DOCUMENT_INGESTED: 'document_ingested',
  DOCUMENT_DELETED: 'document_deleted',

  // Graph
  GRAPH_VIEWED: 'graph_viewed',
  GRAPH_NODE_SELECTED: 'graph_node_selected',
  GRAPH_FILTER_APPLIED: 'graph_filter_applied',

  // Settings
  SETTINGS_UPDATED: 'settings_updated',
  THEME_CHANGED: 'theme_changed',

  // Errors
  ERROR_OCCURRED: 'error_occurred',
  API_ERROR: 'api_error',
} as const;
