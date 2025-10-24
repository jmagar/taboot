"""Client adapters for external systems.

Heavy dependencies (psycopg2, requests, etc.) belong here, not in packages/common.
"""

from packages.clients.postgres_document_store import PostgresDocumentStore

__all__ = ["PostgresDocumentStore"]
