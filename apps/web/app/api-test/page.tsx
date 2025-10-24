"use client";

/**
 * API Test Page
 *
 * Demonstrates calling the Taboot FastAPI backend from the browser.
 * Tests CORS, credentials (JWT cookies), and error handling.
 */

import { api } from "@/lib/api";
import { Button } from "@taboot/ui/components/button";
import { useState } from "react";

interface HealthData {
  healthy: boolean;
  services?: Record<string, { status: string }>;
}

export default function APITestPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    data?: HealthData | Record<string, unknown>;
    error?: string;
  } | null>(null);

  const testHealthEndpoint = async () => {
    setLoading(true);
    setResult(null);

    try {
      const response = await api.get<HealthData>("/health");

      if (response.error) {
        setResult({
          success: false,
          error: response.error,
        });
      } else {
        setResult({
          success: true,
          data: response.data ?? undefined,
        });
      }
    } catch (error) {
      setResult({
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const testRootEndpoint = async () => {
    setLoading(true);
    setResult(null);

    try {
      const response = await api.get<{ message: string; docs: string }>("/");

      if (response.error) {
        setResult({
          success: false,
          error: response.error,
        });
      } else {
        setResult({
          success: true,
          data: response.data ?? undefined,
        });
      }
    } catch (error) {
      setResult({
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-8">
      <div className="max-w-2xl">
        <h1 className="mb-4 text-3xl font-bold">Taboot API Test</h1>
        <p className="mb-8 text-muted-foreground">
          Test the connection between Next.js and FastAPI with CORS and
          authentication.
        </p>

        <div className="mb-8 space-y-4">
          <div>
            <h2 className="mb-2 text-xl font-semibold">Test Endpoints</h2>
            <div className="flex gap-2">
              <Button onClick={testRootEndpoint} disabled={loading}>
                Test Root (/)
              </Button>
              <Button onClick={testHealthEndpoint} disabled={loading}>
                Test Health (/health)
              </Button>
            </div>
          </div>

          {loading && (
            <div className="rounded-lg border bg-card p-4">
              <p className="text-muted-foreground">Loading...</p>
            </div>
          )}

          {result && (
            <div
              className={`rounded-lg border p-4 ${
                result.success
                  ? "border-green-500 bg-green-50 dark:bg-green-950"
                  : "border-red-500 bg-red-50 dark:bg-red-950"
              }`}
            >
              <h3 className="mb-2 font-semibold">
                {result.success ? "Success" : "Error"}
              </h3>
              {result.error && (
                <p className="text-sm text-red-700 dark:text-red-300">
                  {result.error}
                </p>
              )}
              {result.data && (
                <pre className="mt-2 overflow-auto rounded bg-black/5 p-2 text-xs dark:bg-white/5">
                  {JSON.stringify(result.data, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>

        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-2 text-lg font-semibold">Configuration</h2>
          <dl className="space-y-1 text-sm">
            <div>
              <dt className="font-medium text-muted-foreground">API URL:</dt>
              <dd className="font-mono">
                {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">
                Credentials:
              </dt>
              <dd className="font-mono">include (JWT cookies enabled)</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
