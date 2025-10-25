import { PrismaClient } from '../generated/prisma';
import { softDeleteMiddleware } from './middleware/soft-delete';

const globalForPrisma = global as unknown as { prisma: PrismaClient };

export const prisma = globalForPrisma.prisma || new PrismaClient();

// Apply soft delete middleware
prisma.$use(softDeleteMiddleware());

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;

// Re-export middleware helpers for use in API routes
export {
  softDeleteMiddleware,
  setSoftDeleteContext,
  clearSoftDeleteContext,
  restoreUser,
} from './middleware/soft-delete';
