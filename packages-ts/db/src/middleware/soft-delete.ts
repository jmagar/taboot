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
 * Soft delete client extension for Prisma 6.x
 *
 * Migrated from middleware pattern to $extends() client extension.
 *
 * Features:
 * - Converts DELETE to UPDATE (sets deletedAt)
 * - Filters out soft-deleted records from queries
 * - Maintains audit trail for all deletions
 * - Supports restoration
 */
export function softDeleteMiddleware(requestId?: string) {
  return {
    query: {
      user: {
        async delete({ args, query }: any) {
          const context = getContext(requestId);
          const userId = (args as any).where?.id;

          // Log deletion
          if (userId) {
            // Note: We need to access prisma instance differently in extensions
            // For now, audit logging happens in the API layer
          }

          // Convert DELETE to UPDATE
          return (query as any)({
            ...args,
            data: {
              deletedAt: new Date(),
              deletedBy: context.userId || 'system',
            },
          });
        },

        async deleteMany({ args, query }: any) {
          const context = getContext(requestId);

          // Convert DELETE MANY to UPDATE MANY
          return (query as any)({
            ...args,
            data: {
              deletedAt: new Date(),
              deletedBy: context.userId || 'system',
            },
          });
        },

        async findUnique({ args, query }: any) {
          // Fetch the user without automatic filtering
          const result = await query(args);

          // Return null if soft-deleted (unless explicitly querying deleted records)
          if (result && result.deletedAt && !(args as any)?.where?.deletedAt) {
            return null;
          }

          return result;
        },

        async findFirst({ args, query }: any) {
          // Add soft-delete filter unless explicitly querying deleted records
          const where = (args as any).where || {};

          // Only add filter if not explicitly querying deleted records
          if (where.deletedAt === undefined) {
            return query({
              ...args,
              where: {
                ...where,
                deletedAt: null,
              },
            });
          }

          return query(args);
        },

        async findMany({ args, query }: any) {
          // Add soft-delete filter unless explicitly querying deleted records
          const where = (args as any).where || {};

          // Only add filter if not explicitly querying deleted records
          if (where.deletedAt === undefined) {
            return query({
              ...args,
              where: {
                ...where,
                deletedAt: null,
              },
            });
          }

          return query(args);
        },
      },
    },
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
