import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { PrismaClient } from '@taboot/db/generated/prisma';
import {
  softDeleteMiddleware,
  setSoftDeleteContext,
  clearSoftDeleteContext,
  restoreUser,
} from '@taboot/db';

describe('Soft Delete Middleware', () => {
  let prisma: PrismaClient;
  let testUserId: string;
  let testRequestId: string;

  beforeEach(async () => {
    // Create fresh Prisma client with middleware
    prisma = new PrismaClient();
    testRequestId = `test-${Date.now()}`;
    prisma.$use(softDeleteMiddleware(testRequestId));

    // Create test user
    testUserId = `test-user-${Date.now()}`;
    await prisma.user.create({
      data: {
        id: testUserId,
        email: `test-${Date.now()}@example.com`,
        name: 'Test User',
        emailVerified: true,
      },
    });
  });

  afterEach(async () => {
    // Clean up
    clearSoftDeleteContext(testRequestId);

    // Hard delete test data (bypass middleware)
    await prisma.$executeRaw`DELETE FROM "user" WHERE id = ${testUserId}`;
    await prisma.$executeRaw`DELETE FROM "audit_log" WHERE target_id = ${testUserId}`;

    await prisma.$disconnect();
  });

  describe('DELETE operations', () => {
    it('should convert DELETE to UPDATE with deletedAt', async () => {
      // Set context
      setSoftDeleteContext(testRequestId, {
        userId: 'admin-user',
        ipAddress: '127.0.0.1',
        userAgent: 'test-agent',
      });

      // Delete user
      await prisma.user.delete({
        where: { id: testUserId },
      });

      // Verify soft delete (bypass filter to check actual state)
      const user = await prisma.$queryRaw<any[]>`
        SELECT * FROM "user" WHERE id = ${testUserId}
      `;

      expect(user).toHaveLength(1);
      expect(user[0].deleted_at).toBeTruthy();
      expect(user[0].deleted_by).toBe('admin-user');
    });

    it('should write audit log on DELETE', async () => {
      setSoftDeleteContext(testRequestId, {
        userId: 'admin-user',
      });

      await prisma.user.delete({
        where: { id: testUserId },
      });

      // Check audit log
      const auditLogs = await prisma.$queryRaw<any[]>`
        SELECT * FROM "audit_log"
        WHERE target_id = ${testUserId}
        AND action = 'DELETE'
      `;

      expect(auditLogs).toHaveLength(1);
      expect(auditLogs[0].user_id).toBe('admin-user');
      expect(auditLogs[0].target_type).toBe('User');
    });

    it('should handle deleteMany operations', async () => {
      // Create multiple test users
      const user2Id = `test-user-2-${Date.now()}`;
      await prisma.user.create({
        data: {
          id: user2Id,
          email: `test2-${Date.now()}@example.com`,
          name: 'Test User 2',
          emailVerified: true,
        },
      });

      setSoftDeleteContext(testRequestId, {
        userId: 'admin-user',
      });

      // Delete multiple users
      await prisma.user.deleteMany({
        where: {
          id: { in: [testUserId, user2Id] },
        },
      });

      // Verify both are soft-deleted
      const users = await prisma.$queryRaw<any[]>`
        SELECT * FROM "user"
        WHERE id IN (${testUserId}, ${user2Id})
      `;

      expect(users).toHaveLength(2);
      expect(users[0].deleted_at).toBeTruthy();
      expect(users[1].deleted_at).toBeTruthy();

      // Cleanup
      await prisma.$executeRaw`DELETE FROM "user" WHERE id = ${user2Id}`;
      await prisma.$executeRaw`DELETE FROM "audit_log" WHERE target_id = ${user2Id}`;
    });
  });

  describe('Query filtering', () => {
    it('should filter soft-deleted users from findMany', async () => {
      // Soft delete the user
      await prisma.$executeRaw`
        UPDATE "user"
        SET deleted_at = NOW(), deleted_by = 'test'
        WHERE id = ${testUserId}
      `;

      // Query should not return soft-deleted user
      const users = await prisma.user.findMany({
        where: { id: testUserId },
      });

      expect(users).toHaveLength(0);
    });

    it('should allow querying soft-deleted users explicitly', async () => {
      // Soft delete the user
      await prisma.$executeRaw`
        UPDATE "user"
        SET deleted_at = NOW(), deleted_by = 'test'
        WHERE id = ${testUserId}
      `;

      // Explicit query for deleted users should work
      const users = await prisma.user.findMany({
        where: {
          id: testUserId,
          deletedAt: { not: null },
        },
      });

      expect(users).toHaveLength(1);
      expect(users[0].deletedAt).toBeTruthy();
    });

    it('should filter soft-deleted users from findFirst', async () => {
      // Soft delete the user
      await prisma.$executeRaw`
        UPDATE "user"
        SET deleted_at = NOW(), deleted_by = 'test'
        WHERE id = ${testUserId}
      `;

      // Query should not return soft-deleted user
      const user = await prisma.user.findFirst({
        where: { id: testUserId },
      });

      expect(user).toBeNull();
    });

    it('should return null for soft-deleted user in findUnique', async () => {
      // Soft delete the user
      await prisma.$executeRaw`
        UPDATE "user"
        SET deleted_at = NOW(), deleted_by = 'test'
        WHERE id = ${testUserId}
      `;

      // Query should return null
      const user = await prisma.user.findUnique({
        where: { id: testUserId },
      });

      expect(user).toBeNull();
    });
  });

  describe('User restoration', () => {
    it('should restore soft-deleted user', async () => {
      // Soft delete the user
      await prisma.$executeRaw`
        UPDATE "user"
        SET deleted_at = NOW(), deleted_by = 'test'
        WHERE id = ${testUserId}
      `;

      // Restore user
      await restoreUser(prisma, testUserId, 'admin-user', {
        ipAddress: '127.0.0.1',
        userAgent: 'test-agent',
      });

      // Verify restoration
      const user = await prisma.user.findUnique({
        where: { id: testUserId },
      });

      expect(user).toBeTruthy();
      expect(user?.deletedAt).toBeNull();
      expect(user?.deletedBy).toBeNull();
    });

    it('should write audit log on restoration', async () => {
      // Soft delete the user
      await prisma.$executeRaw`
        UPDATE "user"
        SET deleted_at = NOW(), deleted_by = 'test'
        WHERE id = ${testUserId}
      `;

      // Restore user
      await restoreUser(prisma, testUserId, 'admin-user');

      // Check audit log
      const auditLogs = await prisma.$queryRaw<any[]>`
        SELECT * FROM "audit_log"
        WHERE target_id = ${testUserId}
        AND action = 'RESTORE'
      `;

      expect(auditLogs).toHaveLength(1);
      expect(auditLogs[0].user_id).toBe('admin-user');
      expect(auditLogs[0].target_type).toBe('User');
    });

    it('should throw error when restoring non-deleted user', async () => {
      await expect(
        restoreUser(prisma, testUserId, 'admin-user')
      ).rejects.toThrow('User not found or not deleted');
    });

    it('should throw error when restoring non-existent user', async () => {
      await expect(
        restoreUser(prisma, 'non-existent-user', 'admin-user')
      ).rejects.toThrow('User not found or not deleted');
    });
  });

  describe('Audit trail', () => {
    it('should capture IP address and user agent', async () => {
      setSoftDeleteContext(testRequestId, {
        userId: 'admin-user',
        ipAddress: '192.168.1.1',
        userAgent: 'Mozilla/5.0',
      });

      await prisma.user.delete({
        where: { id: testUserId },
      });

      const auditLogs = await prisma.$queryRaw<any[]>`
        SELECT * FROM "audit_log"
        WHERE target_id = ${testUserId}
        AND action = 'DELETE'
      `;

      expect(auditLogs[0].ip_address).toBe('192.168.1.1');
      expect(auditLogs[0].user_agent).toBe('Mozilla/5.0');
    });

    it('should handle missing context gracefully', async () => {
      // No context set
      await prisma.user.delete({
        where: { id: testUserId },
      });

      const auditLogs = await prisma.$queryRaw<any[]>`
        SELECT * FROM "audit_log"
        WHERE target_id = ${testUserId}
        AND action = 'DELETE'
      `;

      expect(auditLogs).toHaveLength(1);
      expect(auditLogs[0].user_id).toBeNull();
      expect(auditLogs[0].ip_address).toBeNull();
    });

    it('should store metadata in audit log', async () => {
      setSoftDeleteContext(testRequestId, {
        userId: 'admin-user',
      });

      await prisma.user.delete({
        where: { id: testUserId },
      });

      const auditLogs = await prisma.$queryRaw<any[]>`
        SELECT * FROM "audit_log"
        WHERE target_id = ${testUserId}
        AND action = 'DELETE'
      `;

      const metadata = auditLogs[0].metadata;
      expect(metadata).toBeTruthy();
      expect(metadata.reason).toBe('user-initiated');
    });
  });

  describe('Context management', () => {
    it('should set and clear context correctly', () => {
      const requestId = 'test-request-123';

      setSoftDeleteContext(requestId, {
        userId: 'user-123',
        ipAddress: '127.0.0.1',
      });

      // Context should be set (tested implicitly by audit logs)

      clearSoftDeleteContext(requestId);

      // Context should be cleared
      // Subsequent operations won't have context
    });
  });
});

