/**
 * Tests for cleanup service
 *
 * Note: Tests are kept lightweight to avoid memory issues with Jest workers.
 * For comprehensive integration testing, use the actual script with test database.
 */

import { cleanupDeletedUsersService } from '../cleanup-service';
import type { CleanupDependencies, Logger } from '../types';

describe('cleanupDeletedUsersService', () => {
  // Global cleanup to help with memory
  afterAll(() => {
    jest.restoreAllMocks();
  });
  let mockPrisma: CleanupDependencies['prisma'];
  let mockLogger: Logger;
  let logMessages: string[];
  let errorMessages: Array<{ message: string; error?: unknown }>;

  beforeEach(() => {
    logMessages = [];
    errorMessages = [];

    mockLogger = {
      log: (message: string) => {
        logMessages.push(message);
      },
      error: (message: string, error?: unknown) => {
        errorMessages.push({ message, error });
      },
    };

    mockPrisma = {
      user: {
        count: jest.fn(),
        findMany: jest.fn(),
      },
      $executeRaw: jest.fn(),
    };
  });

  afterEach(() => {
    jest.clearAllMocks();
    // Clear references to help with garbage collection
    mockPrisma = undefined as unknown as CleanupDependencies['prisma'];
    mockLogger = undefined as unknown as Logger;
    logMessages = [];
    errorMessages = [];
  });

  describe('dry run mode', () => {
    it('should not delete users in dry run mode', async () => {
      const mockUsers = [
        {
          id: 'user-1',
          email: 'test1@example.com',
          deletedAt: new Date('2024-01-01'),
          deletedBy: 'admin',
          _count: { sessions: 2, accounts: 1, twofactors: 0 },
        },
      ];

      const mockUsersEmail = [
        {
          id: 'user-1',
          email: 'test1@example.com',
        },
      ];

      (mockPrisma.user.count as jest.Mock).mockResolvedValue(1);
      (mockPrisma.user.findMany as jest.Mock)
        .mockResolvedValueOnce(mockUsers) // First fetch for summaries
        .mockResolvedValueOnce([]) // End of first pagination
        .mockResolvedValueOnce(mockUsersEmail) // Second fetch for emails
        .mockResolvedValueOnce([]); // End of second pagination

      const result = await cleanupDeletedUsersService(
        { retentionDays: 90, dryRun: true },
        { prisma: mockPrisma, logger: mockLogger, verbose: false }
      );

      expect(result.totalFound).toBe(1);
      expect(result.successCount).toBe(0);
      expect(result.failedCount).toBe(0);
      expect(result.wasDryRun).toBe(true);
      expect(mockPrisma.$executeRaw).not.toHaveBeenCalled();

      // Verify PII masking in logs
      expect(logMessages.some((msg) => msg.includes('t***1@example.com'))).toBe(true);
      expect(logMessages.some((msg) => msg.includes('test1@example.com'))).toBe(false);
    });

    it('should show emails in verbose mode', async () => {
      const mockUsers = [
        {
          id: 'user-1',
          email: 'test1@example.com',
          deletedAt: new Date('2024-01-01'),
          deletedBy: 'admin',
          _count: { sessions: 2, accounts: 1, twofactors: 0 },
        },
      ];

      const mockUsersEmail = [
        {
          id: 'user-1',
          email: 'test1@example.com',
        },
      ];

      (mockPrisma.user.count as jest.Mock).mockResolvedValue(1);
      (mockPrisma.user.findMany as jest.Mock)
        .mockResolvedValueOnce(mockUsers)
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce(mockUsersEmail)
        .mockResolvedValueOnce([]);

      await cleanupDeletedUsersService(
        { retentionDays: 90, dryRun: true },
        { prisma: mockPrisma, logger: mockLogger, verbose: true }
      );

      // Verify no PII masking in verbose mode
      expect(logMessages.some((msg) => msg.includes('test1@example.com'))).toBe(true);
      expect(logMessages.some((msg) => msg.includes('t***1@example.com'))).toBe(false);
    });
  });

  describe('production mode', () => {
    it('should delete users when not in dry run', async () => {
      const mockUsers = [
        {
          id: 'user-1',
          email: 'test1@example.com',
          deletedAt: new Date('2024-01-01'),
          deletedBy: 'admin',
          _count: { sessions: 2, accounts: 1, twofactors: 0 },
        },
      ];

      (mockPrisma.user.count as jest.Mock).mockResolvedValue(1);
      (mockPrisma.user.findMany as jest.Mock)
        .mockResolvedValueOnce(mockUsers)
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce(mockUsers)
        .mockResolvedValueOnce([]);

      (mockPrisma.$executeRaw as jest.Mock).mockResolvedValue(undefined);

      const result = await cleanupDeletedUsersService(
        { retentionDays: 90, dryRun: false },
        { prisma: mockPrisma, logger: mockLogger, verbose: false }
      );

      expect(result.totalFound).toBe(1);
      expect(result.successCount).toBe(1);
      expect(result.failedCount).toBe(0);
      expect(result.wasDryRun).toBe(false);
      expect(result.failedUserIds).toHaveLength(0);

      // Verify both DELETE and audit log INSERT were called
      expect(mockPrisma.$executeRaw).toHaveBeenCalledTimes(2);
    });

    it('should handle deletion failures gracefully', async () => {
      const mockUsers = [
        {
          id: 'user-1',
          email: 'test1@example.com',
          deletedAt: new Date('2024-01-01'),
          deletedBy: 'admin',
          _count: { sessions: 2, accounts: 1, twofactors: 0 },
        },
      ];

      (mockPrisma.user.count as jest.Mock).mockResolvedValue(1);
      (mockPrisma.user.findMany as jest.Mock)
        .mockResolvedValueOnce(mockUsers)
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce(mockUsers)
        .mockResolvedValueOnce([]);

      (mockPrisma.$executeRaw as jest.Mock).mockRejectedValueOnce(new Error('Database error'));

      const result = await cleanupDeletedUsersService(
        { retentionDays: 90, dryRun: false },
        { prisma: mockPrisma, logger: mockLogger, verbose: false }
      );

      expect(result.totalFound).toBe(1);
      expect(result.successCount).toBe(0);
      expect(result.failedCount).toBe(1);
      expect(result.failedUserIds).toEqual(['user-1']);
      expect(errorMessages).toHaveLength(1);
      expect(errorMessages[0]?.message).toContain('Failed to delete');
    });
  });

  describe('edge cases', () => {
    it('should handle no users to delete', async () => {
      (mockPrisma.user.count as jest.Mock).mockResolvedValue(0);

      const result = await cleanupDeletedUsersService(
        { retentionDays: 90, dryRun: false },
        { prisma: mockPrisma, logger: mockLogger, verbose: false }
      );

      expect(result.totalFound).toBe(0);
      expect(result.successCount).toBe(0);
      expect(result.failedCount).toBe(0);
      expect(result.users).toHaveLength(0);
      expect(mockPrisma.$executeRaw).not.toHaveBeenCalled();
    });

    it('should handle users with null email', async () => {
      const mockUsers = [
        {
          id: 'user-1',
          email: null,
          deletedAt: new Date('2024-01-01'),
          deletedBy: 'admin',
          _count: { sessions: 0, accounts: 0, twofactors: 0 },
        },
      ];

      (mockPrisma.user.count as jest.Mock).mockResolvedValue(1);
      (mockPrisma.user.findMany as jest.Mock)
        .mockResolvedValueOnce(mockUsers)
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce(mockUsers)
        .mockResolvedValueOnce([]);

      (mockPrisma.$executeRaw as jest.Mock).mockResolvedValue(undefined);

      const result = await cleanupDeletedUsersService(
        { retentionDays: 90, dryRun: false },
        { prisma: mockPrisma, logger: mockLogger, verbose: false }
      );

      expect(result.successCount).toBe(1);
      expect(logMessages.some((msg) => msg.includes('[no email]'))).toBe(true);
    });
  });

  describe('audit logging', () => {
    it('should create audit log entries for each deletion', async () => {
      const mockUsers = [
        {
          id: 'user-1',
          email: 'test1@example.com',
          deletedAt: new Date('2024-01-01'),
          deletedBy: 'admin',
          _count: { sessions: 2, accounts: 1, twofactors: 0 },
        },
      ];

      const mockUsersEmail = [
        {
          id: 'user-1',
          email: 'test1@example.com',
        },
      ];

      (mockPrisma.user.count as jest.Mock).mockResolvedValue(1);
      (mockPrisma.user.findMany as jest.Mock)
        .mockResolvedValueOnce(mockUsers)
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce(mockUsersEmail)
        .mockResolvedValueOnce([]);

      (mockPrisma.$executeRaw as jest.Mock).mockResolvedValue(undefined);

      await cleanupDeletedUsersService(
        { retentionDays: 90, dryRun: false },
        { prisma: mockPrisma, logger: mockLogger, verbose: false }
      );

      // First call is DELETE, second is audit INSERT
      const calls = (mockPrisma.$executeRaw as jest.Mock).mock.calls;
      expect(calls).toHaveLength(2);

      // Verify DELETE call
      const deleteCall = calls[0];
      expect(String(deleteCall?.[0])).toContain('DELETE FROM');
      expect(deleteCall?.[1]).toBe('user-1');

      // Verify audit log call contains the expected SQL
      const auditCall = calls[1];
      const sqlString = String(auditCall?.[0]);
      expect(sqlString).toContain('INSERT INTO');
      expect(sqlString).toContain('audit_log');
    });
  });
});
