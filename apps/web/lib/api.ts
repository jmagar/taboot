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
 * Type-safe configuration for TabootAPIClient constructor.
 * Extracted using ConstructorParameters to ensure type safety.
 */
type TabootAPIClientConfig = ConstructorParameters<typeof TabootAPIClient>[0];

/**
 * CSRF-aware API client that wraps TabootAPIClient.
 *
 * Automatically includes CSRF tokens in state-changing requests by
 * using csrfFetch instead of the default fetch.
 */
class CsrfAwareAPIClient extends TabootAPIClient {
  private readonly _baseUrl: string;
  private readonly _credentials: RequestCredentials;

  constructor(config?: TabootAPIClientConfig) {
    super(config);
    this._baseUrl = config?.baseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    this._credentials = config?.credentials || "include";
  }

  private getBaseUrl(): string {
    return this._baseUrl;
  }

  private getCredentials(): RequestCredentials {
    return this._credentials;
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

    // Only set Content-Type for string/JSON bodies, not FormData/Blob
    const headers = new Headers(options?.headers);
    if (!headers.has("Content-Type") && options?.body) {
      const isFormDataOrBlob = options.body instanceof FormData || options.body instanceof Blob;
      if (!isFormDataOrBlob) {
        headers.set("Content-Type", "application/json");
      }
    }
    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }

    // Use csrfFetch which automatically adds CSRF token header
    const response = await csrfFetch(url, {
      ...options,
      credentials: this.getCredentials(),
      headers,
    });

    // Handle 204 No Content responses
    if (response.status === 204) {
      return {} as import("@taboot/api-client").APIResponse<T>;
    }

    // Check response content-type before calling response.json()
    const contentType = response.headers.get("content-type");
    const isJson = contentType?.includes("application/json");

    let data: import("@taboot/api-client").APIResponse<T> | { data?: string };
    if (isJson) {
      data = await response.json();
    } else {
      // For non-JSON responses, return text or empty object
      const text = await response.text();
      data = text ? { data: text } : {};
    }

    if (!response.ok) {
      const error = data && "error" in data && data.error
        ? data.error
        : response.statusText || "Request failed";

      throw new Error(error);
    }

    return data;
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
