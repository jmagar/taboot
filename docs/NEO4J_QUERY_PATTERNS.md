# Neo4j Knowledge Graph Query Patterns

Common query patterns for the Taboot knowledge graph. All queries use the standardized PascalCase schema.

## Temporal Queries

### Relationships Created in Time Range

```cypher
MATCH (a)-[r]->(b)
WHERE r.created_at >= '2025-10-22T00:00:00-04:00'
  AND r.created_at <= '2025-10-22T23:59:59-04:00'
RETURN a.name as source,
       type(r) as relationship,
       b.name as target,
       r.created_at as created_at
ORDER BY r.created_at DESC
```

### Relationship Timeline

```cypher
MATCH ()-[r]->()
WHERE r.created_at IS NOT NULL
WITH date(substring(r.created_at, 0, 10)) as date,
     type(r) as rel_type,
     count(*) as count
RETURN date, rel_type, count
ORDER BY date DESC, count DESC
```

### Recent Sessions (Last 7 Days)

```cypher
MATCH (i:Investigation)
WHERE any(obs IN i.observations WHERE obs CONTAINS '2025-10-')
RETURN i.name as investigation,
       [obs IN i.observations WHERE obs CONTAINS 'created_at:' | split(obs, ' | ')[1]][0] as timestamp,
       i.observations[1] as goal
ORDER BY timestamp DESC
LIMIT 10
```

### Entity Creation Timeline

```cypher
MATCH (n)
WHERE any(obs IN n.observations WHERE obs CONTAINS 'created_at:')
WITH n, [obs IN n.observations WHERE obs CONTAINS 'created_at:' | split(obs, ': ')[1]][0] as created
WITH labels(n)[0] as type, date(split(created, 'T')[0]) as date, count(*) as entities_created
RETURN type, date, entities_created
ORDER BY date DESC, entities_created DESC
```

### Modified Files Over Time

```cypher
MATCH (f:File)
WHERE any(obs IN f.observations WHERE obs CONTAINS 'modified_at:')
WITH f, [obs IN f.observations WHERE obs CONTAINS 'modified_at:' | split(obs, ' | ')[1]][0] as modified
RETURN f.name as file,
       modified as last_modified,
       size(f.observations) as total_observations
ORDER BY modified DESC
LIMIT 20
```

## Technology Analysis

### Technology Usage Over Time

```cypher
MATCH (t:Technology)<-[:USES]-(entity)
WHERE any(obs IN entity.observations WHERE obs CONTAINS 'created_at:')
WITH t, entity,
     [obs IN entity.observations WHERE obs CONTAINS 'created_at:' | split(obs, ' | ')[1]][0] as created
RETURN t.name as technology,
       count(DISTINCT entity) as total_usage,
       collect(DISTINCT labels(entity)[0]) as used_by_types,
       min(created) as first_used,
       max(created) as last_used
ORDER BY total_usage DESC
```

### Framework Dependencies

```cypher
MATCH (f:Framework)<-[:USES]-(c:Component)
OPTIONAL MATCH (c)-[:USES]->(dep)
WHERE labels(dep)[0] IN ['Library', 'Service', 'Tool']
RETURN f.name as framework,
       count(DISTINCT c) as components_using,
       collect(DISTINCT dep.name) as dependencies
ORDER BY components_using DESC
```

### Technology Versions

```cypher
MATCH (t:Technology)
WHERE any(obs IN t.observations WHERE obs CONTAINS 'version:')
WITH t, [obs IN t.observations WHERE obs CONTAINS 'version:' | split(split(obs, ' | ')[0], ': ')[1]][0] as version
RETURN t.name as technology,
       version,
       [obs IN t.observations WHERE obs CONTAINS 'usage:' | split(split(obs, ' | ')[0], ': ')[1]][0] as usage
ORDER BY t.name
```

## Developer Activity

### Developer Contribution Summary

```cypher
MATCH (d:Developer)<-[:PERFORMED_BY]-(i:Investigation)
OPTIONAL MATCH (i)-[:CONTAINS|DISCOVERED_FINDING]->(f)
WITH d, i, count(DISTINCT f) as findings
RETURN d.name as developer,
       count(DISTINCT i) as investigations,
       sum(findings) as total_findings,
       collect(DISTINCT labels(f)[0]) as finding_types
ORDER BY investigations DESC
```

### Developer Activity Timeline

```cypher
MATCH (d:Developer)<-[:PERFORMED_BY]-(i:Investigation)
WHERE any(obs IN i.observations WHERE obs CONTAINS 'created_at:')
WITH d, i, [obs IN i.observations WHERE obs CONTAINS 'created_at:' | split(obs, ' | ')[1]][0] as created
RETURN d.name as developer,
       date(split(created, 'T')[0]) as date,
       count(i) as sessions_that_day,
       collect(i.name) as investigations
ORDER BY date DESC, developer
```

### Files Modified by Developer

