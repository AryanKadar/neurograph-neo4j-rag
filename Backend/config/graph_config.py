"""
═══════════════════════════════════════════════════════════════
 🕸️ Graph RAG Configuration
═══════════════════════════════════════════════════════════════
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Graph Database Paths
GRAPH_DB_PATH = "./graph_db"
NODES_FILE = f"{GRAPH_DB_PATH}/nodes.json"
EDGES_FILE = f"{GRAPH_DB_PATH}/edges.json"
ENTITY_CHUNKS_FILE = f"{GRAPH_DB_PATH}/entity_chunks.json"

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Entity Extraction Settings
ENTITY_EXTRACTION_MODEL = "gpt-5-chat"  # Uses your Azure OpenAI
MAX_ENTITIES_PER_CHUNK = 20
MAX_RELATIONSHIPS_PER_CHUNK = 30
EXTRACTION_TEMPERATURE = 0.1  # Low for consistent extraction

# Entity Types (customize for your domain)
ENTITY_TYPES = [
    "PERSON",           # People, users, founders
    "ORGANIZATION",     # Companies, teams
    "SYSTEM",          # Software systems, services
    "CONCEPT",         # Abstract concepts, methodologies
    "ERROR_CODE",      # Error codes, status codes
    "FEATURE",         # Product features
    "LOCATION",        # Places, servers, regions
    "EVENT",           # Events, incidents
    "DOCUMENT",        # Other documents, policies
    "TECHNOLOGY",      # Technologies, frameworks
    "DATABASE",        # Databases, data stores
    "API",             # APIs, endpoints
]

# Relationship Types (customize for your domain)
RELATIONSHIP_TYPES = [
    "CREATED_BY",      # X created by Y
    "DEPENDS_ON",      # X depends on Y
    "USES",            # X uses Y
    "PART_OF",         # X is part of Y
    "RELATES_TO",      # X relates to Y
    "CAUSED_BY",       # X caused by Y (errors)
    "RETURNS",         # X returns Y (errors)
    "CONNECTS_TO",     # X connects to Y
    "MANAGES",         # X manages Y
    "IMPLEMENTS",      # X implements Y
    "MENTIONED_IN",    # X mentioned in Y
    "DEPLOYED_ON",     # X deployed on Y
    "COMMUNICATES_WITH", # X communicates with Y
]

# Graph Traversal Settings
MAX_HOPS = 3                    # Maximum path length
MAX_PATHS_PER_QUERY = 10        # Top paths to consider
MIN_CONFIDENCE = 0.40           # Minimum edge confidence (hard filter)
SOFT_CONFIDENCE = 0.70          # Soft threshold for penalties

# Scoring Weights for Edge Types
EDGE_WEIGHTS = {
    'CREATED_BY': 0.95,
    'CAUSED_BY': 0.95,
    'DEPENDS_ON': 0.90,
    'USES': 0.85,
    'PART_OF': 0.85,
    'IMPLEMENTS': 0.80,
    'CONNECTS_TO': 0.75,
    'MANAGES': 0.70,
    'COMMUNICATES_WITH': 0.70,
    'RETURNS': 0.90,
    'DEPLOYED_ON': 0.75,
    'RELATES_TO': 0.65,
    'MENTIONED_IN': 0.50,
}

# Path Scoring Weights
PATH_SCORING_WEIGHTS = {
    'length': 0.3,      # Shorter paths preferred
    'edge_type': 0.4,   # Relevant edge types
    'confidence': 0.3,  # High confidence edges
}

# Hybrid Search Weights (when graph is added)
HYBRID_SEARCH_WEIGHTS = {
    'vector': 0.35,     # Semantic search
    'bm25': 0.35,       # Keyword search
    'graph': 0.30,      # Relationship search
}
