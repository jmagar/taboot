import { config } from "./base.js";

/**
 * ESLint configuration for library packages with strict rules.
 * Suitable for sensitive code like auth, security, payment processing.
 *
 * @type {import("eslint").Linter.Config[]}
 */
export default [
  ...config,
  {
    rules: {
      // Prevent console usage in library code
      "no-console": "error",
    },
  },
];