```cypher
MATCH (d:Developer)<-[:PERFORMED_BY]-(i:Investigation)-[:CONTAINS]->(f:Feature|Fix|Configuration)
MATCH (f)-[:MODIFIES|CREATES]->(file:File)
RETURN d.name as developer,
       file.name as file_path,
       count(DISTINCT f) as times_modified,
       collect(DISTINCT labels(f)[0]) as change_types
ORDER BY times_modified DESC, file_path
LIMIT 20
```

## Investigation Patterns

### Investigation with Full Context

```cypher
MATCH (i:Investigation)
WHERE i.name CONTAINS 'Taboot'
OPTIONAL MATCH (i)<-[:PERFORMED_BY]-(d:Developer)
OPTIONAL MATCH (i)-[:CONTAINS|DISCOVERED_FINDING]->(f)
OPTIONAL MATCH (i)-[:ON_BRANCH]->(b:Branch)
OPTIONAL MATCH (f)-[:USES]->(t:Technology)
RETURN i.name as investigation,
       d.name as developer,
       b.name as branch,
       collect(DISTINCT f.name) as findings,
       collect(DISTINCT t.name) as technologies_used
ORDER BY i.name
```

### Investigation Impact Analysis

```cypher
MATCH (i:Investigation)-[:CONTAINS]->(f)
WHERE any(obs IN f.observations WHERE obs CONTAINS 'impact:')
WITH i, f, [obs IN f.observations WHERE obs CONTAINS 'impact:' | split(split(obs, ' | ')[0], ': ')[1]][0] as impact
RETURN i.name as investigation,
       collect({finding: f.name, impact: impact}) as findings_with_impact,
       size([x IN collect(impact) WHERE x = 'high']) as high_impact_count
ORDER BY high_impact_count DESC
```

### Failed/Blocked Work

```cypher
MATCH (f:Feature|Fix|Finding)
WHERE any(obs IN f.observations WHERE obs CONTAINS 'status: blocked' OR obs CONTAINS 'status: partial')
OPTIONAL MATCH (f)-[:PART_OF]->(i:Investigation)
RETURN labels(f)[0] as type,
       f.name as item,
       i.name as investigation,
       [obs IN f.observations WHERE obs CONTAINS 'status:' | split(split(obs, ' | ')[0], ': ')[1]][0] as status
ORDER BY type, item
```

## Component Architecture

### Component Dependencies Graph

```cypher
MATCH (c:Component)-[r:USES|DEPENDS_ON]->(dep)
RETURN c.name as component,
       type(r) as relationship,
       labels(dep)[0] as dependency_type,
       dep.name as dependency
ORDER BY c.name, relationship
```

### Component Creation Timeline

```cypher
MATCH (c:Component)
WHERE any(obs IN c.observations WHERE obs CONTAINS 'created_at:')
OPTIONAL MATCH (c)<-[:IMPLEMENTS]-(f:File)
WITH c, f, [obs IN c.observations WHERE obs CONTAINS 'created_at:' | split(obs, ' | ')[1]][0] as created
RETURN c.name as component,
       created as created_at,
       collect(DISTINCT f.name) as implemented_in_files
ORDER BY created
```

### Most Connected Components (Hubs)

```cypher
MATCH (c:Component)
OPTIONAL MATCH (c)-[out]->()
OPTIONAL MATCH (c)<-[in]-()
WITH c, count(DISTINCT out) as outgoing, count(DISTINCT in) as incoming
RETURN c.name as component,
       outgoing + incoming as total_connections,
       outgoing,
       incoming
ORDER BY total_connections DESC
LIMIT 10
```

## File Analysis

### Most Modified Files

```cypher
MATCH (f:File)
WHERE any(obs IN f.observations WHERE obs CONTAINS 'modified_at:')
WITH f, [obs IN f.observations WHERE obs CONTAINS 'modified_at:'] as modifications
RETURN f.name as file,
       size(modifications) as modification_count,
       modifications[-1] as last_modification
ORDER BY modification_count DESC
LIMIT 15
```

### Files by Component

```cypher
MATCH (f:File)-[:IMPLEMENTS]->(c:Component)
RETURN c.name as component,
       collect(f.name) as files,
       size(collect(f)) as file_count
ORDER BY file_count DESC
```

### Orphaned Files (No Component Association)

```cypher
MATCH (f:File)
WHERE NOT EXISTS { (f)-[:IMPLEMENTS]->(:Component) }
RETURN f.name as orphaned_file,
       size(f.observations) as observations_count
ORDER BY f.name
```

## Decision Tracking

### Decisions and Their Impact

```cypher
MATCH (d:Decision)
OPTIONAL MATCH (d)-[:INFLUENCES]->(influenced)
OPTIONAL MATCH (d)-[:MADE_DURING]->(i:Investigation)
RETURN d.name as decision,
       i.name as investigation,
       collect(DISTINCT {type: labels(influenced)[0], name: influenced.name}) as influences,
       [obs IN d.observations WHERE obs CONTAINS 'created_at:' | split(obs, ' | ')[1]][0] as decided_at
ORDER BY decided_at DESC
```

