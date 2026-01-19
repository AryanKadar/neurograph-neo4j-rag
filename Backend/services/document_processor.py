"""
═══════════════════════════════════════════════════════════════
 🌌 COSMIC AI - Document Processing Pipeline
═══════════════════════════════════════════════════════════════
"""

import os
import numpy as np
from typing import List
from services.document_parser import DocumentParser
from services.chunking import get_text_chunker
from services.embeddings import get_embedding_service
from services.vector_store import get_vector_store
from services.bm25_service import get_bm25_service
from services.entity_extractor import get_entity_extractor
from services.graph_service import get_graph_service
from utils.logger import setup_logger

logger = setup_logger()


async def process_document(file_path: str, file_id: str):
    """
    ┌─────────────────────────────────────────────────────────────┐
    │  🚀 Complete Document Processing Pipeline                   │
    │                                                             │
    │  1. Parse document → Extract text                           │
    │  2. Chunk text → Recursive splitting                        │
    │  3. Generate embeddings → Azure OpenAI                      │
    │  4. Store in vector database → FAISS HNSW                   │
    └─────────────────────────────────────────────────────────────┘
    """
    
    try:
        filename = os.path.basename(file_path)
        
        logger.info("═" * 60)
        logger.info(f"🚀 PROCESSING DOCUMENT: {filename}")
        logger.info("═" * 60)
        
        # ─────────────────────────────────────
        # Step 1: Parse document
        # ─────────────────────────────────────
        logger.info("\n📋 STEP 1: Parsing Document")
        logger.info("─" * 40)
        
        parser = DocumentParser()
        text = parser.parse(file_path)
        
        if not text or not text.strip():
            logger.warning("⚠️ No text extracted from document")
            return
        
        logger.info(f"✅ Extracted: {len(text)} characters")
        
        # ─────────────────────────────────────
        # Step 2: Chunk text
        # ─────────────────────────────────────
        logger.info("\n✂️ STEP 2: Chunking Text")
        logger.info("─" * 40)
        
        chunker = get_text_chunker()
        chunks = chunker.chunk_text(text)
        
        if not chunks:
            logger.warning("⚠️ No chunks generated")
            return
        
        logger.info(f"✅ Generated: {len(chunks)} chunks")
        
        # ─────────────────────────────────────
        # Step 3: Generate embeddings
        # ─────────────────────────────────────
        logger.info("\n🧠 STEP 3: Generating Embeddings")
        logger.info("─" * 40)
        
        embedding_service = get_embedding_service()
        
        # Process in batches to avoid token limits
        BATCH_SIZE = 16  # Azure OpenAI batch limit
        all_embeddings = []
        
        total_batches = (len(chunks) - 1) // BATCH_SIZE + 1
        
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            
            logger.info(f"   └─ Batch {batch_num}/{total_batches}: {len(batch)} chunks")
            
            batch_embeddings = embedding_service.embed_texts(batch)
            all_embeddings.append(batch_embeddings)
        
        # Concatenate all embeddings
        embeddings = np.vstack(all_embeddings)
        
        logger.info(f"✅ Embeddings shape: {embeddings.shape}")
        
        # ─────────────────────────────────────
        # Step 4: Store in vector database
        # ─────────────────────────────────────
        logger.info("\n💾 STEP 4: Storing in Vector Database")
        logger.info("─" * 40)
        
        vector_store = get_vector_store()
        
        vector_store.add_chunks(
            file_id=file_id,
            filename=filename,
            chunks=chunks,
            embeddings=embeddings
        )
        
        # ─────────────────────────────────────
        # Step 5: Build BM25 Index
        # ─────────────────────────────────────
        logger.info("\n🔨 STEP 5: Building BM25 Keyword Index")
        logger.info("─" * 40)
        
        bm25_service = get_bm25_service()
        
        # Prepare chunks for BM25 (need id and content)
        bm25_chunks = [
            {
                "id": f"{file_id}_chunk_{i}",
                "content": chunk,
                "file_id": file_id,
                "chunk_index": i
            }
            for i, chunk in enumerate(chunks)
        ]
        
        bm25_service.build_index(bm25_chunks)
        
        # ─────────────────────────────────────
        # Step 6: Extract Knowledge Graph
        # ─────────────────────────────────────
        logger.info("\n🕸️  STEP 6: Extracting Knowledge Graph")
        logger.info("─" * 40)
        
        entity_extractor = get_entity_extractor()
        graph_service = get_graph_service()
        
        # Process larger parent chunks for graph extraction
        # (better context for entity relationships)
        parent_chunk_size = 1500
        parent_chunks = []
        
        # Create parent chunks by combining consecutive chunks
        for i in range(0, len(chunks), 3):
            parent_text = ' '.join(chunks[i:i+3])
            if len(parent_text) > 100:  # Skip tiny chunks
                parent_chunks.append({
                    'id': f"{file_id}_parent_{i}",
                    'text': parent_text
                })
        
        logger.info(f"   └─ Processing {len(parent_chunks)} parent chunks for extraction...")
        
        total_entities = 0
        total_relationships = 0
        
        for parent_chunk in parent_chunks:
            # Extract entities and relationships
            extraction_result = entity_extractor.extract(
                text=parent_chunk['text'],
                chunk_id=parent_chunk['id']
            )
            
            # Add to graph
            graph_service.add_extraction_result(extraction_result, file_id)
            
            total_entities += len(extraction_result.get('entities', []))
            total_relationships += len(extraction_result.get('relationships', []))
        
        logger.info(f"   └─ Extracted: {total_entities} entities, {total_relationships} relationships")
        
        # Get graph stats
        graph_stats = graph_service.get_stats()
        logger.info(f"   └─ Graph now contains: {graph_stats['total_nodes']} nodes, {graph_stats['total_edges']} edges")
        
        # ─────────────────────────────────────
        # Complete!
        # ─────────────────────────────────────
        logger.info("\n" + "═" * 60)
        logger.info(f"🎉 DOCUMENT PROCESSED SUCCESSFULLY!")
        logger.info(f"   └─ File ID: {file_id}")
        logger.info(f"   └─ Chunks: {len(chunks)}")
        logger.info(f"   └─ Vector Index: ✅")
        logger.info(f"   └─ BM25 Index: ✅")
        logger.info(f"   └─ Knowledge Graph: ✅ (+{total_entities} entities, +{total_relationships} rels)")
        logger.info(f"   └─ Ready for Ultimate Hybrid RAG queries")
        logger.info("═" * 60 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error processing document {file_id}: {e}")
        
        # Mark as failed in vector store
        try:
            vector_store = get_vector_store()
            vector_store.mark_as_failed(file_id, str(e))
        except Exception as ve:
            logger.error(f"Failed to update vector store status: {ve}")
            
        raise
