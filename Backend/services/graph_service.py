"""
═══════════════════════════════════════════════════════════════
 🕸️ Graph Database Service - Storage & Management
═══════════════════════════════════════════════════════════════
"""

import json
import os
from typing import List, Dict, Optional
from collections import defaultdict
from config import graph_config
from utils.logger import setup_logger

logger = setup_logger()

class GraphService:
    """
    ┌─────────────────────────────────────────────┐
    │  🕸️  Graph Database Service (JSON-based)    │
    │                                             │
    │  Storage:                                   │
    │  • nodes.json - All entities               │
    │  • edges.json - All relationships          │
    │  • entity_chunks.json - Entity→chunk map   │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.nodes_path = graph_config.NODES_FILE
        self.edges_path = graph_config.EDGES_FILE
        self.entity_chunks_path = graph_config.ENTITY_CHUNKS_FILE
        
        # Create graph_db directory
        os.makedirs(graph_config.GRAPH_DB_PATH, exist_ok=True)
        
        # Load existing graph
        self.nodes = self._load_json(self.nodes_path, {})
        self.edges = self._load_json(self.edges_path, [])
        self.entity_chunks = self._load_json(self.entity_chunks_path, {})
        
        logger.info(
            f"🕸️  Graph loaded: {len(self.nodes)} nodes, "
            f"{len(self.edges)} edges"
        )
    
    def _load_json(self, path: str, default):
        """Load JSON file or return default"""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️  Failed to load {path}: {e}")
                return default
        return default
    
    def _save_json(self, path: str, data):
        """Save data to JSON file"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_extraction_result(
        self,
        extraction_result: Dict,
        file_id: str
    ):
        """
        Add entities and relationships from extraction result
        
        Args:
            extraction_result: Result from EntityExtractor
            file_id: Source file ID
        """
        chunk_id = extraction_result.get('chunk_id', 'unknown')
        entities = extraction_result.get('entities', [])
        relationships = extraction_result.get('relationships', [])
        
        logger.info(
            f"📥 Adding to graph: {len(entities)} entities, "
            f"{len(relationships)} relationships"
        )
        
        # Add entities (nodes)
        for entity in entities:
            entity_id = entity['id']
            
            # Merge if entity already exists (combine info)
            if entity_id in self.nodes:
                existing = self.nodes[entity_id]
                # Update description if new one is longer/better
                if len(entity.get('description', '')) > len(existing.get('description', '')):
                    existing['description'] = entity['description']
                # Track all source chunks
                if 'source_chunks' not in existing:
                    existing['source_chunks'] = []
                if chunk_id not in existing['source_chunks']:
                    existing['source_chunks'].append(chunk_id)
            else:
                # New entity
                entity['source_chunks'] = [chunk_id]
                entity['file_id'] = file_id
                self.nodes[entity_id] = entity
            
            # Map entity → chunks
            if entity_id not in self.entity_chunks:
                self.entity_chunks[entity_id] = []
            if chunk_id not in self.entity_chunks[entity_id]:
                self.entity_chunks[entity_id].append(chunk_id)
        
        # Add relationships (edges)
        for rel in relationships:
            # Only add if both entities exist
            if rel['from_id'] in self.nodes and rel['to_id'] in self.nodes:
                # Add metadata
                rel['file_id'] = file_id
                rel['chunk_id'] = chunk_id
                self.edges.append(rel)
            else:
                logger.warning(
                    f"⚠️  Skipping relationship: "
                    f"{rel.get('from_id', '?')} → {rel.get('to_id', '?')} (missing entities)"
                )
        
        # Save to disk
        self._save_all()
    
    def _save_all(self):
        """Save all graph data"""
        self._save_json(self.nodes_path, self.nodes)
        self._save_json(self.edges_path, self.edges)
        self._save_json(self.entity_chunks_path, self.entity_chunks)
        
        logger.info("💾 Graph saved to disk")
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get a node by ID"""
        return self.nodes.get(node_id)
    
    def find_nodes_by_name(self, name: str, limit: int = 10) -> List[Dict]:
        """Find nodes by name (case-insensitive partial match)"""
        name_lower = name.lower()
        matches = []
        for node_id, node in self.nodes.items():
            if name_lower in node.get('name', '').lower():
                matches.append({**node, 'id': node_id})
                if len(matches) >= limit:
                    break
        return matches
    
    def get_node_edges(self, node_id: str, direction: str = 'both') -> List[Dict]:
        """
        Get all edges connected to a node
        
        Args:
            node_id: Node ID
            direction: 'outgoing', 'incoming', or 'both'
        """
        edges = []
        for edge in self.edges:
            if direction in ['outgoing', 'both'] and edge['from_id'] == node_id:
                edges.append({**edge, 'direction': 'outgoing'})
            elif direction in ['incoming', 'both'] and edge['to_id'] == node_id:
                edges.append({**edge, 'direction': 'incoming'})
        return edges
    
    def get_stats(self) -> Dict:
        """Get graph statistics"""
        node_types = defaultdict(int)
        for node in self.nodes.values():
            node_types[node.get('type', 'unknown')] += 1
        
        edge_types = defaultdict(int)
        for edge in self.edges:
            edge_types[edge.get('type', 'unknown')] += 1
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
            "avg_edges_per_node": len(self.edges) / max(len(self.nodes), 1)
        }
    
    def clear_all(self):
        """
        ┌─────────────────────────────────────────────┐
        │  🗑️ CLEAR ALL GRAPH DATA                   │
        └─────────────────────────────────────────────┘
        
        Removes all nodes, edges, and entity mappings.
        Use this for starting fresh or clearing old data.
        """
        logger.info("═" * 60)
        logger.info("🗑️ CLEARING ALL GRAPH DATA")
        logger.info("═" * 60)
        
        # Reset in-memory structures  
        self.nodes = {}
        self.edges = []
        self.entity_chunks = {}
        
        # Delete JSON files
        if os.path.exists(self.nodes_path):
            os.remove(self.nodes_path)
            logger.info("   └─ Deleted: nodes.json")
        
        if os.path.exists(self.edges_path):
            os.remove(self.edges_path)
            logger.info("   └─ Deleted: edges.json")
        
        if os.path.exists(self.entity_chunks_path):
            os.remove(self.entity_chunks_path)
            logger.info("   └─ Deleted: entity_chunks.json")
        
        logger.info("✅ All graph data cleared successfully")
        logger.info("═" * 60)




# Global instance
_graph_service = None

def get_graph_service() -> GraphService:
    """Get or create graph service singleton"""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
