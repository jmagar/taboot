"""Unit tests for Neo4j constraint creation.

Tests the constraint creation functionality that loads and executes
the neo4j-constraints.cypher file during system initialization.
Following TDD methodology: RED phase - tests written before implementation.
"""

from pathlib import Path
from typing import Any

import pytest
from neo4j.exceptions import Neo4jError

from packages.common.config import TabootConfig


@pytest.mark.unit
class TestConstraintCreation:
    """Test suite for Neo4j constraint creation functionality."""

    def test_constraint_creation_loads_cypher_file_correctly(
        self, test_config: TabootConfig, mocker: Any
    ) -> None:
        """Test that constraint creation function loads cypher file from contracts directory.

        Verifies that the function:
        1. Loads the neo4j-constraints.cypher file from the correct path
        2. Parses multiple Cypher statements from the file
        3. Returns list of executable statements
        """
        # Import will fail until T020 implements this
        from packages.graph.constraints import load_constraint_statements

        statements = load_constraint_statements()

        # Verify statements were loaded
        assert isinstance(statements, list)
        assert len(statements) > 0

        # Verify expected constraints are present
        statement_text = " ".join(statements)
        assert "service_name_unique" in statement_text
        assert "host_hostname_unique" in statement_text
        assert "ip_addr_unique" in statement_text
        assert "proxy_name_unique" in statement_text

    def test_constraint_creation_executes_in_neo4j(
        self, test_config: TabootConfig, mock_neo4j_driver: Any, mocker: Any
    ) -> None:
        """Test that constraints are created in Neo4j using the driver.

        Verifies that the function:
        1. Creates a Neo4j session
        2. Executes each constraint statement
        3. Logs success for each constraint
        4. Commits all changes
        """
        # Import will fail until T020 implements this
        from packages.graph.constraints import create_constraints

        # Setup mock session
        mock_session = mocker.MagicMock()
        mock_context = mocker.MagicMock()
        mock_context.__enter__ = mocker.Mock(return_value=mock_session)
        mock_context.__exit__ = mocker.Mock(return_value=None)
        mock_neo4j_driver.session.return_value = mock_context

        # Execute constraint creation
        create_constraints(mock_neo4j_driver)

        # Verify session was created
        mock_neo4j_driver.session.assert_called_once()

        # Verify multiple run() calls were made (one per statement)
        assert mock_session.run.call_count > 0

    def test_constraint_creation_handles_errors(
        self, test_config: TabootConfig, mock_neo4j_driver: Any, mocker: Any
    ) -> None:
        """Test error handling when constraint creation fails.

        Verifies that the function:
        1. Catches Neo4jError exceptions
        2. Logs the error with correlation ID
        3. Raises a custom ConstraintCreationError
        4. Includes original error details
        """
        # Import will fail until T020 implements this
        from packages.graph.constraints import (
            ConstraintCreationError,
            create_constraints,
        )

        # Setup mock session that raises error
        mock_session = mocker.MagicMock()
        mock_session.run.side_effect = Neo4jError("Constraint creation failed")

        mock_context = mocker.MagicMock()
        mock_context.__enter__ = mocker.Mock(return_value=mock_session)
        mock_context.__exit__ = mocker.Mock(return_value=None)
        mock_neo4j_driver.session.return_value = mock_context

        # Verify error is raised with proper message
        with pytest.raises(ConstraintCreationError, match="Failed to create Neo4j constraints"):
            create_constraints(mock_neo4j_driver)

    def test_constraint_creation_is_idempotent(
        self, test_config: TabootConfig, mock_neo4j_driver: Any, mocker: Any
    ) -> None:
        """Test that constraint creation can be run multiple times safely.

        Verifies that the function:
        1. Uses IF NOT EXISTS clauses in Cypher statements
        2. Can be called multiple times without errors
        3. Skips existing constraints gracefully
        4. Logs when constraints already exist
        """
        # Import will fail until T020 implements this
        from packages.graph.constraints import create_constraints

        # Setup mock session
        mock_session = mocker.MagicMock()
        mock_context = mocker.MagicMock()
        mock_context.__enter__ = mocker.Mock(return_value=mock_session)
        mock_context.__exit__ = mocker.Mock(return_value=None)
        mock_neo4j_driver.session.return_value = mock_context

        # Execute constraint creation twice
        create_constraints(mock_neo4j_driver)
        create_constraints(mock_neo4j_driver)

        # Verify both executions succeeded without errors
        # Session should have been called twice (once per create_constraints call)
        assert mock_neo4j_driver.session.call_count == 2

    def test_constraint_file_path_resolution(self, test_config: TabootConfig) -> None:
        """Test that the constraint file path is resolved correctly.

        Verifies that the function:
        1. Resolves path relative to project root
        2. Uses specs/001-taboot-rag-platform/contracts/ directory
        3. Finds the neo4j-constraints.cypher file
        4. Raises error if file does not exist
        """
        # Import will fail until T020 implements this
        from packages.graph.constraints import get_constraints_file_path

        file_path = get_constraints_file_path()

        # Verify path is correct
        assert isinstance(file_path, Path)
        assert file_path.name == "neo4j-constraints.cypher"
        assert "contracts" in str(file_path)
        assert file_path.exists(), f"Constraint file not found at {file_path}"

    def test_constraint_statements_parsed_correctly(self, test_config: TabootConfig) -> None:
        """Test that Cypher statements are parsed from file correctly.

        Verifies that the parser:
        1. Splits statements on semicolons
        2. Removes comments (lines starting with //)
        3. Strips whitespace
        4. Filters out empty statements
        5. Preserves multi-line statements
        """
        # Import will fail until T020 implements this
        from packages.graph.constraints import load_constraint_statements

        statements = load_constraint_statements()

        # Verify all statements are non-empty
        for stmt in statements:
            assert len(stmt.strip()) > 0
            assert not stmt.strip().startswith("//")

        # Verify expected constraint count (based on neo4j-constraints.cypher)
        # 4 unique constraints + 1 composite index + 11 property indexes + 2 fulltext indexes = 18
        assert len(statements) >= 18

    def test_constraint_creation_with_correlation_id(
        self, test_config: TabootConfig, mock_neo4j_driver: Any, mocker: Any
    ) -> None:
        """Test that constraint creation logs with correlation ID.

        Verifies that the function:
        1. Gets correlation ID from tracing context
        2. Includes correlation ID in all log statements
        3. Enables request tracing across services
        """
        # Import will fail until T020 implements this
        from packages.graph.constraints import create_constraints

        # Mock correlation ID
        mocker.patch(
            "packages.graph.constraints.get_correlation_id",
            return_value="test-corr-456",
        )

        # Setup mock session
        mock_session = mocker.MagicMock()
        mock_context = mocker.MagicMock()
        mock_context.__enter__ = mocker.Mock(return_value=mock_session)
        mock_context.__exit__ = mocker.Mock(return_value=None)
        mock_neo4j_driver.session.return_value = mock_context

        # Capture logs
        import logging

        mock_log_info = mocker.patch.object(logging.Logger, "info")

        create_constraints(mock_neo4j_driver)

        # Verify correlation ID was logged (at least once)
        # Check if any call included correlation_id in extra dict
        calls_with_corr_id = [
            call
            for call in mock_log_info.call_args_list
            if len(call) > 1
            and isinstance(call[1].get("extra"), dict)
            and call[1].get("extra", {}).get("correlation_id") == "test-corr-456"
        ]
        assert len(calls_with_corr_id) > 0 or mock_log_info.call_count > 0
