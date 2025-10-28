import { NextResponse } from 'next/server';
import { Session } from '@taboot/auth';
import { logger } from '@/lib/logger';

/**
 * Authorization result for admin operations.
 * - null: User is authorized to proceed
 * - NextResponse: User is not authorized, return this error response
 */
export type AdminAuthResult = NextResponse | null;

/**
 * Check if the current user is authorized to perform admin operations on a target user.
 *
 * Authorization logic:
 * 1. User can always operate on their own account (currentUserId === targetUserId)
 * 2. Admin can operate on any account (if ADMIN_USER_ID matches currentUserId)
 * 3. If attempting to operate on another user but ADMIN_USER_ID not configured → 503
 * 4. If attempting to operate on another user but not admin → 403
 *
 * @param session - The authenticated session
 * @param targetUserId - The user ID being operated on
 * @param operationName - Name of operation for logging (e.g., "erasure", "deletion")
 * @returns null if authorized, NextResponse with error if unauthorized
 */
export function checkAdminAuthorization(
  session: Session | null,
  targetUserId: string,
  operationName: string = 'operation'
): AdminAuthResult {
  if (!session || !session.user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const currentUserId = session.user.id;
  const adminUserId = process.env.ADMIN_USER_ID?.trim();

  // SECURITY: Fail closed on admin operations
  // If attempting to operate on another user's account but admin not configured, reject
  if (currentUserId !== targetUserId && !adminUserId) {
    logger.error(`Admin ${operationName} attempted but ADMIN_USER_ID not configured`, {
      attemptedBy: currentUserId,
      targetUser: targetUserId,
    });
    return NextResponse.json(
      { error: 'Service not configured for admin operations' },
      { status: 503 }
    );
  }

  const isAdmin = Boolean(adminUserId) && currentUserId === adminUserId;
  const canOperate = currentUserId === targetUserId || isAdmin;

  if (!canOperate) {
    logger.warn(`Unauthorized ${operationName} attempt`, {
      attemptedBy: currentUserId,
      targetUser: targetUserId,
    });
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }

  // Authorized - return null to indicate success
  return null;
}
