"""
═══════════════════════════════════════════════════════════════
 🕸️ Graph Database Service - Neo4j Implementation
═══════════════════════════════════════════════════════════════
"""

import os
from typing import List, Dict, Optional
from collections import defaultdict
from neo4j import GraphDatabase, basic_auth
from config import graph_config
from utils.logger import setup_logger

logger = setup_logger()

class GraphService:
    """
    ┌─────────────────────────────────────────────┐
    │  🕸️  Graph Database Service (Neo4j)         │
    │                                             │
    │  Backend: Neo4j AuraDB / Desktop            │
    │  Driver: Official Python Driver             │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.uri = graph_config.NEO4J_URI
        self.user = graph_config.NEO4J_USER
        self.password = graph_config.NEO4J_PASSWORD
        self.database = getattr(graph_config, 'NEO4J_DATABASE', 'neo4j')
        
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=basic_auth(self.user, self.password)
            )
            self.driver.verify_connectivity()
            logger.info("🕸️  Connected to Neo4j successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            raise e

    def close(self):
        """Close Neo4j driver connection"""
        if self.driver:
            self.driver.close()

    def add_extraction_result(self, extraction_result: Dict, file_id: str):
        """
        Add entities and relationships from extraction result
        Uses atomic transactions for consistency.
        """
        entities = extraction_result.get('entities', [])
        relationships = extraction_result.get('relationships', [])
        chunk_id = extraction_result.get('chunk_id', 'unknown')
        
        if not entities and not relationships:
            return

        logger.info(
            f"📥 Adding to Neo4j: {len(entities)} entities, "
            f"{len(relationships)} relationships"
        )
        
        # 1. Prepare Nodes (Group by Type)
        nodes_by_type = defaultdict(list)
        for entity in entities:
            # Add metadata
            entity['file_id'] = file_id
            entity['chunk_id'] = chunk_id # Add current chunk to source_chunks logic
            nodes_by_type[entity.get('type', 'Unknown')].append(entity)

        # 2. Prepare Relationships (Group by Type)
        rels_by_type = defaultdict(list)
        for rel in relationships:
            rel['file_id'] = file_id
            rel['chunk_id'] = chunk_id
            rels_by_type[rel.get('type', 'RELATED_TO')].append(rel)

        # 3. Execute Writes
        with self.driver.session(database=self.database) as session:
            # Write Nodes
            for node_type, nodes in nodes_by_type.items():
                session.execute_write(self._create_nodes_tx, node_type, nodes)
            
            # Write Relationships
            for rel_type, rels in rels_by_type.items():
                session.execute_write(self._create_rels_tx, rel_type, rels)
                
    @staticmethod
    def _create_nodes_tx(tx, node_type, nodes):
        """Transaction function to create nodes"""
        query = f"""
        UNWIND $batch AS row
        MERGE (n:`{node_type}` {{id: row.id}})
        ON CREATE SET 
            n.name = row.name,
            n.description = row.description,
            n.file_id = row.file_id,
            n.created_at = timestamp(),
            n.source_chunks = [row.chunk_id]
        ON MATCH SET
            n.description = CASE 
                WHEN size(toString(row.description)) > size(toString(n.description)) 
                THEN row.description 
                ELSE n.description 
            END,
            n.source_chunks = CASE
                WHEN NOT row.chunk_id IN n.source_chunks 
                THEN n.source_chunks + row.chunk_id
                ELSE n.source_chunks
            END,
            n.updated_at = timestamp()
        """
        tx.run(query, batch=nodes)

    @staticmethod
    def _create_rels_tx(tx, rel_type, rels):
        """Transaction function to create relationships"""
        query = f"""
        UNWIND $batch AS row
        MATCH (source {{id: row.from_id}})
        MATCH (target {{id: row.to_id}})
        MERGE (source)-[r:`{rel_type}`]->(target)
        ON CREATE SET
            r.confidence = row.confidence,
            r.description = row.description,
            r.file_id = row.file_id,
            r.chunk_id = row.chunk_id,
            r.created_at = timestamp()
        ON MATCH SET
            r.confidence = CASE 
                WHEN row.confidence > r.confidence THEN row.confidence 
                ELSE r.confidence 
            END
        """
        tx.run(query, batch=rels)

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get a node by ID"""
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (n {id: $id}) RETURN n", 
                id=node_id
            ).single()
            
            if result:
                node = dict(result['n'])
                # Add implicit 'type' from labels (taking the first one usually)
                labels = list(result['n'].labels)
                node['type'] = labels[0] if labels else 'Unknown'
                return node
            return None

    def find_nodes_by_name(self, name: str, limit: int = 10) -> List[Dict]:
        """Find nodes by name (case-insensitive partial match)"""
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (n)
            WHERE toLower(n.name) CONTAINS toLower($name)
            RETURN n, labels(n) as labels
            LIMIT $limit
            """
            result = session.run(query, name=name, limit=limit)
            nodes = []
            for record in result:
                node = dict(record['n'])
                node['type'] = record['labels'][0] if record['labels'] else 'Unknown'
                nodes.append(node)
            return nodes

    def get_node_edges(self, node_id: str, direction: str = 'both') -> List[Dict]:
        """
        Get all edges connected to a node
        Returns list of dicts: { ...edge_props, type, from_id, to_id, direction }
        """
        query = ""
        if direction == 'outgoing':
            query = """
            MATCH (n {id: $node_id})-[r]->(target)
            RETURN r, type(r) as type, startNode(r).id as from_id, endNode(r).id as to_id, 'outgoing' as direction
            """
        elif direction == 'incoming':
            query = """
            MATCH (n {id: $node_id})<-[r]-(source)
            RETURN r, type(r) as type, startNode(r).id as from_id, endNode(r).id as to_id, 'incoming' as direction
            """
        else: # both
            query = """
            MATCH (n {id: $node_id})-[r]-(other)
            RETURN r, type(r) as type, startNode(r).id as from_id, endNode(r).id as to_id, 
                   CASE WHEN startNode(r).id = $node_id THEN 'outgoing' ELSE 'incoming' END as direction
            """
            
        with self.driver.session(database=self.database) as session:
            result = session.run(query, node_id=node_id)
            edges = []
            for record in result:
                edge_props = dict(record['r'])
                edge_props['type'] = record['type']
                edge_props['from_id'] = record['from_id']
                edge_props['to_id'] = record['to_id']
                edge_props['direction'] = record['direction']
                edges.append(edge_props)
            return edges

    def get_stats(self) -> Dict:
        """Get graph statistics"""
        with self.driver.session(database=self.database) as session:
            # Fast approximations or exact counts
            nodes_count = session.run("MATCH (n) RETURN count(n) as c").single()['c']
            edges_count = session.run("MATCH ()-[r]->() RETURN count(r) as c").single()['c']
            
            # Count by labels (approximated for speed logic, but simple enough here)
            node_types_res = session.run("CALL db.labels() YIELD label CALL apoc.cypher.run('MATCH (:`'+label+'`) RETURN count(*) as count', {}) YIELD value RETURN label, value.count as count")
            # Fallback if apoc not available or complex:
            # Just do simple match for types if few
            
            node_types = {}
            try:
                for record in node_types_res:
                    node_types[record['label']] = record['count']
            except Exception:
                # Basic redundant fallback
                node_types = {"Status": "Detailed stats require APOC"}

            # Simple edge type count
            edge_types_res = session.run("MATCH ()-[r]->() RETURN type(r) as t, count(r) as c")
            edge_types = {record['t']: record['c'] for record in edge_types_res}

            return {
                "total_nodes": nodes_count,
                "total_edges": edges_count,
                "node_types": node_types,
                "edge_types": edge_types,
                "avg_edges_per_node": edges_count / max(nodes_count, 1)
            }

    def clear_all(self):
        """
        ┌─────────────────────────────────────────────┐
        │  🗑️ CLEAR ALL GRAPH DATA                   │
        └─────────────────────────────────────────────┘
        """
        logger.info("🗑️ CLEARING ALL NEO4J DATA")
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("✅ Neo4j database cleared")

# Global instance
_graph_service = None

def get_graph_service() -> GraphService:
    """Get or create graph service singleton"""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
