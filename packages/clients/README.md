# Packages / Clients

Generated client SDKs that talk to the LlamaCrawl API surfaces. Keep this
package free of handwritten business logic—treat it as output from generators.

## Layout

```
packages/clients/
├── README.md
├── python/          # Generated Python client package (pydantic / httpx)
├── typescript/      # Generated TypeScript client package
└── scripts/         # Generation scripts (openapi, post-processing)
```

## Key docs

- [`apps/api/openapi.yaml`](../../apps/api/openapi.yaml) – source of truth for the
  REST schema.
- [`docs/MAKEFILE_REFERENCES.md`](../../docs/MAKEFILE_REFERENCES.md) – contains
  automation targets for regenerating clients.
- [`apps/api/docs/API.md`](../../apps/api/docs/API.md) – explains endpoint
  behaviour and payloads.

## Generation workflow

1. Ensure `apps/api/openapi.yaml` reflects the latest changes (run the API tests
   and regenerate the spec if needed).
2. From the repository root, use the documented targets:

   ```bash
   # TypeScript
   npx openapi-typescript apps/api/openapi.yaml -o packages/clients/typescript/index.ts

   # Python
   openapi-python-client generate --path apps/api/openapi.yaml --output packages/clients/python
   ```

   (Wire these commands into `packages/clients/scripts/` as automation evolves.)
3. Commit regenerated sources alongside the OpenAPI diff and note the generation
   commands in the PR description.

## Publishing

Document publishing steps once we release to PyPI/npm. For now, generated
clients should be consumed directly from the repository or packaged locally as
part of downstream deployments.
