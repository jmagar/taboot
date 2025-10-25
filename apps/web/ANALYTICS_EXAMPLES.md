# Analytics Usage Examples

Practical examples of using analytics in Taboot web application components.

## Authentication Examples

### Sign In Component

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { signIn } from '@taboot/auth/client';

export function SignInForm() {
  const handleSignIn = async (email: string, password: string) => {
    try {
      const result = await signIn.email({ email, password });

      if (result.data?.user) {
        // Track successful sign-in
        analytics.track(ANALYTICS_EVENTS.USER_SIGNED_IN, {
          method: 'email',
        });

        // Identify user (use hashed ID, not email!)
        analytics.identify(result.data.user.id, {
          // Safe traits (no PII)
          created_at: result.data.user.createdAt,
        });
      }
    } catch (error) {
      // Track sign-in errors
      analytics.track(ANALYTICS_EVENTS.ERROR_OCCURRED, {
        action: 'sign_in',
        error_type: error instanceof Error ? error.name : 'unknown',
      });
    }
  };

  return <form>{/* ... */}</form>;
}
```

### Sign Out Component

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { signOut } from '@taboot/auth/client';

export function SignOutButton() {
  const handleSignOut = async () => {
    // Track sign-out before clearing session
    analytics.track(ANALYTICS_EVENTS.USER_SIGNED_OUT);

    // Clear analytics session
    analytics.reset();

    await signOut();
  };

  return <button onClick={handleSignOut}>Sign Out</button>;
}
```

## Search & Query Examples

### Search Component

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { useState } from 'react';

export function SearchBar() {
  const [query, setQuery] = useState('');

  const handleSearch = async (searchQuery: string) => {
    const startTime = Date.now();

    try {
      const results = await fetch(`/api/search?q=${encodeURIComponent(searchQuery)}`);
      const data = await results.json();
      const duration = Date.now() - startTime;

      // Track successful search
      analytics.track(ANALYTICS_EVENTS.SEARCH_PERFORMED, {
        results_count: data.length,
        duration_ms: duration,
        has_results: data.length > 0,
        // DO NOT send actual query content (privacy)
      });
    } catch (error) {
      // Track search errors
      analytics.track(ANALYTICS_EVENTS.API_ERROR, {
        endpoint: '/api/search',
        error_type: error instanceof Error ? error.name : 'unknown',
      });
    }
  };

  return <input onChange={(e) => handleSearch(e.target.value)} />;
}
```

### Query Execution

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';

export function QueryEngine() {
  const executeQuery = async (query: string) => {
    const startTime = Date.now();

    try {
      const result = await runQuery(query);
      const duration = Date.now() - startTime;

      // Track query metrics (not content!)
      analytics.track(ANALYTICS_EVENTS.QUERY_EXECUTED, {
        duration_ms: duration,
        nodes_returned: result.nodes.length,
        query_type: detectQueryType(query), // e.g., 'graph_traversal', 'vector_search'
      });

      return result;
    } catch (error) {
      analytics.track(ANALYTICS_EVENTS.QUERY_FAILED, {
        error_type: error instanceof Error ? error.name : 'unknown',
        query_type: detectQueryType(query),
      });
      throw error;
    }
  };
}
```

## Document Management Examples

### Document Viewer

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { useEffect } from 'react';

export function DocumentViewer({ docId, docType }: { docId: string; docType: string }) {
  useEffect(() => {
    // Track document views
    analytics.track(ANALYTICS_EVENTS.DOCUMENT_VIEWED, {
      doc_type: docType,
      // DO NOT send doc_id if it contains sensitive info
    });
  }, [docId, docType]);

  return <div>{/* Document content */}</div>;
}
```

### Document Ingestion

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';

export function IngestDocument() {
  const handleIngest = async (file: File) => {
    const startTime = Date.now();

    try {
      const result = await ingestFile(file);
      const duration = Date.now() - startTime;

      analytics.track(ANALYTICS_EVENTS.DOCUMENT_INGESTED, {
        file_type: file.type,
        file_size_kb: Math.round(file.size / 1024),
        duration_ms: duration,
        chunks_created: result.chunks,
        // DO NOT send filename (may contain sensitive info)
      });
    } catch (error) {
      analytics.track(ANALYTICS_EVENTS.ERROR_OCCURRED, {
        action: 'document_ingest',
        file_type: file.type,
        error_type: error instanceof Error ? error.name : 'unknown',
      });
    }
  };
}
```

## Graph Visualization Examples

### Graph View

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { useEffect } from 'react';

export function GraphVisualization() {
  useEffect(() => {
    // Track graph view
    analytics.track(ANALYTICS_EVENTS.GRAPH_VIEWED);
  }, []);

  const handleNodeSelect = (nodeType: string) => {
    analytics.track(ANALYTICS_EVENTS.GRAPH_NODE_SELECTED, {
      node_type: nodeType,
      // DO NOT send node IDs or labels (may be sensitive)
    });
  };

  const handleFilterApply = (filterType: string, filterCount: number) => {
    analytics.track(ANALYTICS_EVENTS.GRAPH_FILTER_APPLIED, {
      filter_type: filterType,
      filter_count: filterCount,
    });
  };

  return <div>{/* Graph UI */}</div>;
}
```

## Settings & Preferences Examples

### Theme Switcher

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { useTheme } from 'next-themes';

export function ThemeSwitcher() {
  const { setTheme } = useTheme();

  const handleThemeChange = (newTheme: string) => {
    setTheme(newTheme);

    // Track theme changes
    analytics.track(ANALYTICS_EVENTS.THEME_CHANGED, {
      theme: newTheme,
    });

    // Update user properties
    analytics.setUserProperties({
      preferred_theme: newTheme,
    });
  };

  return <select onChange={(e) => handleThemeChange(e.target.value)} />;
}
```

