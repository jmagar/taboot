import { Prisma } from '../generated/prisma';

/**
 * Context for tracking current user during operations
 */
interface SoftDeleteContext {
  userId?: string;
  ipAddress?: string;
  userAgent?: string;
}

// Global context storage (should be set by auth middleware)
const contextStore = new Map<string, SoftDeleteContext>();

/**
 * Set current user context for soft delete operations
 */
export function setSoftDeleteContext(requestId: string, context: SoftDeleteContext): void {
  contextStore.set(requestId, context);
}

/**
 * Get current user context
 */
function getContext(requestId?: string): SoftDeleteContext {
  if (!requestId) {
    return {};
  }
  return contextStore.get(requestId) || {};
}

/**
 * Clear context after request completes
 */
export function clearSoftDeleteContext(requestId: string): void {
  contextStore.delete(requestId);
}

/**
 * Log audit trail for data operations
 *
 * SECURITY: Uses raw SQL to avoid middleware recursion.
 * SQL injection protection is provided by:
 * 1. Prisma tagged template literals (automatic parameterization)
 * 2. JSON.stringify() serialization before parameterization
 * 3. PostgreSQL JSONB type validation
 *
 * All ${...} values are sent as query parameters ($1, $2, etc.),
 * NOT string interpolation. Verified safe by security audit.
 *
 * @see /home/jmagar/code/taboot/docs/security/AUDIT_SQL_INJECTION_AUDIT_LOG.md
 */
async function logAudit(
  prisma: any,
  params: {
    userId?: string;
    targetId: string;
    targetType: string;
    action: string;
    metadata?: Record<string, any>;
    ipAddress?: string;
    userAgent?: string;
  }
): Promise<void> {
  try {
    // Use raw query to avoid middleware recursion
    // SAFE: Prisma tagged templates use parameterized queries (not string interpolation)
    await prisma.$executeRaw`
      INSERT INTO "audit_log" (
        id, user_id, target_id, target_type, action,
        metadata, ip_address, user_agent, created_at
      ) VALUES (
        gen_random_uuid()::text,
        ${params.userId || null},
        ${params.targetId},
        ${params.targetType},
        ${params.action},
        ${params.metadata ? JSON.stringify(params.metadata) : null}::jsonb,
        ${params.ipAddress || null},
        ${params.userAgent || null},
        NOW()
      )
    `;
  } catch (error) {
    // Log error but don't fail the operation
    console.error('Failed to write audit log:', error);
  }
}

/**
 * Soft delete middleware for Prisma
 *
 * Features:
 * - Converts DELETE to UPDATE (sets deletedAt)
 * - Filters out soft-deleted records from queries
 * - Maintains audit trail for all deletions
 * - Supports restoration
 */
export function softDeleteMiddleware(requestId?: string): Prisma.Middleware {
  return async (params, next) => {
    const context = getContext(requestId);

    // Convert DELETE to UPDATE (set deletedAt)
    if (params.model === 'User' && params.action === 'delete') {
      const userId = params.args.where?.id;

      // Convert to update operation
      params.action = 'update';
      params.args.data = {
        deletedAt: new Date(),
        deletedBy: context.userId || 'system',
      };

      // Log deletion
      if (userId) {
        // Get prisma instance from the middleware context
        const prisma = (params as any).runInTransaction
          ? (params as any).runInTransaction
          : (next as any).__prismaClient;

        await logAudit(prisma, {
          userId: context.userId,
          targetId: userId,
          targetType: 'User',
          action: 'DELETE',
          metadata: {
            reason: context.userId ? 'user-initiated' : 'system-initiated',
            originalWhere: params.args.where,
          },
          ipAddress: context.ipAddress,
          userAgent: context.userAgent,
        });
      }

      return next(params);
    }

    // Convert deleteMany to updateMany
    if (params.model === 'User' && params.action === 'deleteMany') {
      params.action = 'updateMany';
      params.args.data = {
        deletedAt: new Date(),
        deletedBy: context.userId || 'system',
      };

      // Log bulk deletion
      const prisma = (params as any).runInTransaction
        ? (params as any).runInTransaction
        : (next as any).__prismaClient;

      await logAudit(prisma, {
        userId: context.userId,
        targetId: 'bulk',
        targetType: 'User',
        action: 'DELETE_MANY',
        metadata: {
          where: params.args.where,
        },
        ipAddress: context.ipAddress,
        userAgent: context.userAgent,
      });

      return next(params);
    }

    // Filter out soft-deleted records from findMany
    if (params.model === 'User' && params.action === 'findMany') {
      // Add deletedAt filter unless explicitly including deleted records
      if (!params.args) {
        params.args = {};
      }

      if (!params.args.where) {
        params.args.where = {};
      }

      // Only add filter if not explicitly querying deleted records
      if (params.args.where.deletedAt === undefined) {
        params.args.where = {
          ...params.args.where,
          deletedAt: null,
        };
      }
    }

    // Filter soft-deleted from findFirst
    if (params.model === 'User' && params.action === 'findFirst') {
      if (!params.args) {
        params.args = {};
      }

      if (!params.args.where) {
        params.args.where = {};
      }

      // Only add filter if not explicitly querying deleted records
      if (params.args.where.deletedAt === undefined) {
        params.args.where = {
          ...params.args.where,
          deletedAt: null,
        };
      }
    }

    // Filter soft-deleted from findUnique
    if (params.model === 'User' && params.action === 'findUnique') {
      const result = await next(params);

      // Return null if soft-deleted (unless explicitly querying deleted records)
      if (result && result.deletedAt && !params.args?.where?.deletedAt) {
        return null;
      }

      return result;
    }

    // Pass through all other operations
    return next(params);
  };
}

/**
 * Helper function to restore a soft-deleted user
 */
export async function restoreUser(
  prisma: any,
  userId: string,
  restoredBy: string,
  context?: Pick<SoftDeleteContext, 'ipAddress' | 'userAgent'>
): Promise<void> {
  // Get the deleted user (bypass soft delete filter)
  const user = await prisma.user.findUnique({
    where: { id: userId, deletedAt: { not: null } },
  });

  if (!user || !user.deletedAt) {
    throw new Error('User not found or not deleted');
  }

  // Restore user
  await prisma.user.update({
    where: { id: userId },
    data: {
      deletedAt: null,
      deletedBy: null,
    },
  });

  // Log restoration
  await logAudit(prisma, {
    userId: restoredBy,
    targetId: userId,
    targetType: 'User',
    action: 'RESTORE',
    metadata: {
      originalDeletedAt: user.deletedAt,
      originalDeletedBy: user.deletedBy,
    },
    ipAddress: context?.ipAddress,
    userAgent: context?.userAgent,
  });
}
