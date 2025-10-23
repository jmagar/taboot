"""Neo4j constraint creation and management.

Loads and executes constraint statements from the contracts/neo4j-constraints.cypher
file during system initialization. Ensures proper unique indexes and composite indexes
are created for efficient graph traversal and data integrity.
"""

from pathlib import Path

from neo4j import Driver
from neo4j.exceptions import Neo4jError

from packages.common.logging import get_logger
from packages.common.tracing import get_correlation_id

logger = get_logger(__name__)


class ConstraintCreationError(Exception):
    """Exception raised when constraint creation fails in Neo4j.

    This error wraps underlying Neo4j errors with additional context
    about which constraint failed during initialization.
    """

    pass


def get_constraints_file_path() -> Path:
    """Get the absolute path to the neo4j-constraints.cypher file.

    Returns:
        Path: Absolute path to the constraints file.

    Raises:
        FileNotFoundError: If the constraints file does not exist.

    Example:
        >>> path = get_constraints_file_path()
        >>> print(path)
        /home/user/taboot/specs/001-taboot-rag-platform/contracts/neo4j-constraints.cypher
    """
    constraints_file = (
        Path(__file__).resolve().parent.parent.parent
        / "specs"
        / "001-taboot-rag-platform"
        / "contracts"
        / "neo4j-constraints.cypher"
    )

    if not constraints_file.exists():
        raise FileNotFoundError(f"Constraints file not found at {constraints_file}")

    return constraints_file.resolve()


def load_constraint_statements() -> list[str]:
    """Load and parse Cypher constraint statements from the constraints file.

    Reads the neo4j-constraints.cypher file, strips comments, and splits
    statements by semicolons. Filters out empty statements and whitespace.

    Returns:
        list[str]: List of executable Cypher constraint statements.

    Raises:
        FileNotFoundError: If the constraints file does not exist.

    Example:
        >>> statements = load_constraint_statements()
        >>> len(statements)
        18
        >>> "service_name_unique" in statements[0]
        True
    """
    file_path = get_constraints_file_path()

    if not file_path.exists():
        raise FileNotFoundError(f"Constraints file not found at {file_path}")

    # Read the entire file
    content = file_path.read_text(encoding="utf-8")

    # Split by lines and filter out comments
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        # Skip empty lines and comment lines
        if stripped and not stripped.startswith("//"):
            lines.append(line)

    # Join back together and split by semicolons
    cleaned_content = "\n".join(lines)
    statements = cleaned_content.split(";")

    # Strip whitespace from each statement and filter out empty ones
    result = []
    for stmt in statements:
        cleaned_stmt = stmt.strip()
        if cleaned_stmt:
            result.append(cleaned_stmt)

    return result


def create_constraints(driver: Driver) -> None:
    """Create Neo4j constraints by executing statements from the constraints file.

    Loads constraint statements and executes each one in Neo4j. Uses correlation
    IDs for tracing and JSON structured logging. Handles errors by wrapping them
    in ConstraintCreationError.

    Args:
        driver: Neo4j driver instance to use for executing statements.

    Raises:
        ConstraintCreationError: If any constraint statement fails to execute.

    Example:
        >>> from neo4j import GraphDatabase
        >>> driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        >>> create_constraints(driver)
        >>> driver.close()
    """
    correlation_id = get_correlation_id()

    logger.info(
        "Starting Neo4j constraint creation",
        extra={"correlation_id": correlation_id}
    )

    try:
        statements = load_constraint_statements()

        logger.info(
            f"Loaded {len(statements)} constraint statements",
            extra={"correlation_id": correlation_id, "statement_count": len(statements)}
        )

        with driver.session() as session:
            for i, statement in enumerate(statements, 1):
                try:
                    session.run(statement)
                    logger.info(
                        f"Executed constraint statement {i}/{len(statements)}",
                        extra={
                            "correlation_id": correlation_id,
                            "statement_number": i,
                            "total_statements": len(statements)
                        }
                    )
                except Neo4jError as e:
                    logger.error(
                        f"Failed to execute constraint statement {i}: {statement[:100]}...",
                        extra={
                            "correlation_id": correlation_id,
                            "statement_number": i,
                            "error": str(e)
                        }
                    )
                    raise ConstraintCreationError(
                        f"Failed to create Neo4j constraints: {str(e)}"
                    ) from e

        logger.info(
            "Successfully created all Neo4j constraints",
            extra={"correlation_id": correlation_id, "statement_count": len(statements)}
        )

    except FileNotFoundError as e:
        logger.error(
            f"Constraints file not found: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise ConstraintCreationError(
            f"Failed to create Neo4j constraints: {str(e)}"
        ) from e
    except ConstraintCreationError:
        # Re-raise ConstraintCreationError without wrapping
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during constraint creation: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise ConstraintCreationError(
            f"Failed to create Neo4j constraints: {str(e)}"
        ) from e


async def create_neo4j_constraints() -> None:
    """Create Neo4j constraints asynchronously (async wrapper for create_constraints).

    This async function is used by the /init endpoint and other async contexts.
    It wraps the synchronous create_constraints function in an async executor.

    Raises:
        ConstraintCreationError: If constraint creation fails.

    Example:
        >>> await create_neo4j_constraints()
    """
    from packages.graph.client import Neo4jClient

    client = Neo4jClient()
    try:
        client.connect()
        create_constraints(client.get_driver())
    finally:
        client.close()


__all__ = [
    "ConstraintCreationError",
    "get_constraints_file_path",
    "load_constraint_statements",
    "create_constraints",
    "create_neo4j_constraints",
]
