import { prisma } from '../client';
import type { Account } from '../../generated/prisma';

/**
 * Check if a user has a password set for their credential account
 */
export async function checkUserHasPassword(userId: string): Promise<boolean> {
  const account = await prisma.account.findFirst({
    where: {
      userId,
      providerId: 'credential',
    },
    select: {
      password: true,
    },
  });

  return !!account?.password;
}

/**
 * Get a user's credential account if it exists
 */
export async function getUserCredentialAccount(
  userId: string,
): Promise<Pick<Account, 'id' | 'userId' | 'providerId' | 'password'> | null> {
  const account = await prisma.account.findFirst({
    where: {
      userId,
      providerId: 'credential',
    },
    select: {
      id: true,
      userId: true,
      providerId: true,
      password: true,
    },
  });

  return account;
}
