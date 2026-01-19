"""
═══════════════════════════════════════════════════════════════
 🎯 Cross-Encoder Reranker - Final Quality Filter
═══════════════════════════════════════════════════════════════
"""

from typing import List, Dict, Tuple, Optional
from sentence_transformers import CrossEncoder
from utils.logger import setup_logger

logger = setup_logger()

class RerankerService:
    """
    ┌─────────────────────────────────────────────┐
    │  🎯 Cross-Encoder Reranking                │
    │                                             │
    │  Why Rerank?                               │
    │  • Bi-encoders (vector search) are fast    │
    │    but approximate                         │
    │  • Cross-encoders are slow but accurate    │
    │                                             │
    │  Strategy:                                 │
    │  1. Fast search gets 50 candidates         │
    │  2. Reranker scores top 20 precisely       │
    │  3. Return best 5-10                       │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2",
        device: str = "cpu"
    ):
        """
        Args:
            model_name: HuggingFace model for cross-encoding
            device: 'cpu' or 'cuda'
        """
        logger.info(f"🔄 Loading cross-encoder: {model_name}...")
        try:
            self.model = CrossEncoder(model_name, device=device)
            logger.info(f"✅ Cross-encoder loaded successfully")
            self.model_loaded = True
        except Exception as e:
            logger.error(f"❌ Failed to load cross-encoder: {e}")
            logger.warning("⚠️ Reranker will return results without reranking")
            self.model = None
            self.model_loaded = False
    
    def rerank(
        self,
        query: str,
        candidates: List[Tuple[Dict, float]],
        top_k: int = 10,
        threshold: Optional[float] = None
    ) -> List[Tuple[Dict, float]]:
        """
        Rerank candidates using cross-encoder
        
        Args:
            query: Original user query
            candidates: List of (chunk, score) from initial search
            top_k: Number of results to return
            threshold: Optional minimum score threshold (drop results below this)
        
        Returns:
            Reranked results sorted by cross-encoder score
        
        Example:
            initial_results = hybrid_retriever.fuse([vector_results, bm25_results])
            reranked = reranker.rerank("What is error 503?", initial_results, top_k=5)
        """
        if not candidates:
            return []
        
        # If model not loaded, return original results
        if not self.model_loaded:
            logger.warning("⚠️ Returning results without reranking (model not loaded)")
            return candidates[:top_k]
        
        # Prepare query-document pairs
        pairs = [(query, chunk.get('content', '')) for chunk, _ in candidates]
        
        # Get cross-encoder scores
        try:
            scores = self.model.predict(pairs)
        except Exception as e:
            logger.error(f"❌ Reranking error: {e}")
            return candidates[:top_k]
        
        # Combine with original chunks
        reranked = []
        for i, (chunk, original_score) in enumerate(candidates):
            chunk_copy = chunk.copy()
            reranker_score = float(scores[i])
            
            # Add reranking metadata
            chunk_copy['reranker_score'] = reranker_score
            chunk_copy['original_score'] = original_score
            
            reranked.append((chunk_copy, reranker_score))
        
        # Apply threshold if specified
        if threshold is not None:
            reranked = [(chunk, score) for chunk, score in reranked if score >= threshold]
        
        # Sort by reranker score
        reranked.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k
        top_results = reranked[:top_k]
        
        logger.info(
            f"🎯 Reranked {len(candidates)} candidates → "
            f"{len(top_results)} results "
            f"(threshold: {threshold if threshold else 'none'})"
        )
        
        return top_results


# Global instance
_reranker_service = None


def get_reranker_service() -> RerankerService:
    """Get or create reranker service singleton"""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
