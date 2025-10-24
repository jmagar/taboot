"""initial_schema

Revision ID: 57e233e31a2a
Revises:
Create Date: 2025-10-24 02:38:43.664579

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "57e233e31a2a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Creates initial schema for Taboot platform:
    - ingestion_jobs: Track crawl/ingestion job lifecycle
    - schema_versions: Track migration versions for Neo4j/Qdrant
    """
    # Create ingestion_jobs table
    op.create_table(
        "ingestion_jobs",
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("chunks_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("job_id"),
    )

    # Create indexes for common queries
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])
    op.create_index("ix_ingestion_jobs_source_type", "ingestion_jobs", ["source_type"])
    op.create_index("ix_ingestion_jobs_created_at", "ingestion_jobs", ["created_at"])

    # Create schema_versions table for tracking Neo4j/Qdrant migrations
    op.create_table(
        "schema_versions",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("component", sa.String(length=50), nullable=False),  # "neo4j" or "qdrant"
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index for version lookups
    op.create_index("ix_schema_versions_component", "schema_versions", ["component", "version"])


def downgrade() -> None:
    """Downgrade schema.

    Drops all tables created in upgrade.
    """
    op.drop_index("ix_schema_versions_component", table_name="schema_versions")
    op.drop_table("schema_versions")

    op.drop_index("ix_ingestion_jobs_created_at", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_source_type", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
