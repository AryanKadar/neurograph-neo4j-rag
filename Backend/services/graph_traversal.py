"""
═══════════════════════════════════════════════════════════════
 🔍 Graph Traversal - Path Finding & Scoring
═══════════════════════════════════════════════════════════════
"""

from typing import List, Dict, Tuple, Set
from collections import deque
from config import graph_config
from services.graph_service import get_graph_service
from utils.logger import setup_logger

logger = setup_logger()

class GraphTraversal:
    """
    ┌─────────────────────────────────────────────┐
    │  🔍 Graph Traversal Service                │
    │                                             │
    │  Algorithm: Breadth-First Search (BFS)     │
    │  • Finds paths between entities            │
    │  • Scores paths by relevance               │
    │  • Returns source chunks                   │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.graph_service = get_graph_service()
        logger.info("🔍 GraphTraversal initialized")
    
    def find_paths(
        self,
        start_entities: List[str],
        end_entities: List[str],
        max_hops: int = None
    ) -> List[Dict]:
        """
        Find paths between start and end entities using BFS
        
        Args:
            start_entities: List of starting entity IDs/names
            end_entities: List of target entity IDs/names
            max_hops: Maximum path length (default from config)
        
        Returns:
            List of path dictionaries with scores
        """
        if max_hops is None:
            max_hops = graph_config.MAX_HOPS
        
        logger.info(
            f"🔍 Finding paths: {start_entities[:2]}... → {end_entities[:2]}... "
            f"(max {max_hops} hops)"
        )
        
        # Resolve entity names to IDs
        start_ids = self._resolve_entities(start_entities)
        end_ids = self._resolve_entities(end_entities)
        
        if not start_ids or not end_ids:
            logger.info("   └─ Could not resolve entities")
            return []
        
        # Find all paths
        all_paths = []
        for start_id in start_ids:
            for end_id in end_ids:
                if start_id != end_id:
                    paths = self._bfs_paths(start_id, end_id, max_hops)
                    all_paths.extend(paths)
        
        # Score and rank paths
        scored_paths = []
        for path in all_paths:
            scored = self._score_path(path)
            if scored and scored['score'] > 0:
                scored_paths.append(scored)
        
        # Sort by score
        scored_paths.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"   └─ Found {len(scored_paths)} valid paths")
        
        return scored_paths[:graph_config.MAX_PATHS_PER_QUERY]
    
    def _resolve_entities(self, entity_refs: List[str]) -> List[str]:
        """Resolve entity names/IDs to actual IDs"""
        resolved = []
        for ref in entity_refs:
            # Try direct ID lookup
            if ref in self.graph_service.nodes:
                resolved.append(ref)
            else:
                # Try name search
                matches = self.graph_service.find_nodes_by_name(ref, limit=3)
                resolved.extend([m['id'] for m in matches])
        return list(set(resolved))[:10]  # Limit to 10 unique IDs
    
    def _bfs_paths(
        self,
        start_id: str,
        end_id: str,
        max_hops: int
    ) -> List[List[Dict]]:
        """
        BFS to find all paths from start to end
        
        Returns: List of paths, where each path is a list of edges
        """
        # Queue: (current_node, path_so_far, visited_nodes)
        queue = deque([(start_id, [], {start_id})])
        found_paths = []
        
        while queue and len(found_paths) < 20:  # Limit total paths
            current, path, visited = queue.popleft()
            
            # Stop if too long
            if len(path) >= max_hops:
                continue
            
            # Get outgoing edges from current node
            edges = self.graph_service.get_node_edges(current, direction='outgoing')
            
            for edge in edges:
                next_node = edge.get('to_id')
                
                if not next_node:
                    continue
                
                # Found target!
                if next_node == end_id:
                    found_paths.append(path + [edge])
                    if len(found_paths) >= 20:
                        break
                    continue
                
                # Visit if not seen and within hop limit
                if next_node not in visited and len(path) < max_hops - 1:
                    queue.append((
                        next_node,
                        path + [edge],
                        visited | {next_node}
                    ))
        
        return found_paths
    
    def _score_path(self, path: List[Dict]) -> Optional[Dict]:
        """
        Score a path based on multiple factors
        
        Returns:
            {
                'path': path,
                'score': float,
                'nodes': [node_ids],
                'edges': [edge_types],
                'source_chunks': [chunk_ids]
            }
        """
        if not path:
            return None
        
        # Factor 1: Length (shorter is better)
        hop_count = len(path)
        length_score = {1: 1.0, 2: 0.8, 3: 0.6}.get(hop_count, 0.4)
        
        # Factor 2: Edge relevance (weighted by type)
        edge_scores = [
            graph_config.EDGE_WEIGHTS.get(edge.get('type', ''), 0.5)
            for edge in path
        ]
        edge_score = sum(edge_scores) / len(edge_scores) if edge_scores else 0.5
        
        # Factor 3: Confidence (from extraction)
        confidences = [edge.get('confidence', 0.8) for edge in path]
        
        # Apply hybrid confidence filtering
        min_confidence = min(confidences) if confidences else 0.5
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Hard filter for very low confidence
        if min_confidence < graph_config.MIN_CONFIDENCE:
            return None  # Reject this path
        
        # Soft penalty for medium confidence
        if min_confidence < graph_config.SOFT_CONFIDENCE:
            normalized = (min_confidence - graph_config.MIN_CONFIDENCE) / \
                        (graph_config.SOFT_CONFIDENCE - graph_config.MIN_CONFIDENCE)
            avg_confidence *= (0.5 + 0.5 * max(0, normalized))
        
        # Final score (weighted combination)
        weights = graph_config.PATH_SCORING_WEIGHTS
        final_score = (
            weights['length'] * length_score +
            weights['edge_type'] * edge_score +
            weights['confidence'] * avg_confidence
        )
        
        # Extract info
        nodes = [path[0].get('from_id', '')] + [e.get('to_id', '') for e in path]
        source_chunks = list(set(
            e.get('chunk_id', '') for e in path if e.get('chunk_id')
        ))
        
        return {
            'path': path,
            'score': final_score,
            'hop_count': hop_count,
            'nodes': nodes,
            'edges': [e.get('type', '') for e in path],
            'source_chunks': source_chunks,
            'confidence_scores': confidences,
            'low_confidence_warning': min_confidence < 0.70
        }
    
    def search_by_query(self, query: str) -> List[Tuple[Dict, float]]:
        """
        Search graph based on query (extract entities and find paths)
        
        Args:
            query: User query string
        
        Returns:
            List of (chunk_dict, score) tuples for RRF fusion
        """
        logger.info(f"🕸️  Graph search: '{query[:50]}...'")
        
        # Simple entity extraction from query (keywords)
        # Remove common words
        stop_words = {'what', 'when', 'where', 'how', 'why', 'who', 'the', 'is', 'are', 
                     'was', 'were', 'to', 'from', 'in', 'on', 'at', 'by', 'with', 'and', 'or'}
        query_words = [
            word.strip('.,!?;:()[]{}"\' ')
            for word in query.lower().split()
            if len(word) > 2 and word.lower() not in stop_words
        ]
        
        if len(query_words) < 2:
            logger.info("   └─ Need at least 2 entities for relationship query")
            return []
        
        # Find paths between entities mentioned in query
        paths = self.find_paths(
            start_entities=query_words[:5],  # First N words
            end_entities=query_words[-5:],   # Last N words
            max_hops=graph_config.MAX_HOPS
        )
        
        if not paths:
            logger.info("   └─ No graph paths found")
            return []
        
        # Convert paths to chunks for RRF
        results = []
        seen_chunks = set()
        
        for path_info in paths[:5]:  # Top 5 paths
            for chunk_id in path_info.get('source_chunks', []):
                if chunk_id and chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    
                    # Create descriptive content about the path
                    node_names = []
                    for node_id in path_info['nodes']:
                        node = self.graph_service.get_node(node_id)
                        if node:
                            node_names.append(node.get('name', node_id))
                    
                    path_description = ' → '.join(node_names)
                    
                    results.append((
                        {
                            'id': f"graph_{chunk_id}",
                            'content': f"Knowledge Graph Path: {path_description}",
                            'chunk_id': chunk_id,
                            'graph_path': path_info['edges'],
                            'path_score': path_info['score'],
                            'hop_count': path_info['hop_count']
                        },
                        path_info['score']
                    ))
        
        logger.info(f"   └─ Graph: {len(results)} chunks from {len(paths)} paths")
        
        return results


# Global instance
_graph_traversal = None

def get_graph_traversal() -> GraphTraversal:
    """Get or create graph traversal singleton"""
    global _graph_traversal
    if _graph_traversal is None:
        _graph_traversal = GraphTraversal()
    return _graph_traversal
