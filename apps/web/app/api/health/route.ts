import { NextResponse } from 'next/server';

/**
 * Health check endpoint for Docker health checks and monitoring.
 * Returns simple status response without authentication required.
 *
 * This endpoint is excluded from CSRF protection (see middleware.ts:115)
 */
export async function GET() {
  return NextResponse.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'taboot-web'
  });
}
