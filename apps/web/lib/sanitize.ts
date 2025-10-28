/**
 * Error message sanitization utilities
 *
 * This module provides functions to redact sensitive information from error messages
 * before they are logged or displayed to users. It aims to balance security (redacting
 * actual secrets) with debuggability (preserving legitimate technical data).
 */

/**
 * Sanitizes error messages by redacting sensitive information patterns.
 *
 * Trade-offs and Pattern Design:
 *
 * 1. **Email Pattern**: `\S+@\S+\.\S+`
 *    - Conservative: captures most email formats
 *    - Low false positive rate (@ is rare in non-email contexts)
 *
 * 2. **Bearer Token Pattern**: `Bearer\s+[\w._-]+`
 *    - Expanded to include dots and underscores (common in JWTs)
 *    - Very low false positive rate (requires "Bearer" prefix)
 *    - Context-aware: only redacts when "Bearer" keyword present
 *
 * 3. **Session ID Pattern**: `(session[_-]?id|sid)[=:]\s*[\w-]+`
 *    - Context-aware: requires key-value syntax (= or :)
 *    - Matches common session ID formats in logs and URLs
 *    - Low false positive rate due to required prefix
 *
 * 4. **Long Hex Pattern**: `\b[0-9a-f]{32,}\b` (lowercase only)
 *    - Requires 32+ chars to avoid matching short hashes (e.g., colors, short IDs)
 *    - Word boundary (\b) prevents matching hex within larger strings
 *    - Case-sensitive (lowercase only) to avoid false positives with uppercase base64
 *    - **Known limitation**: May redact legitimate long hex strings (checksums, UUIDs)
 *    - Trade-off: security over debuggability for long hex sequences
 *
 * 5. **Long Base64 Pattern**: `[A-Za-z0-9+/]{40,}(?:={1,2})?(?=\s|$|\W)`
 *    - Requires 40+ chars to avoid matching short encoded strings
 *    - Matches optional padding (1-2 '=' chars) as part of redaction
 *    - Lookahead ensures match ends at whitespace, string end, or non-word char
 *    - **Known limitation**: May redact legitimate long base64 (encoded images, checksums)
 *    - Trade-off: security over debuggability for long base64 sequences
 *
 * **When to adjust patterns:**
 * - If legitimate hex checksums are being redacted, consider requiring more context
 *   (e.g., only redact when preceded by "token", "secret", "key")
 * - If legitimate base64 is being redacted, consider increasing min length or
 *   requiring context markers
 *
 * @param message - The error message to sanitize
 * @returns Sanitized error message with sensitive data replaced by [REDACTED]
 *
 * @example
 * ```ts
 * sanitizeErrorMessage("User user@example.com failed auth")
 * // Returns: "User [REDACTED] failed auth"
 *
 * sanitizeErrorMessage("Invalid token: Bearer eyJhbGciOiJIUzI1Ni...")
 * // Returns: "Invalid token: Bearer [REDACTED]"
 *
 * sanitizeErrorMessage("Checksum: abc123def456...")  // 32+ hex chars
 * // Returns: "Checksum: [REDACTED]"
 * ```
 */
export function sanitizeErrorMessage(message: string): string {
  if (!message || typeof message !== 'string') {
    return message;
  }

  let sanitized = message;

  // Pattern 1: Email addresses (low false positive rate)
  sanitized = sanitized.replace(/\S+@\S+\.\S+/gi, '[REDACTED]');

  // Pattern 2: Bearer tokens (context-aware, very low false positive rate)
  // Expanded to include dots and underscores common in JWTs
  // Preserve case of "Bearer" keyword using callback
  //
  // Note: Bearer tokens are expected to be base64/JWTs. An email inside a Bearer value
  // (e.g., "Bearer user@example.com") is not a realistic token case, but the email will
  // still be redacted by Pattern 1 (email rule) before this pattern runs.
  //
  // Pattern execution order is intentional:
  // 1. Email → 2. Bearer → 3. Session → 4. Hex → 5. Base64
  // This ensures emails are redacted regardless of context, including edge cases like
  // "Failed for user@example.com with Bearer abc123" (email redacted, Bearer token preserved)
  sanitized = sanitized.replace(
    /(Bearer)\s+([\w._-]+)/gi,
    (match, bearer) => `${bearer} [REDACTED]`
  );

  // Pattern 3: Session IDs (context-aware, requires key-value syntax)
  sanitized = sanitized.replace(
    /(session[_-]?id|sid)[=:]\s*[\w-]+/gi,
    '$1=[REDACTED]'
  );

  // Pattern 4: Long hex strings (32+ chars, lowercase only)
  // Trade-off: May redact legitimate checksums/UUIDs for security
  // Word boundaries prevent matching hex within larger strings
  // Case-sensitive to avoid false positives with uppercase base64 strings
  // Note: UUIDs containing dashes (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) are preserved
  // intentionally so request/trace identifiers remain usable in logs.
  sanitized = sanitized.replace(/\b[0-9a-f]{32,}\b/g, '[REDACTED]');

  // Pattern 5: Long base64 strings (40+ chars)
  // Trade-off: May redact legitimate encoded data for security
  // Matches 40+ base64 chars, optionally followed by 1-2 '=' padding chars
  // Uses lookahead to ensure we're at a word boundary after optional padding
  sanitized = sanitized.replace(/[A-Za-z0-9+/]{40,}(?:={1,2})?(?=\s|$|\W)/g, '[REDACTED]');

  return sanitized;
}

/**
 * Sanitizes an Error object by redacting sensitive information from its message.
 *
 * @param error - The Error object to sanitize
 * @returns A new Error with sanitized message (preserves stack trace)
 *
 * @example
 * ```ts
 * try {
 *   throw new Error("Auth failed for user@example.com");
 * } catch (err) {
 *   const sanitized = sanitizeError(err);
 *   console.log(sanitized.message); // "Auth failed for [REDACTED]"
 * }
 * ```
 */
export function sanitizeError(error: Error): Error {
  const sanitized = new Error(sanitizeErrorMessage(error.message));
  sanitized.stack = error.stack;
  sanitized.name = error.name;
  return sanitized;
}
