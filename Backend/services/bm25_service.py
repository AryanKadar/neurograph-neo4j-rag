"""
═══════════════════════════════════════════════════════════════
 🔍 BM25 Search Service - Keyword-based Retrieval
═══════════════════════════════════════════════════════════════
"""

import json
import pickle
import os
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from utils.logger import setup_logger

logger = setup_logger()

class BM25Service:
    """
    ┌─────────────────────────────────────────────┐
    │  🔍 BM25 Keyword Search Service            │
    │                                             │
    │  Features:                                  │
    │  • Fast keyword-based retrieval            │
    │  • Exact term matching                     │
    │  • TF-IDF scoring                          │
    │  • Optimized for codes, IDs, names         │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(
        self,
        index_path: str = "./indices/bm25_index.pkl",
        corpus_path: str = "./indices/bm25_corpus.json"
    ):
        self.index_path = index_path
        self.corpus_path = corpus_path
        self.bm25 = None
        self.chunks = []
        self.tokenized_corpus = []
        
        # Load existing index if available
        if os.path.exists(index_path) and os.path.exists(corpus_path):
            self.load_index()
            logger.info(f"✅ BM25 index loaded from {index_path}")
        else:
            logger.info("📝 No BM25 index found. Will create on first indexing.")
    
    def preprocess_text(self, text: str) -> List[str]:
        """
        Tokenize and preprocess text for BM25
        
        Steps:
        1. Lowercase
        2. Tokenize (simple split)
        3. Remove very short tokens
        4. Keep important chars (for error codes, IDs)
        """
        text = text.lower()
        
        # Simple tokenization - keeps alphanumeric and hyphens/underscores
        # This preserves error codes like "ABC-123" or "error_500"
        tokens = []
        current_token = ""
        
        for char in text:
            if char.isalnum() or char in ['-', '_']:
                current_token += char
            else:
                if len(current_token) > 1:  # Keep tokens longer than 1 char
                    tokens.append(current_token)
                current_token = ""
        
        # Don't forget last token
        if len(current_token) > 1:
            tokens.append(current_token)
        
        return tokens
    
    def build_index(self, chunks: List[Dict]):
        """
        Build BM25 index from chunks
        
        Args:
            chunks: List of chunk dictionaries with 'id' and 'content' fields
        
        Example:
            chunks = [
                {"id": "chunk_001", "content": "PaymentService returns 503..."},
                {"id": "chunk_002", "content": "SmartBot connects to API..."}
            ]
        """
        logger.info(f"🔨 Building BM25 index for {len(chunks)} chunks...")
        
        self.chunks = chunks
        
        # Tokenize all chunks
        self.tokenized_corpus = []
        for chunk in chunks:
            tokens = self.preprocess_text(chunk['content'])
            self.tokenized_corpus.append(tokens)
        
        # Build BM25 index
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        
        # Save to disk
        self.save_index()
        
        logger.info(f"✅ BM25 index built and saved")
    
    def save_index(self):
        """Save BM25 index and corpus to disk"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        # Save BM25 index
        with open(self.index_path, 'wb') as f:
            pickle.dump(self.bm25, f)
        
        # Save corpus metadata
        corpus_data = {
            "chunks": self.chunks,
            "tokenized_corpus": self.tokenized_corpus
        }
        with open(self.corpus_path, 'w', encoding='utf-8') as f:
            json.dump(corpus_data, f, ensure_ascii=False)
    
    def load_index(self):
        """Load BM25 index from disk"""
        with open(self.index_path, 'rb') as f:
            self.bm25 = pickle.load(f)
        
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            corpus_data = json.load(f)
            self.chunks = corpus_data['chunks']
            self.tokenized_corpus = corpus_data['tokenized_corpus']
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """
        Search using BM25
        
        Args:
            query: Search query string
            top_k: Number of results to return
        
        Returns:
            List of (chunk_dict, score) tuples, sorted by score descending
        
        Example:
            results = bm25.search("error code ABC-123", top_k=5)
            for chunk, score in results:
                print(f"Score: {score:.2f} - {chunk['content'][:100]}")
        """
        if self.bm25 is None:
            logger.warning("⚠️ BM25 index not built. Call build_index() first.")
            return []
        
        # Tokenize query
        query_tokens = self.preprocess_text(query)
        
        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = sorted(
            range(len(scores)), 
            key=lambda i: scores[i], 
            reverse=True
        )[:top_k]
        
        # Return chunks with scores
        results = [
            (self.chunks[i], float(scores[i]))
            for i in top_indices
            if scores[i] > 0  # Only return chunks with non-zero scores
        ]
        
        logger.info(f"🔍 BM25 search: '{query}' → {len(results)} results")
        
        return results


# Global instance
_bm25_service = None


def get_bm25_service() -> BM25Service:
    """Get or create BM25 service singleton"""
    global _bm25_service
    if _bm25_service is None:
        _bm25_service = BM25Service()
    return _bm25_service
