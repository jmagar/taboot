/**
 * Taboot API Client Instance
 *
 * Configured client for the Taboot FastAPI backend.
 * Uses NEXT_PUBLIC_API_URL from environment variables.
 *
 * CSRF Protection:
 * State-changing requests (POST/PUT/PATCH/DELETE) automatically include
 * CSRF tokens via the csrfFetch wrapper. The token is retrieved from
 * the __Host-taboot.csrf cookie set by the middleware.
 */

import { TabootAPIClient } from "@taboot/api-client";
import { csrfFetch } from "./csrf-client";

/**
 * CSRF-aware API client that wraps TabootAPIClient.
 *
 * Automatically includes CSRF tokens in state-changing requests by
 * using csrfFetch instead of the default fetch.
 */
class CsrfAwareAPIClient extends TabootAPIClient {
  private getBaseUrl(): string {
    return (this as any).baseUrl;
  }

  private getCredentials(): RequestCredentials {
    return (this as any).credentials;
  }

  async get<T>(path: string, options?: RequestInit): Promise<import("@taboot/api-client").APIResponse<T>> {
    return this.requestWithCsrf<T>(path, {
      ...options,
      method: "GET",
    });
  }

  async post<T>(
    path: string,
    data?: unknown,
    options?: RequestInit,
  ): Promise<import("@taboot/api-client").APIResponse<T>> {
    return this.requestWithCsrf<T>(path, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(
    path: string,
    data?: unknown,
    options?: RequestInit,
  ): Promise<import("@taboot/api-client").APIResponse<T>> {
    return this.requestWithCsrf<T>(path, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(
    path: string,
    data?: unknown,
    options?: RequestInit,
  ): Promise<import("@taboot/api-client").APIResponse<T>> {
    return this.requestWithCsrf<T>(path, {
      ...options,
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(path: string, options?: RequestInit): Promise<import("@taboot/api-client").APIResponse<T>> {
    return this.requestWithCsrf<T>(path, {
      ...options,
      method: "DELETE",
    });
  }

  private async requestWithCsrf<T>(
    path: string,
    options?: RequestInit,
  ): Promise<import("@taboot/api-client").APIResponse<T>> {
    const url = `${this.getBaseUrl()}${path}`;

    try {
      // Use csrfFetch which automatically adds CSRF token header
      const response = await csrfFetch(url, {
        ...options,
        credentials: this.getCredentials(),
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...options?.headers,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        const error = data && "error" in data && data.error
          ? data.error
          : response.statusText || "Request failed";

        throw new Error(error);
      }

      return data;
    } catch (error) {
      throw error;
    }
  }
}

/**
 * Singleton API client instance.
 *
 * Configuration:
 * - baseUrl: NEXT_PUBLIC_API_URL (defaults to http://localhost:8000)
 * - credentials: 'include' (required for JWT cookies)
 * - CSRF protection: Automatic token inclusion for POST/PUT/PATCH/DELETE
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
export const api = new CsrfAwareAPIClient({
  baseUrl: process.env.NEXT_PUBLIC_API_URL,
  credentials: "include", // Required for JWT cookies
});
