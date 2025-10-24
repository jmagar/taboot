import { auth } from '@taboot/auth';
import { prisma } from '@taboot/db';
import { passwordSchema } from '@taboot/utils';
import { logger } from '@/lib/logger';
import { NextResponse } from 'next/server';

export async function GET(req: Request) {
  try {
    const session = await auth.api.getSession({ headers: req.headers });
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Check if user has a password in their account
    const account = await prisma.account.findFirst({
      where: {
        userId: session.user.id,
        providerId: 'credential',
      },
      select: {
        password: true,
      },
    });

    const hasPassword = !!account?.password;

    return NextResponse.json({ hasPassword });
  } catch (error) {
    logger.error('Error checking password status', { error });
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const session = await auth.api.getSession({ headers: req.headers });
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    let newPasswordRaw: unknown;
    try {
      const body = await req.json();
      if (!body || typeof body !== 'object') {
        logger.warn('Password request body is not an object');
        return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
      }
      newPasswordRaw = (body as { newPassword?: unknown }).newPassword;
    } catch (parseError) {
      logger.warn('Invalid password request payload', { error: parseError });
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }

    if (typeof newPasswordRaw !== 'string') {
      return NextResponse.json(
        { error: 'Password must be provided as a string' },
        { status: 400 },
      );
    }

    const validation = passwordSchema.safeParse(newPasswordRaw);
    if (!validation.success) {
      return NextResponse.json(
        { error: 'Password must be 8-100 characters long' },
        { status: 400 },
      );
    }
    const newPassword = validation.data;

    // Check if user already has a credential account with password
    const existingAccount = await prisma.account.findFirst({
      where: {
        userId: session.user.id,
        providerId: 'credential',
      },
    });

    if (existingAccount?.password) {
      return NextResponse.json(
        {
          error: 'Password already exists. Please use change password instead.',
        },
        { status: 400 },
      );
    }

    const result = await auth.api.setPassword({
      body: { newPassword },
      headers: req.headers,
    });

    if (!result.status) {
      return NextResponse.json({ error: 'Failed to set password' }, { status: 400 });
    }

    return NextResponse.json({ message: 'Password set successfully' });
  } catch (error) {
    logger.error('Error setting password', { error });
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
