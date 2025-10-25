# Web App Testing

This document describes the testing infrastructure for the Taboot web application.

## Overview

The web app uses [Vitest](https://vitest.dev/) as the test framework with React Testing Library for component testing. Tests are co-located with source files using the `.test.ts` or `.test.tsx` extension.

## Running Tests

```bash
# Run tests in watch mode
pnpm --filter=web test

# Run tests once with UI
pnpm --filter=web test:ui

# Run tests with coverage
pnpm --filter=web test:coverage

# Run tests in CI mode (no watch)
pnpm --filter=web test:ci
```

## Project Structure

```
apps/web/
├── vitest.config.ts        # Vitest configuration
├── vitest.setup.ts         # Global test setup
├── test/
│   └── utils.tsx          # Testing utilities and providers
├── components/
│   └── *.test.tsx         # Component tests
├── hooks/
│   └── *.test.tsx         # Hook tests
└── lib/
    └── *.test.ts          # Library tests
```

## Configuration

### vitest.config.ts

- **Environment**: jsdom (for DOM testing)
- **Setup Files**: `vitest.setup.ts` (mocks and global configuration)
- **Coverage**: v8 provider with multiple reporters (text, JSON, HTML, lcov)
- **Path Aliases**: Configured to match TypeScript paths

### vitest.setup.ts

Global setup includes:
- `@testing-library/jest-dom` matchers
- Automatic cleanup after each test
- Next.js navigation mocks (useRouter, usePathname, useSearchParams)
- Environment variables for API URLs

## Testing Utilities

### test/utils.tsx

Provides:
- `createTestQueryClient()`: Creates a test-optimized React Query client
- `renderWithProviders()`: Wraps components in required providers (React Query, etc.)

Example usage:

```tsx
import { renderWithProviders, screen } from '@/test/utils';
import userEvent from '@testing-library/user-event';

it('should render button', () => {
  renderWithProviders(<MyComponent />);
  expect(screen.getByRole('button')).toBeInTheDocument();
});
```

## Writing Tests

### Component Tests

```tsx
import { renderWithProviders, screen } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { MyComponent } from './my-component';

describe('MyComponent', () => {
  it('should render correctly', () => {
    renderWithProviders(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('should handle user interaction', async () => {
    const user = userEvent.setup();
    renderWithProviders(<MyComponent />);

    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Clicked')).toBeInTheDocument();
  });
});
```

### Hook Tests

```tsx
import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useMyHook } from './use-my-hook';

describe('useMyHook', () => {
  it('should return expected value', () => {
    const { result } = renderHook(() => useMyHook());
    expect(result.current.value).toBe(42);
  });
});
```

### API Client Tests

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TabootAPIClient } from '@taboot/api-client';

describe('API Client', () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    global.fetch = mockFetch;
  });

  it('should make GET request', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: vi.fn(async () => ({ data: { id: 1 }, error: null })),
    });

    const client = new TabootAPIClient();
    const result = await client.get('/test');

    expect(result.data).toEqual({ id: 1 });
  });
});
```

## Mocking

### Mocking Modules

```tsx
vi.mock('@taboot/auth/client', () => ({
  useSession: vi.fn(),
  signIn: { email: vi.fn() },
}));
```

### Mocking Next.js

Next.js modules are automatically mocked in `vitest.setup.ts`:
- `useRouter()`
- `usePathname()`
- `useSearchParams()`

To customize mocks per test:

```tsx
import { vi } from 'vitest';
import { useRouter } from 'next/navigation';

const mockPush = vi.fn();
vi.mocked(useRouter).mockReturnValue({
  push: mockPush,
  // ...other methods
});
```

## Coverage

Coverage reports are generated in the `coverage/` directory:
- **HTML**: `coverage/index.html` (interactive browseable report)
- **LCOV**: `coverage/lcov.info` (for CI/CD integration)
- **JSON**: `coverage/coverage-final.json` (programmatic access)

Current coverage targets:
- Core API client: >80%
- Hooks: >80%
- Components: Focus on critical user flows

## CI/CD

Tests run automatically on pull requests via GitHub Actions (`.github/workflows/web-test.yml`).

The workflow:
1. Runs on PRs affecting `apps/web/**` or `packages-ts/**`
2. Installs dependencies with pnpm
3. Runs tests with coverage
4. Uploads coverage to Codecov

## Troubleshooting

### Tests timeout

If tests are timing out:
1. Check that all async operations use `await`
2. Use `waitFor()` with appropriate timeout for slow operations
3. Verify mocks are properly configured

### Mock not working

If mocks aren't being applied:
1. Ensure `vi.mock()` is called before imports
2. Check that module paths match exactly
3. Use `vi.clearAllMocks()` in `beforeEach()`

### Coverage issues

If coverage is not being collected:
1. Verify files are not in the `exclude` list in `vitest.config.ts`
2. Ensure tests are importing from source (not dist)
3. Check that tests are actually executing the code

## Best Practices

1. **Co-locate tests**: Place test files next to source files
2. **Use descriptive names**: Test names should clearly describe what they test
3. **Test user behavior**: Focus on user interactions, not implementation details
4. **Keep tests isolated**: Each test should be independent
5. **Mock external dependencies**: Don't make real API calls or network requests
6. **Use TypeScript**: All tests should use TypeScript with proper types
7. **Prefer `screen` queries**: Use `screen.getByRole()`, `screen.getByText()`, etc.
8. **Clean up**: Let the test framework handle cleanup automatically

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Library Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [Vitest UI](https://vitest.dev/guide/ui.html)
