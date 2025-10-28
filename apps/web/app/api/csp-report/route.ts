import { NextRequest, NextResponse } from 'next/server';
import { logger } from '@/lib/logger';

/**
 * CSP Violation Report Endpoint
 *
 * Receives Content Security Policy violation reports from the browser
 * and logs them for security monitoring and debugging.
 *
 * This endpoint is excluded from CSRF protection (see middleware.ts csrfExcludedRoutes)
 * as it receives automated reports from the browser.
 */
export async function POST(request: NextRequest) {
  try {
    const report = await request.json();
    const cspReport = report['csp-report'];

    // Extract key violation details for easier debugging
    const violationDetails = cspReport ? {
      blockedUri: cspReport['blocked-uri'],
      violatedDirective: cspReport['violated-directive'],
      effectiveDirective: cspReport['effective-directive'],
      sourceFile: cspReport['source-file'],
      lineNumber: cspReport['line-number'],
      columnNumber: cspReport['column-number'],
      scriptSample: cspReport['script-sample'],
    } : {};

    // Log CSP violation with extracted details
    logger.warn('CSP Violation', {
      ...violationDetails,
      fullReport: report,
      userAgent: request.headers.get('user-agent'),
      timestamp: new Date().toISOString(),
    });

    // Return 204 No Content (standard response for report endpoints)
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    // Log parsing errors but still return 204 to avoid browser retries
    logger.error('Failed to parse CSP violation report', {
      error: error instanceof Error ? error.message : String(error),
    });

    return new NextResponse(null, { status: 204 });
  }
}
