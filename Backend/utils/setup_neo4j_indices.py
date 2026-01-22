
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import GraphDatabase
from config import graph_config

def setup_indices():
    """Create indices for all entity types"""
    print("🚀 Setting up Neo4j Indices...")
    
    driver = GraphDatabase.driver(
        graph_config.NEO4J_URI,
        auth=(graph_config.NEO4J_USER, graph_config.NEO4J_PASSWORD)
    )
    
    entity_types = graph_config.ENTITY_TYPES
    # Add generic 'Entity' if you plan to use a base label, but we used specific labels.
    
    with driver.session(database=graph_config.NEO4J_DATABASE) as session:
        for ent_type in entity_types:
            # 1. ID Constraint/Index (Constraint is better for IDs)
            # "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Person) REQUIRE n.id IS UNIQUE"
            # Note: Enterprise users get more constraints, but uniqueness is good.
            # Free tier supports unique constraints.
            
            try:
                # Using 4.4+ syntax or 5.x compatible
                query_unique = f"CREATE CONSTRAINT constraint_{ent_type}_id IF NOT EXISTS FOR (n:`{ent_type}`) REQUIRE n.id IS UNIQUE"
                session.run(query_unique)
                print(f"   └─ ✅ Constraint created for :{ent_type}(id)")
                
                # 2. Name Index (for search)
                query_index = f"CREATE INDEX index_{ent_type}_name IF NOT EXISTS FOR (n:`{ent_type}`) ON (n.name)"
                session.run(query_index)
                print(f"   └─ ✅ Index created for :{ent_type}(name)")
                
            except Exception as e:
                print(f"   └─ ⚠️ Error for {ent_type}: {e}")

    driver.close()
    print("\n✨ Indices setup complete!")

if __name__ == "__main__":
    setup_indices()
