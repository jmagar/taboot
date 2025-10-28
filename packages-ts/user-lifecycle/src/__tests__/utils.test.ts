/**
 * Tests for utility functions
 */

import { calculateCutoffDate, formatDate, maskEmail } from '../utils';

describe('maskEmail', () => {
  it('should mask regular email addresses', () => {
    expect(maskEmail('john.doe@example.com')).toBe('j***e@example.com');
    expect(maskEmail('user@test.com')).toBe('u***r@test.com');
  });

  it('should handle single character local parts', () => {
    expect(maskEmail('a@test.com')).toBe('a***@test.com');
  });

  it('should handle two character local parts', () => {
    expect(maskEmail('ab@test.com')).toBe('a***b@test.com');
  });

  it('should handle null and undefined', () => {
    expect(maskEmail(null)).toBe('[no email]');
    expect(maskEmail(undefined)).toBe('[no email]');
  });

  it('should handle invalid email formats', () => {
    expect(maskEmail('notanemail')).toBe('[invalid email]');
    expect(maskEmail('@nodomain.com')).toBe('[invalid email]');
    expect(maskEmail('noatsign.com')).toBe('[invalid email]');
  });
});

describe('formatDate', () => {
  it('should format valid dates as ISO 8601', () => {
    const date = new Date('2024-01-15T10:30:00Z');
    expect(formatDate(date)).toBe('2024-01-15T10:30:00.000Z');
  });

  it('should handle null and undefined', () => {
    expect(formatDate(null)).toBe('[unknown]');
    expect(formatDate(undefined)).toBe('[unknown]');
  });
});

describe('calculateCutoffDate', () => {
  it('should calculate cutoff date correctly', () => {
    const now = new Date('2024-10-26T00:00:00Z');
    jest.useFakeTimers();
    jest.setSystemTime(now);

    const cutoff = calculateCutoffDate(90);
    const expected = new Date('2024-07-28T00:00:00Z');

    expect(cutoff.toISOString()).toBe(expected.toISOString());

    jest.useRealTimers();
  });

  it('should handle different retention periods', () => {
    const now = new Date('2024-10-26T00:00:00Z');
    jest.useFakeTimers();
    jest.setSystemTime(now);

    const cutoff1 = calculateCutoffDate(1);
    const cutoff30 = calculateCutoffDate(30);
    const cutoff365 = calculateCutoffDate(365);

    // Verify the dates are correct by checking day difference
    expect(Math.floor((now.getTime() - cutoff1.getTime()) / (1000 * 60 * 60 * 24))).toBe(1);
    expect(Math.floor((now.getTime() - cutoff30.getTime()) / (1000 * 60 * 60 * 24))).toBe(30);
    expect(Math.floor((now.getTime() - cutoff365.getTime()) / (1000 * 60 * 60 * 24))).toBe(365);

    jest.useRealTimers();
  });
});
