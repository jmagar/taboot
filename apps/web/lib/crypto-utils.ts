/**
 * Cross-Runtime Cryptographic Utilities
 *
 * Provides utilities that work across both Edge and Node.js runtimes.
 * Handles the differences in available APIs between environments.
 */

/**
 * Convert a Uint8Array to a base64url-encoded string
 *
 * Uses btoa() in Edge/browser runtime (where Buffer is unavailable)
 * Falls back to Buffer.from() in Node.js runtime
 *
 * Base64url encoding:
 * - Replaces + with -
 * - Replaces / with _
 * - Removes padding (=)
 *
 * @param bytes - The bytes to encode
 * @returns A base64url-encoded string
 */
export function toBase64Url(bytes: Uint8Array): string {
  let base64: string;

  if (typeof btoa === 'function') {
    // Edge/browser runtime
    // btoa expects a binary string where each character represents a byte
    const binary = String.fromCharCode(...bytes);
    base64 = btoa(binary);
  } else {
    // Node.js runtime
    // @ts-ignore Buffer is not available in Edge runtime type definitions
    base64 = Buffer.from(bytes).toString('base64');
  }

  // Convert standard base64 to base64url format
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}
