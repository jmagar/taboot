import { NextRequest, NextResponse } from 'next/server';
import { isIP } from 'node:net';
import { prisma, restoreUser } from '@taboot/db';
import { auth } from '@taboot/auth';
import { logger } from '@/lib/logger';

/**
 * Validate IP address format (IPv4 or IPv6).
 * Uses Node.js built-in validator for comprehensive IPv4/IPv6 support
 * including IPv6-mapped IPv4 addresses and all valid formats.
 * @param ip - IP address string to validate
 * @returns true if valid IPv4 or IPv6 address
 */
function isValidIp(ip: string): boolean {
  return isIP(ip) !== 0;
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
 * POST /api/admin/users/[id]/restore
 *
 * Restore a soft-deleted user account
 *
 * Requires admin role and authentication
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  // Await params in Next.js 15+
  const { id } = await params;
  try {
    // Get authenticated session
    const session = await auth();

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Admin authorization check (single-user system: allow first user or env-configured admin)
    const adminUserId = process.env.ADMIN_USER_ID;
    if (!adminUserId) {
      logger.error('ADMIN_USER_ID not configured for restore operation');
      return NextResponse.json(
        { error: 'Service not configured' },
        { status: 503 }
      );
    }

    if (session.user.id !== adminUserId) {
      logger.warn('Unauthorized restore attempt', {
        attemptedBy: session.user.id,
        targetUser: id,
      });
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    const userId = id;

    // Find the soft-deleted user (using findFirst since deletedAt is not unique)
    const user = await prisma.user.findFirst({
      where: {
        id: userId,
        deletedAt: { not: null },
      },
    });

    if (!user) {
      return NextResponse.json(
        { error: 'User not found or not deleted' },
        { status: 404 }
      );
    }

    // Get request metadata for audit trail with safe proxy header handling
    const ipAddress = getClientIp(request);
    const userAgent = request.headers.get('user-agent') || undefined;

    // Restore the user
    await restoreUser(prisma, userId, session.user.id, {
      ipAddress,
      userAgent,
    });

    return NextResponse.json({
      success: true,
      message: 'User restored successfully',
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
      },
    });
  } catch (error) {
    console.error('Error restoring user:', error);

    return NextResponse.json(
      {
        error: 'Failed to restore user',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

/**
 * GET /api/admin/users/[id]/restore
 *
 * Get soft-deleted user information
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  // Await params in Next.js 15+
  const { id } = await params;
  try {
    // Get authenticated session
    const session = await auth();

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Admin authorization check (single-user system: allow first user or env-configured admin)
    const adminUserId = process.env.ADMIN_USER_ID;
    if (!adminUserId) {
      logger.error('ADMIN_USER_ID not configured for restore operation');
      return NextResponse.json(
        { error: 'Service not configured' },
        { status: 503 }
      );
    }

    if (session.user.id !== adminUserId) {
      logger.warn('Unauthorized restore attempt', {
        attemptedBy: session.user.id,
        targetUser: id,
      });
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    const userId = id;

    // Find the soft-deleted user (using findFirst since deletedAt is not unique)
    const user = await prisma.user.findFirst({
      where: {
        id: userId,
        deletedAt: { not: null },
      },
      select: {
        id: true,
        email: true,
        name: true,
        deletedAt: true,
        deletedBy: true,
        createdAt: true,
        _count: {
          select: {
            sessions: true,
            accounts: true,
            twofactors: true,
          },
        },
      },
    });

    if (!user) {
      return NextResponse.json(
        { error: 'User not found or not deleted' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        deletedAt: user.deletedAt,
        deletedBy: user.deletedBy,
        createdAt: user.createdAt,
        relatedRecords: {
          sessions: user._count.sessions,
          accounts: user._count.accounts,
          twoFactors: user._count.twofactors,
        },
      },
    });
  } catch (error) {
    console.error('Error fetching deleted user:', error);

    return NextResponse.json(
      {
        error: 'Failed to fetch user',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