### Settings Form

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';

export function SettingsForm() {
  const handleSaveSettings = async (settings: UserSettings) => {
    await saveSettings(settings);

    // Track settings updates
    analytics.track(ANALYTICS_EVENTS.SETTINGS_UPDATED, {
      // Only track which settings changed, not values
      notifications_changed: settings.notifications !== oldSettings.notifications,
      privacy_changed: settings.privacy !== oldSettings.privacy,
      display_changed: settings.display !== oldSettings.display,
    });

    // Update user properties (non-PII only)
    analytics.setUserProperties({
      notifications_enabled: settings.notifications,
      // DO NOT send email, name, or other PII
    });
  };
}
```

## Error Tracking Examples

### Global Error Boundary

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { useEffect } from 'react';
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error }: { error: Error }) {
  useEffect(() => {
    // Track errors caught by boundary
    analytics.track(ANALYTICS_EVENTS.ERROR_OCCURRED, {
      error_type: error.name,
      error_boundary: true,
      // DO NOT send error.message (may contain sensitive data)
    });
  }, [error]);

  return <div>Something went wrong</div>;
}

export function App({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback} onError={() => {}}>
      {children}
    </ErrorBoundary>
  );
}
```

### API Error Tracking

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';

export async function apiClient(endpoint: string, options?: RequestInit) {
  try {
    const response = await fetch(endpoint, options);

    if (!response.ok) {
      // Track API errors
      analytics.track(ANALYTICS_EVENTS.API_ERROR, {
        endpoint: endpoint.split('?')[0], // Remove query params
        status_code: response.status,
        method: options?.method || 'GET',
      });
    }

    return response;
  } catch (error) {
    // Track network errors
    analytics.track(ANALYTICS_EVENTS.API_ERROR, {
      endpoint: endpoint.split('?')[0],
      error_type: error instanceof Error ? error.name : 'network_error',
      method: options?.method || 'GET',
    });
    throw error;
  }
}
```

## React Hooks Examples

### Custom Analytics Hook

```typescript
'use client';

import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { useCallback } from 'react';

export function useAnalytics() {
  const trackPageView = useCallback(() => {
    analytics.page();
  }, []);

  const trackFeatureUsage = useCallback((feature: string, data?: Record<string, unknown>) => {
    analytics.track('feature_used', {
      feature,
      ...data,
    });
  }, []);

  const trackError = useCallback((error: Error, context?: string) => {
    analytics.track(ANALYTICS_EVENTS.ERROR_OCCURRED, {
      error_type: error.name,
      context,
      // DO NOT send error.message
    });
  }, []);

  return {
    trackPageView,
    trackFeatureUsage,
    trackError,
    isEnabled: analytics.isEnabled(),
  };
}
```

### Usage in Component

```typescript
'use client';

import { useAnalytics } from '@/hooks/use-analytics';

export function FeatureComponent() {
  const { trackFeatureUsage } = useAnalytics();

  const handleAction = () => {
    // Do something
    trackFeatureUsage('special_feature', {
      action: 'button_clicked',
    });
  };

  return <button onClick={handleAction}>Action</button>;
}
```

## Privacy Best Practices

### ✅ Safe to Track

```typescript
// Aggregate metrics
analytics.track('search_performed', {
  results_count: 42,
  duration_ms: 150,
});

// Feature usage
analytics.track('feature_enabled', {
  feature: 'dark_mode',
});

// UI interactions
analytics.track('button_clicked', {
  button_id: 'submit',
  section: 'settings',
});

// Generic types
analytics.track('document_viewed', {
  doc_type: 'pdf',
  file_size_kb: 1024,
});
```

### ❌ Never Track

```typescript
// PII - Email addresses
analytics.track('user_signed_in', {
  email: 'user@example.com', // ❌ NEVER
});

// PII - Names
analytics.track('profile_updated', {
  full_name: 'John Doe', // ❌ NEVER
});

// Sensitive content
analytics.track('query_executed', {
  query: 'SELECT * FROM passwords', // ❌ NEVER
});

// Tokens or credentials
analytics.track('api_call', {
  token: 'sk-xxx', // ❌ NEVER
});

// Unredacted errors
analytics.track('error', {
  message: error.message, // ❌ MAY CONTAIN SENSITIVE DATA
});
```

## Testing Analytics

### Component Test

```typescript
import { analytics, ANALYTICS_EVENTS } from '@/lib/analytics';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock analytics
jest.mock('@/lib/analytics', () => ({
  analytics: {
    track: jest.fn(),
  },
  ANALYTICS_EVENTS: {
    USER_SIGNED_IN: 'user_signed_in',
  },
}));

describe('SignInForm', () => {
  it('tracks sign-in event', async () => {
    render(<SignInForm />);

    const button = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(button);

    expect(analytics.track).toHaveBeenCalledWith(ANALYTICS_EVENTS.USER_SIGNED_IN, {
      method: 'email',
    });
  });
});
```

## Summary

**Key Principles:**

1. **Privacy First** - Never send PII
2. **Type Safety** - Use `ANALYTICS_EVENTS` constants
3. **Graceful Degradation** - Works without credentials
4. **Aggregate Metrics** - Counts, durations, types only
5. **Generic Identifiers** - Types not IDs, categories not values

**Remember:**

- Track **what** users do, not **who** they are
- Track **patterns**, not **content**
- Track **metrics**, not **details**
