"""
═══════════════════════════════════════════════════════════════
 🌌 COSMIC AI - FAISS Vector Store with HNSW
═══════════════════════════════════════════════════════════════
"""

import faiss
import numpy as np
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger()


class VectorStore:
    """
    ┌─────────────────────────────────────────────┐
    │  🔍 FAISS-based Vector Store                │
    │  Using HNSW for fast similarity search      │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.dimension = settings.EMBEDDING_DIMENSION  # Azure OpenAI text-embedding-ada-002 dimension
        self.index: Optional[faiss.IndexHNSWFlat] = None
        self.chunks: List[Dict] = []
        self.metadata: Dict = {"documents": {}}
        self.processing_files: set = set()
        self.failed_files: Dict[str, str] = {}

        
        self.index_path = os.path.join(settings.VECTOR_DB_PATH, "index.faiss")
        self.chunks_path = os.path.join(settings.VECTOR_DB_PATH, "chunks.json")
        self.metadata_path = os.path.join(settings.VECTOR_DB_PATH, "metadata.json")
        
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize or load FAISS HNSW index"""
        
        if os.path.exists(self.index_path):
            logger.info("📂 Loading existing FAISS index...")
            self.index = faiss.read_index(self.index_path)
            self._load_chunks()
            self._load_metadata()
            logger.info(f"   └─ Loaded: {self.index.ntotal} vectors")
        else:
            logger.info("🆕 Creating new FAISS HNSW index...")
            self.index = faiss.IndexHNSWFlat(
                self.dimension,
                settings.HNSW_M  # Number of connections per layer
            )
            # Set construction parameter
            self.index.hnsw.efConstruction = settings.HNSW_EF_CONSTRUCTION
            logger.info(f"   └─ M: {settings.HNSW_M}")
            logger.info(f"   └─ efConstruction: {settings.HNSW_EF_CONSTRUCTION}")
    
    def add_chunks(
        self,
        file_id: str,
        filename: str,
        chunks: List[str],
        embeddings: np.ndarray
    ):
        """
        Add document chunks and embeddings to the vector store
        
        ┌─────────────────────────────────────────────┐
        │  📥 Adding chunks to vector database        │
        └─────────────────────────────────────────────┘
        """
        
        if embeddings.shape[0] != len(chunks):
            raise ValueError("Number of embeddings must match number of chunks")
        
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension must be {self.dimension}")
        
        logger.info(f"📥 Adding {len(chunks)} chunks to vector store...")
        
        # Convert to float32 if needed
        embeddings = embeddings.astype('float32')
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Get starting index
        start_idx = len(self.chunks)
        
        # Add embeddings to FAISS index
        self.index.add(embeddings)
        
        # Store chunks with metadata
        for i, chunk_text in enumerate(chunks):
            self.chunks.append({
                "id": start_idx + i,
                "file_id": file_id,
                "content": chunk_text,
                "chunk_index": i,
                "tokens": len(chunk_text.split())  # Rough estimate
            })
        
        # Update metadata
        self.metadata["documents"][file_id] = {
            "filename": filename,
            "upload_date": datetime.utcnow().isoformat(),
            "num_chunks": len(chunks),
            "total_tokens": sum(len(c.split()) for c in chunks)
        }
        
        # Remove from processing list
        self.processing_files.discard(file_id)
        
        # Persist to disk
        self._save_all()
        
        logger.info(f"   └─ Total vectors: {self.index.ntotal}")
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 3,
        file_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for similar chunks using HNSW
        
        ┌─────────────────────────────────────────────┐
        │  🔍 Searching vector database               │
        └─────────────────────────────────────────────┘
        
        Returns:
            List of dicts with keys: content, score, file_id, chunk_index
        """
        
        if self.index.ntotal == 0:
            logger.warning("⚠️ Vector store is empty")
            return []
        
        logger.info(f"🔍 Searching for top {top_k} similar chunks...")
        
        # Ensure correct shape and type
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Set search parameter
        self.index.hnsw.efSearch = settings.HNSW_EF_SEARCH
        
        # Perform search
        # Get more results if filtering by file_id
        k = top_k * 10 if file_ids else top_k
        k = min(k, self.index.ntotal)
        
        distances, indices = self.index.search(query_embedding, k)
        
        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for missing results
                continue
            
            chunk = self.chunks[idx]
            
            # Filter by file_ids if specified
            if file_ids and chunk["file_id"] not in file_ids:
                continue
            
            # Convert distance to similarity score (cosine similarity)
            # L2 distance after normalization: d = 2 - 2*cos(theta)
            # So: cos(theta) = 1 - d/2
            similarity = 1 - (dist / 2)
            
            results.append({
                "content": chunk["content"],
                "score": float(similarity),
                "file_id": chunk["file_id"],
                "chunk_index": chunk["chunk_index"]
            })
            
            if len(results) >= top_k:
                break
        
        logger.info(f"   └─ Found: {len(results)} similar chunks")
        
        return results
    
    def get_document_status(self, file_id: str) -> Dict:
        """Get processing status for a document"""
        
        if file_id in self.metadata["documents"]:
            doc = self.metadata["documents"][file_id]
            return {
                "status": "completed",
                "chunks_count": doc["num_chunks"],
                "upload_date": doc["upload_date"]
            }
        elif file_id in self.processing_files:
            return {
                "status": "processing",
                "chunks_count": 0
            }
        elif file_id in self.failed_files:
            return {
                "status": "failed",
                "chunks_count": 0,
                "error": self.failed_files[file_id]
            }
        else:
            return {
                "status": "not_found",
                "chunks_count": 0
            }
    
    def mark_as_processing(self, file_id: str):
        """Mark a file as currently processing"""
        self.processing_files.add(file_id)
        if file_id in self.failed_files:
            del self.failed_files[file_id]
            
    def mark_as_failed(self, file_id: str, error: str):
        """Mark a file as failed processing"""
        self.processing_files.discard(file_id)
        self.failed_files[file_id] = error
    
    def get_all_chunks_for_file(self, file_id: str) -> List[str]:
        """Get all chunk contents for a specific file"""
        return [c["content"] for c in self.chunks if c["file_id"] == file_id]
    
    def clear_all(self):
        """
        ┌─────────────────────────────────────────────┐
        │  🗑️ CLEAR ALL DATA - Reset Database         │
        └─────────────────────────────────────────────┘
        
        Removes all vectors, chunks, metadata, and files.
        Use this for starting fresh or clearing old data.
        """
        logger.info("═" * 60)
        logger.info("🗑️ CLEARING ALL VECTOR STORE DATA")
        logger.info("═" * 60)
        
        # Reset in-memory structures
        self.chunks = []
        self.metadata = {"documents": {}}
        self.processing_files = set()
        self.failed_files = {}
        
        # Recreate FAISS index
        logger.info("🔄 Recreating FAISS index...")
        self.index = faiss.IndexHNSWFlat(
            self.dimension,
            settings.HNSW_M
        )
        self.index.hnsw.efConstruction = settings.HNSW_EF_CONSTRUCTION
        
        # Delete persisted files
        import shutil
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
            logger.info("   └─ Deleted: index.faiss")
        
        if os.path.exists(self.chunks_path):
            os.remove(self.chunks_path)
            logger.info("   └─ Deleted: chunks.json")
        
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)
            logger.info("   └─ Deleted: metadata.json")
        
        # Clear uploaded files
        if os.path.exists(settings.UPLOAD_DIR):
            for filename in os.listdir(settings.UPLOAD_DIR):
                file_path = os.path.join(settings.UPLOAD_DIR, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not delete {filename}: {e}")
            logger.info("   └─ Cleared: uploads directory")
        
        # Clear BM25 index
        bm25_path = os.path.join(settings.VECTOR_DB_PATH, "bm25_index.pkl")
        if os.path.exists(bm25_path):
            os.remove(bm25_path)
            logger.info("   └─ Deleted: bm25_index.pkl")
        
        logger.info("✅ All data cleared successfully")
        logger.info("═" * 60)
    
    def _save_all(self):
        """Persist index and data to disk"""
        
        logger.info("💾 Saving vector store to disk...")
        
        # Save FAISS index
        faiss.write_index(self.index, self.index_path)
        
        # Save chunks
        with open(self.chunks_path, 'w', encoding='utf-8') as f:
            json.dump({"chunks": self.chunks}, f, indent=2, ensure_ascii=False)
        
        # Save metadata
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        
        logger.info("   └─ Saved successfully")
    
    def _load_chunks(self):
        """Load chunks from disk"""
        
        if os.path.exists(self.chunks_path):
            with open(self.chunks_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.chunks = data.get("chunks", [])
    
    def _load_metadata(self):
        """Load metadata from disk"""
        
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {"documents": {}}


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create vector store singleton"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
