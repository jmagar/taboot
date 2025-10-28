module.exports = {
  ...require('@taboot/jest-presets/node/jest-preset'),
  displayName: 'user-lifecycle',
  testMatch: ['<rootDir>/src/**/*.test.ts'],
  // Increase memory limit to avoid OOM
  maxWorkers: 1,
  workerIdleMemoryLimit: '512MB',
};
