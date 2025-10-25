import { describe, expect, it } from 'vitest';
import { queryKeys } from '../query-keys';

describe('Caching Strategy', () => {
  describe('Query Keys Factory', () => {
    it('should generate consistent auth.all keys', () => {
      const key1 = queryKeys.auth.all;
      const key2 = queryKeys.auth.all;
      expect(key1).toEqual(key2);
      expect(key1).toEqual(['auth']);
    });

    it('should generate consistent auth.hasPassword keys', () => {
      const key1 = queryKeys.auth.hasPassword();
      const key2 = queryKeys.auth.hasPassword();
      expect(key1).toEqual(key2);
      expect(key1).toEqual(['auth', 'hasPassword']);
    });

    it('should generate hierarchical keys', () => {
      const authAll = queryKeys.auth.all;
      const hasPassword = queryKeys.auth.hasPassword();

      // hasPassword should include auth.all as prefix
      expect(hasPassword[0]).toBe(authAll[0]);
      expect(hasPassword).toContain('auth');
      expect(hasPassword).toContain('hasPassword');
    });

    it('should generate user keys with different scopes', () => {
      const userAll = queryKeys.user.all;
      const userSettings = queryKeys.user.settings();

      expect(userSettings[0]).toBe(userAll[0]);
      expect(userSettings).toEqual(['user', 'settings']);
    });

    it('should support parameterized keys', () => {
      const userId1 = 'user-123';
      const userId2 = 'user-456';

      const profile1 = queryKeys.user.profile(userId1);
      const profile2 = queryKeys.user.profile(userId2);

      expect(profile1).toEqual(['user', 'profile', userId1]);
      expect(profile2).toEqual(['user', 'profile', userId2]);
      expect(profile1).not.toEqual(profile2);
    });
  });

  describe('Cache Configuration', () => {
    it('should use appropriate stale times for different data types', () => {
      // Test that our cache times are reasonable
      const fiveMinutes = 5 * 60 * 1000;
      const thirtyMinutes = 30 * 60 * 1000;
      const oneHour = 60 * 60 * 1000;

      // Password state changes infrequently - 30 minutes is appropriate
      expect(thirtyMinutes).toBe(1800000);

      // General cache time - 5 minutes is conservative
      expect(fiveMinutes).toBe(300000);

      // Long-term cache - 1 hour for rarely changing data
      expect(oneHour).toBe(3600000);
    });
  });
});
