"""PropertyGraphIndex implementation over Neo4j."""

from llama_index.core import PropertyGraphIndex
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore


def create_graph_index(
    neo4j_uri: str, username: str, password: str, database: str = "neo4j"
) -> PropertyGraphIndex:
    """
    Create PropertyGraphIndex backed by Neo4j.

    Args:
        neo4j_uri: Neo4j connection URI
        username: Neo4j username
        password: Neo4j password
        database: Neo4j database name

    Returns:
        PropertyGraphIndex instance
    """
    # Create Neo4j graph store
    graph_store = Neo4jPropertyGraphStore(
        url=neo4j_uri, username=username, password=password, database=database
    )

    # Create property graph index
    index = PropertyGraphIndex.from_existing(property_graph_store=graph_store)

    return index
