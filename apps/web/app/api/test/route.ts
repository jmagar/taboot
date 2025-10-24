/**
 * Test API Route
 *
 * Demonstrates calling the Taboot FastAPI backend from Next.js API routes.
 * Tests CORS, credentials (JWT cookies), and error handling.
 */

import { api } from "@/lib/api";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    // Test unauthenticated endpoint
    const healthResponse = await api.get<{
      healthy: boolean;
      services?: Record<string, { status: string }>;
    }>("/health");

    if (healthResponse.error) {
      return NextResponse.json(
        {
          success: false,
          error: healthResponse.error,
        },
        { status: 500 },
      );
    }

    return NextResponse.json({
      success: true,
      message: "Successfully connected to Taboot API",
      health: healthResponse.data,
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 },
    );
  }
}
