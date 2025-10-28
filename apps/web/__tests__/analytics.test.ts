import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest';

describe('Analytics', () => {
  beforeEach(() => {
    // Mock window object
    global.window = {} as Window & typeof globalThis;

    // Clear console spies
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('track', () => {
    it('should gracefully handle PostHog not being loaded', () => {
      expect(() => {
        analytics.track(ANALYTICS_EVENTS.USER_SIGNED_IN);
      }).not.toThrow();
    });

    it('should not throw when tracking with properties', () => {
      expect(() => {
        analytics.track(ANALYTICS_EVENTS.SEARCH_PERFORMED, {
          query: 'test',
          results: 10,
        });
      }).not.toThrow();
    });
  });

  describe('identify', () => {
    it('should gracefully handle PostHog not being loaded', () => {
      expect(() => {
        analytics.identify('user-123');
      }).not.toThrow();
    });

    it('should not throw when identifying with traits', () => {
      expect(() => {
        analytics.identify('user-123', {
          plan: 'pro',
          role: 'admin',
        });
      }).not.toThrow();
    });
  });

  describe('page', () => {
    it('should gracefully handle PostHog not being loaded', () => {
      expect(() => {
        analytics.page();
      }).not.toThrow();
    });
  });

  describe('reset', () => {
    it('should gracefully handle PostHog not being loaded', () => {
      expect(() => {
        analytics.reset();
      }).not.toThrow();
    });
  });

  describe('setUserProperties', () => {
    it('should gracefully handle PostHog not being loaded', () => {
      expect(() => {
        analytics.setUserProperties({ theme: 'dark' });
      }).not.toThrow();
    });
  });

  describe('isEnabled', () => {
    it('should return false when PostHog is not loaded', () => {
      expect(analytics.isEnabled()).toBe(false);
    });

    it('should return false in server-side context', () => {
      // @ts-expect-error - Testing server-side behavior
      delete global.window;
      expect(analytics.isEnabled()).toBe(false);
    });
  });

  describe('ANALYTICS_EVENTS', () => {
    it('should have all expected event constants', () => {
      expect(ANALYTICS_EVENTS).toHaveProperty('USER_SIGNED_IN');
      expect(ANALYTICS_EVENTS).toHaveProperty('USER_SIGNED_OUT');
      expect(ANALYTICS_EVENTS).toHaveProperty('USER_SIGNED_UP');
      expect(ANALYTICS_EVENTS).toHaveProperty('SEARCH_PERFORMED');
      expect(ANALYTICS_EVENTS).toHaveProperty('QUERY_EXECUTED');
      expect(ANALYTICS_EVENTS).toHaveProperty('DOCUMENT_VIEWED');
      expect(ANALYTICS_EVENTS).toHaveProperty('GRAPH_VIEWED');
      expect(ANALYTICS_EVENTS).toHaveProperty('ERROR_OCCURRED');
    });

    it('should use snake_case naming convention', () => {
      Object.values(ANALYTICS_EVENTS).forEach((event) => {
        expect(event).toMatch(/^[a-z_]+$/);
      });
    });
  });
});