### Alternative Decisions Considered

```cypher
MATCH (d:Decision)
WHERE any(obs IN d.observations WHERE obs CONTAINS 'alternatives:' OR obs CONTAINS 'rejected:')
RETURN d.name as decision,
       [obs IN d.observations WHERE obs CONTAINS 'rationale:' | split(split(obs, ' | ')[0], ': ')[1]][0] as rationale,
       [obs IN d.observations WHERE obs CONTAINS 'alternatives:' | split(split(obs, ' | ')[0], ': ')[1]] as alternatives
ORDER BY d.name
```

## Fulltext Search

### Search Across All Entities

```cypher
CALL db.index.fulltext.queryNodes('entity_search', 'FastAPI OR API')
YIELD node, score
RETURN labels(node)[0] as type,
       node.name as name,
       score,
       [obs IN node.observations WHERE obs CONTAINS toLower('API') | obs][0..3] as relevant_observations
ORDER BY score DESC
LIMIT 20
```

### Search by Date Range

```cypher
MATCH (n)
WHERE any(obs IN n.observations WHERE obs CONTAINS '2025-10-22')
RETURN labels(n)[0] as type,
       n.name as name,
       [obs IN n.observations WHERE obs CONTAINS '2025-10-22'][0] as matching_observation
ORDER BY type, name
```

## Graph Statistics

### Overall Graph Metrics

```cypher
MATCH (n)
OPTIONAL MATCH ()-[r]->()
RETURN count(DISTINCT n) as total_nodes,
       count(DISTINCT r) as total_relationships,
       count(DISTINCT labels(n)[0]) as unique_entity_types,
       count(DISTINCT type(r)) as unique_relationship_types
```

### Relationship Type Distribution

```cypher
MATCH ()-[r]->()
RETURN type(r) as relationship_type,
       count(*) as count
ORDER BY count DESC
```

### Entity Type Distribution

```cypher
MATCH (n)
RETURN labels(n)[0] as entity_type,
       count(*) as count,
       avg(size(n.observations)) as avg_observations
ORDER BY count DESC
```

## Advanced Patterns

### Path Between Entities

```cypher
MATCH path = shortestPath(
  (start {name: 'Investigation:Taboot Phase 5'})-[*..5]-(end {name: 'Component:QdrantClient'})
)
RETURN [node IN nodes(path) | {type: labels(node)[0], name: node.name}] as path_nodes,
       [rel IN relationships(path) | type(rel)] as relationship_types,
       length(path) as path_length
```

### Find Related Investigations

```cypher
MATCH (i1:Investigation)-[:USES|CONTAINS]->(shared)<-[:USES|CONTAINS]-(i2:Investigation)
WHERE id(i1) < id(i2)
WITH i1, i2, collect(DISTINCT shared.name) as shared_entities, count(DISTINCT shared) as shared_count
WHERE shared_count >= 2
RETURN i1.name as investigation_1,
       i2.name as investigation_2,
       shared_count,
       shared_entities
ORDER BY shared_count DESC
LIMIT 10
```

### Technology Stack for Investigation

```cypher
MATCH (i:Investigation)-[:CONTAINS|USES*1..3]->(t:Technology|Framework|Library|Language|Tool)
RETURN i.name as investigation,
       labels(t)[0] as tech_category,
       collect(DISTINCT t.name) as technologies
ORDER BY i.name
```

## Validation Queries

### Find Orphaned Nodes

```cypher
MATCH (n)
WHERE NOT EXISTS { (n)-[]-() }
RETURN labels(n)[0] as label, n.name as name
ORDER BY label, name
```

### Find Nodes Missing Temporal Tracking

```cypher
MATCH (n)
WHERE NOT any(obs IN n.observations WHERE obs CONTAINS 'created_at:' OR obs CONTAINS 'modified_at:')
RETURN labels(n)[0] as label, n.name as name, size(n.observations) as observation_count
ORDER BY label, name
LIMIT 10
```

### Find Relationships Missing Temporal Tracking

```cypher
MATCH (a)-[r]->(b)
WHERE r.created_at IS NULL
RETURN a.name as source,
       type(r) as relationship,
       b.name as target
ORDER BY source, relationship
LIMIT 10
```

### Find Duplicate Relationships

```cypher
MATCH (a)-[r]->(b)
WITH a, type(r) as rel_type, b, count(*) as cnt
WHERE cnt > 1
RETURN a.name as source, rel_type, b.name as target, cnt as duplicate_count
ORDER BY cnt DESC
```

### Verify Entity Counts

```cypher
MATCH (n)
RETURN labels(n)[0] as entity_type, count(*) as count
ORDER BY count DESC
```

**Expected Results**:
- Orphaned nodes: 0 (or only newly created entities awaiting relationships)
- Nodes missing temporal tracking: 0 (all entities MUST have timestamps)
- Relationships missing temporal tracking: 0 (all relationships MUST have `created_at`)
- Duplicate relationships: 0 (each relationship should be unique)
- Entity counts: Should match documentation expectations
