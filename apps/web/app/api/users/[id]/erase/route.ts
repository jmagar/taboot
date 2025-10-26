import { NextResponse } from 'next/server';
import { prisma } from '@taboot/db';
import { auth } from '@taboot/auth';
import { logger } from '@/lib/logger';

/**
 * Validate IP address format (IPv4 or IPv6).
 * @param ip - IP address string to validate
 * @returns true if valid IPv4 or IPv6 address
 */
function isValidIp(ip: string): boolean {
  // IPv4 regex pattern
  const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
  // IPv6 regex pattern (simplified - matches most common formats)
  const ipv6Regex = /^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;
  // IPv6 compressed format (with ::)
  const ipv6CompressedRegex = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/;

  if (ipv4Regex.test(ip)) {
    // Validate octets are 0-255
    const octets = ip.split('.').map(Number);
    return octets.every((octet) => octet >= 0 && octet <= 255);
  }

  return ipv6Regex.test(ip) || ipv6CompressedRegex.test(ip);
}

/**
 * Get client IP address from request headers with proxy support.
 *
 * SECURITY: Only trust X-Forwarded-For if behind verified reverse proxy.
 * Set TRUST_PROXY=true in production ONLY if using Cloudflare, nginx, etc.
 *
 * @param request - The incoming request
 * @returns Client IP address or undefined
 */
function getClientIp(request: Request): string | undefined {
  const trustProxy = process.env.TRUST_PROXY === 'true';

  // Only trust X-Forwarded-For if behind verified proxy
  if (trustProxy) {
    const xff = request.headers.get('x-forwarded-for') ?? '';
    const leftmost = xff.split(',')[0]?.trim();

    // Validate IP format before using
    if (leftmost && isValidIp(leftmost)) {
      return leftmost;
    }
  }

  // Fallback to X-Real-IP (also requires proxy trust)
  if (trustProxy) {
    const realIp = request.headers.get('x-real-ip');
    if (realIp && isValidIp(realIp)) {
      return realIp;
    }
  }

  return undefined;
}

/**
 * POST /api/users/[id]/erase
 *
 * GDPR Article 17: Right to Erasure
 * Immediately anonymizes all PII and deletes sensitive data
 * User can erase own account, admin can erase any account
 *
 * This is IRREVERSIBLE unlike soft delete
 */
export async function POST(
  request: Request,
  { params }: { params: { id: string } }
): Promise<NextResponse> {
  try {
    // Get authenticated session
    const session = await auth.api.getSession({
      headers: request.headers,
    });

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = params.id;
    const currentUserId = session.user.id;

    // Authorization: user can erase own account OR admin can erase any account
    const adminUserId = process.env.ADMIN_USER_ID;
    const isAdmin = currentUserId === adminUserId;
    const canErase = currentUserId === userId || isAdmin;

    if (!canErase) {
      logger.warn('Unauthorized erasure attempt', {
        attemptedBy: currentUserId,
        targetUser: userId,
      });
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    // Find the user to erase
    const userToErase = await prisma.user.findUnique({
      where: { id: userId },
      select: { id: true, email: true, name: true },
    });

    if (!userToErase) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    // Get request metadata for audit trail with safe proxy header handling
    const ipAddress = getClientIp(request);
    const userAgent = request.headers.get('user-agent') || undefined;

    // GDPR erasure: atomic transaction to ensure consistency
    await prisma.$transaction(async (tx) => {
      // 1. Anonymize user PII in the user record
      await tx.user.update({
        where: { id: userId },
        data: {
          email: `anonymized-${userId}@example.local`,
          name: 'Anonymized User',
          image: null,
          deletedAt: new Date(),
          deletedBy: currentUserId,
        },
      });

      // 2. Delete all sessions (forces re-authentication)
      await tx.session.deleteMany({
        where: { userId },
      });

      // 3. Delete all accounts (OAuth/external auth)
      await tx.account.deleteMany({
        where: { userId },
      });

      // 4. Delete all verification tokens
      await tx.verification.deleteMany({
        where: { identifier: userToErase.email },
      });

      // 5. Delete all two-factor auth entries
      await tx.twoFactor.deleteMany({
        where: { userId },
      });

      // 6. Anonymize audit log entries (keep action, remove PII)
      await tx.auditLog.updateMany({
        where: { userId },
        data: {
          ipAddress: 'anonymized',
          userAgent: 'anonymized',
          metadata: { gdpr_erased: true },
        },
      });

      // 7. Create erasure audit log entry with minimal PII
      await tx.auditLog.create({
        data: {
          userId: currentUserId,
          action: 'USER_ERASE_GDPR',
          targetType: 'user',
          targetId: userId,
          metadata: {
            timestamp: new Date().toISOString(),
            gdpr_article_17: true,
            ip_address: ipAddress ? 'present' : 'absent',
            initiatedBy: isAdmin ? 'admin' : 'self',
          },
        },
      });
    });

    logger.info('User data erased per GDPR Article 17', {
      userId,
      erasedBy: currentUserId,
      isAdmin,
    });

    return NextResponse.json({
      success: true,
      message: 'User data erased per GDPR Article 17 (Right to Erasure)',
      erasureDetails: {
        erasedAt: new Date().toISOString(),
        irreversible: true,
        completeness: {
          userPII: 'anonymized',
          sessions: 'deleted',
          oauth: 'deleted',
          verifications: 'deleted',
          mfa: 'deleted',
          auditLogs: 'pii_removed',
        },
      },
    });
  } catch (error) {
    logger.error('Error erasing user data:', {
      error: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined,
    });

    return NextResponse.json(
      {
        error: 'Failed to erase user data',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

/**
 * GET /api/users/[id]/erase
 *
 * Preview what will be erased (for confirmation UI)
 * User can preview own account erasure, admin can preview any
 */
export async function GET(
  request: Request,
  { params }: { params: { id: string } }
): Promise<NextResponse> {
  try {
    // Get authenticated session
    const session = await auth.api.getSession({
      headers: request.headers,
    });

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = params.id;
    const currentUserId = session.user.id;

    // Authorization: user can preview own erasure OR admin can preview any
    const adminUserId = process.env.ADMIN_USER_ID;
    const isAdmin = currentUserId === adminUserId;
    const canPreview = currentUserId === userId || isAdmin;

    if (!canPreview) {
      logger.warn('Unauthorized erasure preview attempt', {
        attemptedBy: currentUserId,
        targetUser: userId,
      });
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    // Fetch data that will be erased
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: {
        id: true,
        email: true,
        name: true,
        createdAt: true,
        _count: {
          select: {
            sessions: true,
            accounts: true,
            twoFactor: true,
            auditLogs: true,
          },
        },
      },
    });

    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    const auditLogEntries = await prisma.auditLog.count({
      where: { userId },
    });

    return NextResponse.json({
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt,
      },
      willBeErased: {
        pii: {
          email: user.email,
          name: user.name,
          profileImage: 'if_present',
        },
        data: {
          sessions: user._count.sessions,
          oauthAccounts: user._count.accounts,
          verificationTokens: 'will_be_deleted',
          twoFactorAuth: user._count.twoFactor,
        },
        auditTrail: {
          total: auditLogEntries,
          action: 'PII removed, action log retained for compliance',
        },
      },
      warning: 'This action is IRREVERSIBLE. All PII will be permanently anonymized.',
      gdprCompliance: 'Article 17 - Right to Erasure',
    });
  } catch (error) {
    logger.error('Error previewing erasure:', {
      error: error instanceof Error ? error.message : 'Unknown error',
    });

    return NextResponse.json(
      {
        error: 'Failed to preview erasure',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
