import json
import time
from collections import defaultdict
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import graph_config
from neo4j import GraphDatabase

def load_json_data():
    """Load existing JSON graph data"""
    print("📂 Loading JSON data...")
    nodes_data = {}
    edges_data = []

    if os.path.exists(graph_config.NODES_FILE):
        with open(graph_config.NODES_FILE, 'r', encoding='utf-8') as f:
            nodes_data = json.load(f)
            
    if os.path.exists(graph_config.EDGES_FILE):
        with open(graph_config.EDGES_FILE, 'r', encoding='utf-8') as f:
            edges_data = json.load(f)
            
    print(f"   └─ Found {len(nodes_data)} nodes and {len(edges_data)} edges.")
    return nodes_data, edges_data

def migrate_to_neo4j():
    """Migrate JSON data to Neo4j"""
    
    # 1. Load Data
    nodes_dict, edges_list = load_json_data()
    
    if not nodes_dict and not edges_list:
        print("⚠️  No data to migrate.")
        return

    # 2. Connect to Neo4j
    print(f"\n🔌 Connecting to Neo4j at {graph_config.NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(
            graph_config.NEO4J_URI,
            auth=(graph_config.NEO4J_USER, graph_config.NEO4J_PASSWORD)
        )
        driver.verify_connectivity()
        print("   └─ Connected successfully!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # 3. Import Nodes (Grouped by Type for efficiency and dynamic labelling)
    print("\n📦 Importing Nodes...")
    nodes_by_type = defaultdict(list)
    for node_id, node_data in nodes_dict.items():
        node_type = node_data.get('type', 'Unknown')
        # Ensure ID is in the data dict for UNWIND
        node_data['id'] = node_id
        nodes_by_type[node_type].append(node_data)

    total_nodes_created = 0
    with driver.session(database=graph_config.NEO4J_DATABASE) as session:
        for node_type, nodes in nodes_by_type.items():
            # Cypher query with dynamic label (safe because we iterate types)
            query = f"""
            UNWIND $batch AS row
            MERGE (n:`{node_type}` {{id: row.id}})
            SET n.name = row.name,
                n.description = row.description,
                n.file_id = row.file_id,
                n.source_chunks = row.source_chunks,
                n.migrated_at = timestamp()
            """
            
            result = session.run(query, batch=nodes)
            consume_result = result.consume()
            count = consume_result.counters.nodes_created + consume_result.counters.properties_set // 4 # Approximate
            # Actually, let's just use len(nodes) for reporting as MERGE is idempotent
            print(f"   └─ Merging {len(nodes)} nodes of type :{node_type}")
            total_nodes_created += len(nodes)

    # 4. Import Edges (Grouped by Type)
    print("\n🔗 Importing Relationships...")
    edges_by_type = defaultdict(list)
    for edge in edges_list:
        edge_type = edge.get('type', 'RELATED_TO')
        edges_by_type[edge_type].append(edge)

    total_edges_created = 0
    with driver.session(database=graph_config.NEO4J_DATABASE) as session:
        for edge_type, edges in edges_by_type.items():
            # Cypher query with dynamic relationship type
            query = f"""
            UNWIND $batch AS row
            MATCH (source {{id: row.from_id}})
            MATCH (target {{id: row.to_id}})
            MERGE (source)-[r:`{edge_type}`]->(target)
            SET r.confidence = row.confidence,
                r.description = row.description,
                r.file_id = row.file_id,
                r.chunk_id = row.chunk_id,
                r.migrated_at = timestamp()
            """
            
            result = session.run(query, batch=edges)
            print(f"   └─ Merging {len(edges)} relationships of type :{edge_type}")
            total_edges_created += len(edges)

    driver.close()
    print("\n✅ Migration Complete!")
    print(f"   Summary: ~{total_nodes_created} Nodes processed, ~{total_edges_created} Edges processed.")

if __name__ == "__main__":
    migrate_to_neo4j()
