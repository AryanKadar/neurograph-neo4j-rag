"""
═══════════════════════════════════════════════════════════════
 🔀 Hybrid Retrieval - RRF Fusion
═══════════════════════════════════════════════════════════════
"""

from typing import List, Dict, Tuple
from collections import defaultdict
from utils.logger import setup_logger

logger = setup_logger()

class HybridRetriever:
    """
    ┌─────────────────────────────────────────────┐
    │  🔀 Reciprocal Rank Fusion (RRF)           │
    │                                             │
    │  Merges multiple search results fairly:    │
    │  • Vector search results                   │
    │  • BM25 search results                     │
    │  • Graph search results (future)           │
    │                                             │
    │  Formula: RRF_score(d) = Σ 1/(k + rank(d)) │
    │  where k = 60 (constant)                   │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self, k: int = 60):
        """
        Args:
            k: RRF constant (default 60, from research)
        """
        self.k = k
    
    def fuse(
        self, 
        result_sets: List[List[Tuple[Dict, float]]], 
        weights: List[float] = None,
        method_names: List[str] = None
    ) -> List[Tuple[Dict, float]]:
        """
        Fuse multiple ranked result sets using RRF
        
        Args:
            result_sets: List of result lists, each containing (chunk, score) tuples
            weights: Optional weights for each result set (default: equal weights)
            method_names: Optional names for each method (for logging)
        
        Returns:
            Fused results sorted by RRF score
        
        Example:
            vector_results = [(chunk1, 0.89), (chunk2, 0.82), ...]
            bm25_results = [(chunk3, 15.2), (chunk1, 12.1), ...]
            
            fused = hybrid_retriever.fuse([vector_results, bm25_results])
            # chunk1 appears in both → high RRF score
        """
        if weights is None:
            weights = [1.0] * len(result_sets)
        
        if method_names is None:
            method_names = [f"Method_{i+1}" for i in range(len(result_sets))]
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # Calculate RRF scores
        rrf_scores = defaultdict(float)
        chunk_map = {}
        contribution_tracker = defaultdict(list)
        
        for result_set, weight, method_name in zip(result_sets, weights, method_names):
            for rank, (chunk, original_score) in enumerate(result_set):
                # Use 'id' if available, otherwise create unique key from content
                chunk_id = chunk.get('id') or hash(chunk.get('content', ''))
                
                # RRF formula: weight / (k + rank)
                rrf_score = weight / (self.k + rank)
                rrf_scores[chunk_id] += rrf_score
                
                # Track contribution
                contribution_tracker[chunk_id].append({
                    'method': method_name,
                    'rank': rank,
                    'original_score': original_score,
                    'rrf_contribution': rrf_score
                })
                
                # Store chunk (in case not stored yet)
                if chunk_id not in chunk_map:
                    chunk_map[chunk_id] = chunk
        
        # Sort by RRF score
        sorted_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Convert back to (chunk, score) format with metadata
        fused_results = []
        for chunk_id, score in sorted_results:
            chunk = chunk_map[chunk_id].copy()
            # Add fusion metadata
            chunk['rrf_score'] = score
            chunk['appeared_in'] = [c['method'] for c in contribution_tracker[chunk_id]]
            chunk['fusion_details'] = contribution_tracker[chunk_id]
            
            fused_results.append((chunk, score))
        
        logger.info(
            f"🔀 RRF Fusion: {len(result_sets)} methods ({', '.join(method_names)}) → "
            f"{len(fused_results)} unique results"
        )
        
        return fused_results
    
    def weighted_fuse(
        self,
        vector_results: List[Tuple[Dict, float]],
        bm25_results: List[Tuple[Dict, float]],
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5
    ) -> List[Tuple[Dict, float]]:
        """
        Convenience method for vector + BM25 fusion
        
        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            vector_weight: Weight for vector search (default 0.5)
            bm25_weight: Weight for BM25 search (default 0.5)
        
        Returns:
            Fused results
        """
        return self.fuse(
            [vector_results, bm25_results],
            weights=[vector_weight, bm25_weight],
            method_names=['Vector Search', 'BM25 Search']
        )


# Global instance
_hybrid_retriever = None


def get_hybrid_retriever() -> HybridRetriever:
    """Get or create hybrid retriever singleton"""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever
