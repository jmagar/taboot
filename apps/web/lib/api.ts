/**
 * Taboot API Client Instance
 *
 * Configured client for the Taboot FastAPI backend.
 * Uses NEXT_PUBLIC_API_URL from environment variables.
 */

import { TabootAPIClient } from "@taboot/api-client";

/**
 * Singleton API client instance.
 *
 * Configuration:
 * - baseUrl: NEXT_PUBLIC_API_URL (defaults to http://localhost:8000)
 * - credentials: 'include' (required for JWT cookies)
 *
 * Usage:
 * ```typescript
 * import { api } from "@/lib/api";
 *
 * const response = await api.get("/health");
 * if (response.error) {
 *   console.error(response.error);
 * } else {
 *   console.log(response.data);
 * }
 * ```
 */
export const api = new TabootAPIClient({
  baseUrl: process.env.NEXT_PUBLIC_API_URL,
  credentials: "include", // Required for JWT cookies
});
