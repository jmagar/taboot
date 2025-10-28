/**
 * Container detection utility for Next.js
 * Matches the logic from packages/common/config/__init__.py:_is_running_in_container()
 */

import { existsSync, readFileSync } from 'fs';

/**
 * Detect if code is running inside a Docker container.
 *
 * Checks for common container indicators:
 * - /.dockerenv file (Docker)
 * - DOCKER_CONTAINER environment variable
 * - Container-specific cgroup entries
 *
 * @returns {boolean} True if running in container, False if on host
 */
export function isRunningInContainer(): boolean {
  // Check for /.dockerenv file
  if (existsSync('/.dockerenv')) {
    return true;
  }

  // Check for DOCKER_CONTAINER env var
  if (process.env.DOCKER_CONTAINER) {
    return true;
  }

  // Check cgroup for docker/containerd
  try {
    const cgroup = readFileSync('/proc/1/cgroup', 'utf8');
    return cgroup.includes('docker') || cgroup.includes('containerd');
  } catch {
    // File not found or permission error - not in container
    return false;
  }
}

/**
 * Rewrite Docker service URLs to localhost when running on host.
 *
 * When running locally (not in container), rewrites container hostnames
 * to localhost with mapped ports from docker-compose.yaml.
 *
 * @param {string} url - URL that may contain Docker service hostname
 * @returns {string} Rewritten URL if on host, original if in container
 */
export function rewriteDockerUrl(url: string): string {
  if (isRunningInContainer()) {
    return url;
  }

  // Map of Docker service hostnames to localhost ports
  const serviceMap: Record<string, string> = {
    'taboot-cache:6379': 'localhost:6379',
    'taboot-db:5432': 'localhost:5432',
    'taboot-vectors:6333': 'localhost:7000', // QDRANT_HTTP_PORT
    'taboot-graph:7687': 'localhost:7687',
    'taboot-embed:80': 'localhost:8080',
    'taboot-rerank:8000': 'localhost:8081',
    'taboot-ollama:11434': 'localhost:11434',
    'taboot-crawler:3002': 'localhost:3002',
    'taboot-playwright:3000': 'localhost:3000',
    'taboot-api:8000': 'localhost:8000',
  };

  let rewritten = url;
  for (const [dockerHost, localHost] of Object.entries(serviceMap)) {
    rewritten = rewritten.replace(dockerHost, localHost);
  }

  return rewritten;
}

/**
 * Get Redis URL with automatic localhost rewriting when not in container.
 *
 * @returns {string} Redis connection URL
 */
export function getRedisUrl(): string {
  const envUrl = process.env.REDIS_URL || process.env.REDIS_RATE_LIMIT_URL;
  const defaultUrl = 'redis://taboot-cache:6379';
  return rewriteDockerUrl(envUrl || defaultUrl);
}