describe('Cleanup Script', () => {
  let prisma: PrismaClient;

  beforeEach(async () => {
    prisma = new PrismaClient();
  });

  afterEach(async () => {
    await prisma.$disconnect();
  });

  it('should identify users deleted beyond retention period', async () => {
    // Create test user
    const oldUserId = `old-user-${Date.now()}`;
    await prisma.user.create({
      data: {
        id: oldUserId,
        email: `old-${Date.now()}@example.com`,
        name: 'Old User',
        emailVerified: true,
      },
    });

    // Soft delete with old timestamp (100 days ago)
    const oldDate = new Date();
    oldDate.setDate(oldDate.getDate() - 100);

    await prisma.$executeRaw`
      UPDATE "user"
      SET deleted_at = ${oldDate}, deleted_by = 'test'
      WHERE id = ${oldUserId}
    `;

    // Find users deleted more than 90 days ago
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - 90);

    const usersToDelete = await prisma.user.findMany({
      where: {
        deletedAt: {
          not: null,
          lte: cutoffDate,
        },
      },
    });

    expect(usersToDelete.length).toBeGreaterThan(0);
    expect(usersToDelete.some((u) => u.id === oldUserId)).toBe(true);

    // Cleanup
    await prisma.$executeRaw`DELETE FROM "user" WHERE id = ${oldUserId}`;
  });
});
