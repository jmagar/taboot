/**
 * Typed API Client with Zod Validation
 *
 * Wraps the base API client with runtime type validation using Zod schemas.
 * All requests and responses are validated against their schemas, ensuring
 * type safety at runtime.
 */

import { z, ZodSchema } from 'zod';
import { api } from './api';

export class ValidationError extends Error {
  constructor(
    message: string,
    public errors: z.ZodError,
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}

export interface TypedRequestOptions<TRequest> {
  path: string;
  requestSchema?: ZodSchema<TRequest>;
  responseSchema: ZodSchema<unknown>;
  data?: TRequest;
}

export interface TypedGetOptions<TResponse> {
  path: string;
  responseSchema: ZodSchema<TResponse>;
}

/**
 * Validates data against a Zod schema and throws ValidationError if invalid.
 */
function validateSchema<T>(schema: ZodSchema<T>, data: unknown, context: string): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new ValidationError(
      `${context} validation failed: ${result.error.message}`,
      result.error,
    );
  }
  return result.data;
}

/**
 * Validates request data against schema if provided, otherwise returns data unchanged.
 */
function validateRequest<T>(
  requestSchema: ZodSchema<T> | undefined,
  data: T | undefined,
): T | undefined {
  return requestSchema && data
    ? validateSchema(requestSchema, data, 'Request')
    : data;
}

/**
 * Typed API client with automatic Zod validation.
 *
 * All API calls validate:
 * 1. Request data against request schema (if provided)
 * 2. Response data against response schema
 *
 * Throws ValidationError if validation fails.
 */
export class TypedAPIClient {
  /**
   * Perform a typed GET request with response validation.
   */
  async get<TResponse>(options: TypedGetOptions<TResponse>): Promise<TResponse> {
    const response = await api.get<TResponse>(options.path);

    if (response.error) {
      throw new Error(response.error);
    }

    return validateSchema(options.responseSchema, response.data, 'Response');
  }

  /**
   * Perform a typed POST request with request and response validation.
   */
  async post<TRequest, TResponse>(
    options: TypedRequestOptions<TRequest>,
  ): Promise<TResponse> {
    const validatedData = validateRequest(options.requestSchema, options.data);

    const response = await api.post<TResponse>(options.path, validatedData);

    if (response.error) {
      throw new Error(response.error);
    }

    return validateSchema(options.responseSchema, response.data, 'Response') as TResponse;
  }

  /**
   * Perform a typed PUT request with request and response validation.
   */
  async put<TRequest, TResponse>(
    options: TypedRequestOptions<TRequest>,
  ): Promise<TResponse> {
    const validatedData = validateRequest(options.requestSchema, options.data);

    const response = await api.put<TResponse>(options.path, validatedData);

    if (response.error) {
      throw new Error(response.error);
    }

    return validateSchema(options.responseSchema, response.data, 'Response') as TResponse;
  }

  /**
   * Perform a typed PATCH request with request and response validation.
   */
  async patch<TRequest, TResponse>(
    options: TypedRequestOptions<TRequest>,
  ): Promise<TResponse> {
    const validatedData = validateRequest(options.requestSchema, options.data);

    const response = await api.patch<TResponse>(options.path, validatedData);

    if (response.error) {
      throw new Error(response.error);
    }

    return validateSchema(options.responseSchema, response.data, 'Response') as TResponse;
  }

  /**
   * Perform a typed DELETE request with response validation.
   */
  async delete<TResponse>(options: TypedGetOptions<TResponse>): Promise<TResponse> {
    const response = await api.delete<TResponse>(options.path);

    if (response.error) {
      throw new Error(response.error);
    }

    return validateSchema(options.responseSchema, response.data, 'Response');
  }
}

// Export singleton instance
export const typedApi = new TypedAPIClient();
