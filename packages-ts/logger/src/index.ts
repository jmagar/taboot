type LogLevel = 'info' | 'warn' | 'error';

type LogMeta = Record<string, unknown> | undefined;

function serializeMeta(meta: LogMeta): Record<string, unknown> | undefined {
  if (!meta) {
    return undefined;
  }

  const entries = Object.entries(meta).map(([key, value]) => {
    if (value instanceof Error) {
      return [
        key,
        {
          name: value.name,
          message: value.message,
          stack: value.stack,
        },
      ];
    }

    return [key, value];
  });

  return Object.fromEntries(entries);
}

function log(level: LogLevel, message: string, meta?: LogMeta) {
  const consoleMethod =
    level === 'error' ? console.error : level === 'warn' ? console.warn : console.log;

  consoleMethod({
    level,
    message,
    timestamp: new Date().toISOString(),
    ...(meta ? { meta: serializeMeta(meta) } : {}),
  });
}

export const logger = {
  info(message: string, meta?: LogMeta) {
    log('info', message, meta);
  },
  warn(message: string, meta?: LogMeta) {
    log('warn', message, meta);
  },
  error(message: string, meta?: LogMeta) {
    log('error', message, meta);
  },
};

export type Logger = typeof logger;
