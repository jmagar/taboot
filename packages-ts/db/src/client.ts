import { PrismaClient } from '../generated/prisma';
import { softDeleteMiddleware } from './middleware/soft-delete';

const globalForPrisma = global as unknown as { prisma: any };

const baseClient = globalForPrisma.prisma || new PrismaClient();

// Apply soft delete client extension
export const prisma = baseClient.$extends(softDeleteMiddleware());

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;

// Re-export middleware helpers for use in API routes
export {
  softDeleteMiddleware,
  setSoftDeleteContext,
  clearSoftDeleteContext,
  restoreUser,
} from './middleware/soft-delete';
