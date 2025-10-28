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
  if (!(bytes instanceof Uint8Array)) {
    throw new TypeError("Expected bytes to be a Uint8Array");
  }

  let base64: string;

  if (typeof btoa === 'function') {
    // Edge/browser runtime
    // btoa expects a binary string where each character represents a byte
    const chunkSize = 8192;
    const chunks: string[] = [];
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const chunk = bytes.subarray(i, i + chunkSize);
      chunks.push(String.fromCharCode(...chunk));
    }
    base64 = btoa(chunks.join(''));
  } else {
    // Node.js runtime
    // @ts-ignore Buffer is not available in Edge runtime type definitions
    if (typeof Buffer === 'undefined') {
      throw new Error('Buffer is not available in this runtime');
    }
    base64 = Buffer.from(bytes).toString('base64');
  }

  // Convert standard base64 to base64url format
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}
