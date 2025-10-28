export * from './soft-delete-context.edge';
export type { SoftDeleteContextMetadata } from './soft-delete-context.edge';

import * as softDeleteEdge from './soft-delete-context.edge';

/**
 * Activate Prisma soft delete context using propagated headers.
 *
 * This runs in the Node.js runtime; dynamic imports ensure Prisma is not
 * eagerly pulled into Edge bundles.
 */
const {
  SOFT_DELETE_IP_ADDRESS_HEADER,
  SOFT_DELETE_REQUEST_ID_HEADER,
  SOFT_DELETE_USER_AGENT_HEADER,
  SOFT_DELETE_USER_ID_HEADER,
} = softDeleteEdge;

export async function applyContextFromHeaders(
  headers: Headers
): Promise<string | undefined> {
  const requestId = headers.get(SOFT_DELETE_REQUEST_ID_HEADER);
  if (!requestId) {
    return undefined;
  }

  const { setSoftDeleteContext } = await import('@taboot/db');

  setSoftDeleteContext(requestId, {
    userId: headers.get(SOFT_DELETE_USER_ID_HEADER) || undefined,
    ipAddress: headers.get(SOFT_DELETE_IP_ADDRESS_HEADER) || undefined,
    userAgent: headers.get(SOFT_DELETE_USER_AGENT_HEADER) || undefined,
  });

  return requestId;
}

/**
 * Clear the Prisma soft delete context.
 */
export async function cleanupSoftDeleteContext(requestId: string): Promise<void> {
  const { clearSoftDeleteContext } = await import('@taboot/db');
  clearSoftDeleteContext(requestId);
}
