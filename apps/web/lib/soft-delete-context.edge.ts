import type { NextRequest } from 'next/server';
import type { Session } from '@taboot/auth';

/**
 * Soft delete context metadata extracted from a request.
 */
export interface SoftDeleteContextMetadata {
  requestId: string;
  userId?: string;
  ipAddress?: string;
  userAgent?: string;
}

const IPV4_PATTERN =
  /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;

// Simplified IPv6 validation that covers the common representations.
const IPV6_PATTERN =
  /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$|^[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:)?[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}::[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}::$/;

const TRUST_PROXY_HEADER = /^true$/i;

const CF_CONNECTING_IP = 'cf-connecting-ip';
const X_REAL_IP = 'x-real-ip';
const X_FORWARDED_FOR = 'x-forwarded-for';

/**
 * Validate IP address format (IPv4 or IPv6).
 */
function isValidIp(ip: string): boolean {
  return IPV4_PATTERN.test(ip) || IPV6_PATTERN.test(ip);
}

/**
 * Extracts a trusted client IP address from a Next.js request.
 */
function getClientIp(request: NextRequest): string | undefined {
  const trustProxy = TRUST_PROXY_HEADER.test(process.env.TRUST_PROXY ?? '');

  if (trustProxy) {
    const cfIp = request.headers.get(CF_CONNECTING_IP);
    if (cfIp && isValidIp(cfIp)) {
      return cfIp;
    }

    const realIp = request.headers.get(X_REAL_IP);
    if (realIp && isValidIp(realIp)) {
      return realIp;
    }

    const xff = request.headers.get(X_FORWARDED_FOR) ?? '';
    const leftmost = xff.split(',')[0]?.trim();
    if (leftmost && isValidIp(leftmost)) {
      return leftmost;
    }
  }

  const nextReq = request as { ip?: string };
  return nextReq.ip && isValidIp(nextReq.ip) ? nextReq.ip : undefined;
}

/**
 * Generate a unique request identifier.
 */
export function generateRequestId(): string {
  return crypto.randomUUID();
}

/**
 * Extract context metadata from a request and session.
 */
export function extractContextMetadata(
  request: NextRequest,
  session: Session | null
): SoftDeleteContextMetadata {
  const requestId = generateRequestId();
  const userId = session?.user?.id;
  const ipAddress = getClientIp(request);
  const userAgent = request.headers.get('user-agent') || undefined;

  return {
    requestId,
    userId,
    ipAddress,
    userAgent,
  };
}

/**
 * Setup soft delete context for the current request.
 */
export function setupSoftDeleteContext(
  request: NextRequest,
  session: Session | null
): SoftDeleteContextMetadata {
  return extractContextMetadata(request, session);
}

export const SOFT_DELETE_REQUEST_ID_HEADER = 'x-soft-delete-request-id';
export const SOFT_DELETE_USER_ID_HEADER = 'x-soft-delete-user-id';
export const SOFT_DELETE_IP_ADDRESS_HEADER = 'x-soft-delete-ip-address';
export const SOFT_DELETE_USER_AGENT_HEADER = 'x-soft-delete-user-agent';
