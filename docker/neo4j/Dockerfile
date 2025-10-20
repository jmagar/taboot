FROM neo4j:5.23-community

# Expose cypher-shell via the PATH so compose healthchecks can invoke it
RUN ln -sf /var/lib/neo4j/bin/cypher-shell /usr/local/bin/cypher-shell
