import { NextResponse } from 'next/server';
import { prisma, restoreUser } from '@taboot/db';
import { auth } from '@/lib/auth';

/**
 * POST /api/admin/users/[id]/restore
 *
 * Restore a soft-deleted user account
 *
 * Requires admin role and authentication
 */
export async function POST(
  request: Request,
  { params }: { params: { id: string } }
): Promise<NextResponse> {
  try {
    // Get authenticated session
    const session = await auth();

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // TODO: Add admin role check
    // For now, require authenticated user
    // In production, add: if (!session.user.role?.includes('admin'))

    const userId = params.id;

    // Find the soft-deleted user
    const user = await prisma.user.findUnique({
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

    if (!user.deletedAt) {
      return NextResponse.json(
        { error: 'User is not deleted' },
        { status: 400 }
      );
    }

    // Get request metadata for audit trail
    const ipAddress =
      request.headers.get('x-forwarded-for') ||
      request.headers.get('x-real-ip') ||
      undefined;
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
  request: Request,
  { params }: { params: { id: string } }
): Promise<NextResponse> {
  try {
    // Get authenticated session
    const session = await auth();

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // TODO: Add admin role check
    // For now, require authenticated user

    const userId = params.id;

    // Find the soft-deleted user
    const user = await prisma.user.findUnique({
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
