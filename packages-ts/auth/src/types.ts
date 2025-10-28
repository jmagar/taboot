/**
 * Session data structure returned by Better Auth.
 * This is the same type as auth.$Infer.Session from server.ts
 */
export interface Session {
  user: {
    id: string;
    email?: string;
    name?: string;
    emailVerified?: boolean;
    image?: string;
    createdAt?: Date;
    updatedAt?: Date;
  };
  session: {
    id: string;
    userId: string;
    expiresAt: Date;
    ipAddress?: string;
    userAgent?: string;
    createdAt?: Date;
  };
}

/**
 * JWT payload structure for session tokens.
 * Used for edge-compatible session validation.
 */
export interface SessionTokenPayload {
  userId: string;
  sessionId: string;
  exp: number;
  iat?: number;
  [key: string]: unknown;
}
