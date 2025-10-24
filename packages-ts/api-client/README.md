# @taboot/api-client

Type-safe HTTP client for the Taboot FastAPI backend.

## Features

- ✅ Type-safe request/response methods
- ✅ Automatic JWT cookie handling (credentials: 'include')
- ✅ CORS-compliant (requires backend CORS configuration)
- ✅ Error handling with typed responses
- ✅ OpenAPI type generation support

## Installation

This package is internal to the Taboot monorepo. Add it to your `package.json`:

```json
{
  "dependencies": {
    "@taboot/api-client": "workspace:*"
  }
}
```

## Usage

### Basic Usage

```typescript
import { api } from "@taboot/api-client";

// GET request
const response = await api.get("/health");
if (response.error) {
  console.error(response.error);
} else {
  console.log(response.data);
}

// POST request
const createResponse = await api.post("/ingest/web", {
  url: "https://example.com",
});
```

### Custom Configuration

```typescript
import { TabootAPIClient } from "@taboot/api-client";

const client = new TabootAPIClient({
  baseUrl: process.env.NEXT_PUBLIC_API_URL,
  credentials: "include", // Required for JWT cookies
});
```

### In Next.js App

Create a configured instance in `lib/api.ts`:

```typescript
import { TabootAPIClient } from "@taboot/api-client";

export const api = new TabootAPIClient({
  baseUrl: process.env.NEXT_PUBLIC_API_URL,
  credentials: "include",
});
```

Then use it throughout your app:

```typescript
import { api } from "@/lib/api";

export default function MyComponent() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/health").then((response) => {
      if (!response.error) {
        setData(response.data);
      }
    });
  }, []);

  return <div>{JSON.stringify(data)}</div>;
}
```

## Response Format

All responses follow the FastAPI envelope format:

```typescript
// Success
{
  data: T;
  error: null;
}

// Error
{
  data: null;
  error: string;
}
```

## Type Generation

Generate TypeScript types from the FastAPI OpenAPI schema:

1. Start the FastAPI server:
   ```bash
   docker compose up taboot-app
   ```

2. Generate types:
   ```bash
   pnpm --filter @taboot/api-client generate:types
   ```

3. Import generated types:
   ```typescript
   import type { paths } from "@taboot/api-client/types";

   // Use with client
   type HealthResponse = paths["/health"]["get"]["responses"]["200"]["content"]["application/json"];
   ```

## Environment Variables

Configure the API URL via environment variables:

```env
# .env.local (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## CORS Requirements

The FastAPI backend must have CORS configured to allow the Next.js origin:

```python
# apps/api/app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3003"],
    allow_credentials=True,  # Required for JWT cookies
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
```

## API Methods

| Method | Description |
|--------|-------------|
| `get<T>(path, options?)` | GET request |
| `post<T>(path, data?, options?)` | POST request |
| `put<T>(path, data?, options?)` | PUT request |
| `patch<T>(path, data?, options?)` | PATCH request |
| `delete<T>(path, options?)` | DELETE request |

## Error Handling

The client throws `APIError` for HTTP errors:

```typescript
import { APIError } from "@taboot/api-client";

try {
  const response = await api.get("/protected");
  if (response.error) {
    // Handle error response
  }
} catch (error) {
  if (error instanceof APIError) {
    console.error(`HTTP ${error.status}: ${error.message}`);
  }
}
```

## Authentication

The client automatically includes credentials (JWT cookies) with all requests when configured with `credentials: "include"`. This is required for authenticated endpoints.

The FastAPI backend should use JWT middleware to validate the token:

```python
from apps.api.middleware.jwt_auth import require_auth

@app.get("/protected")
async def protected_route(user: dict = Depends(require_auth)):
    return {"data": {"user": user}, "error": None}
```

## Development

Build the package:

```bash
pnpm --filter @taboot/api-client build
```

Type-check:

```bash
pnpm --filter @taboot/api-client check-types
```

Lint:

```bash
pnpm --filter @taboot/api-client lint
```
