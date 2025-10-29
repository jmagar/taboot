/**
 * Taboot API Client
 *
 * Type-safe HTTP client for the Taboot FastAPI backend.
 * Handles authentication (JWT cookies), CORS, and error handling.
 */

export interface APIErrorResponse {
  data: null;
  error: string;
}

export interface APISuccessResponse<T> {
  data: T;
  error: null;
}

export type APIResponse<T> = APISuccessResponse<T> | APIErrorResponse;

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: unknown,
  ) {
    super(message);
    this.name = "APIError";
  }
}

export interface APIClientConfig {
  baseUrl: string;
  credentials?: RequestCredentials;
}

/**
 * Type-safe API client for Taboot backend.
 *
 * Features:
 * - Automatic JSON serialization/deserialization
 * - JWT cookie handling (credentials: 'include')
 * - Error handling with typed responses
 * - Base URL configuration from environment
 */
export class TabootAPIClient {
  private readonly baseUrl: string;
  private readonly credentials: RequestCredentials;

  constructor(config?: Partial<APIClientConfig>) {
    this.baseUrl = config?.baseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:4209";
    this.credentials = config?.credentials || "include"; // Required for JWT cookies
  }

  /**
   * Perform HTTP request with automatic error handling.
   */
  private async request<T>(
    path: string,
    options?: RequestInit,
  ): Promise<APIResponse<T>> {
    const url = `${this.baseUrl}${path}`;

    try {
      const response = await fetch(url, {
        ...options,
        credentials: this.credentials,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...options?.headers,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        // FastAPI returns {data: null, error: "message"} for errors
        if (data && "error" in data && data.error) {
          throw new APIError(data.error, response.status, data);
        }
        throw new APIError(
          response.statusText || "Request failed",
          response.status,
          data,
        );
      }

      return data as APIResponse<T>;
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      throw new APIError(
        error instanceof Error ? error.message : "Unknown error",
        0,
        error,
      );
    }
  }

  /**
   * GET request.
   */
  async get<T>(path: string, options?: RequestInit): Promise<APIResponse<T>> {
    return this.request<T>(path, {
      ...options,
      method: "GET",
    });
  }

  /**
   * POST request.
   */
  async post<T>(
    path: string,
    data?: unknown,
    options?: RequestInit,
  ): Promise<APIResponse<T>> {
    return this.request<T>(path, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request.
   */
  async put<T>(
    path: string,
    data?: unknown,
    options?: RequestInit,
  ): Promise<APIResponse<T>> {
    return this.request<T>(path, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PATCH request.
   */
  async patch<T>(
    path: string,
    data?: unknown,
    options?: RequestInit,
  ): Promise<APIResponse<T>> {
    return this.request<T>(path, {
      ...options,
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request.
   */
  async delete<T>(path: string, options?: RequestInit): Promise<APIResponse<T>> {
    return this.request<T>(path, {
      ...options,
      method: "DELETE",
    });
  }
}

// Export a default instance
export const api = new TabootAPIClient();
