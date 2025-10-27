const SCRUB_KEYS = new Set([
  'email',
  'password',
  'pass',
  'token',
  'access_token',
  'refresh_token',
  'authorization',
  'auth',
  'apikey',
  'key',
  'secret',
  'sessionid',
  'phone',
  'address',
  'ssn',
]);

export const scrubData = (data: unknown): unknown => {
  if (data === null || data === undefined) return data;
  if (Array.isArray(data)) return data.map((value) => scrubData(value));
  if (typeof data === 'object') {
    const input = data as Record<string, unknown>;
    const output: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(input)) {
      if (SCRUB_KEYS.has(key.toLowerCase())) {
        output[key] = '[Filtered]';
      } else {
        output[key] = scrubData(value);
      }
    }
    return output;
  }
  return data;
};

export const parseSampleRate = (value: string | undefined, fallback: number): number => {
  const parsed = Number(value ?? fallback);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(0, Math.min(1, parsed));
};

export const resolveSentryEnvironment = (): string | undefined =>
  process.env.SENTRY_ENVIRONMENT ??
  process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ??
  process.env.NEXT_PUBLIC_VERCEL_ENV ??
  process.env.VERCEL_ENV ??
  process.env.NEXT_PUBLIC_RUNTIME_ENV ??
  process.env.NODE_ENV;
