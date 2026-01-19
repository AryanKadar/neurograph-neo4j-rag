"""
═══════════════════════════════════════════════════════════════
 🌌 COSMIC AI - Chat Service with RAG
═══════════════════════════════════════════════════════════════
"""

import json
import time
from typing import List, Dict, Optional, AsyncGenerator
from openai import AzureOpenAI, APIError, APIConnectionError
from config.settings import settings
from config import agent_config
from services.vector_store import get_vector_store
from services.embeddings import get_embedding_service
from services.bm25_service import get_bm25_service
from services.hybrid_retriever import get_hybrid_retriever
from services.reranker_service import get_reranker_service
from services.graph_traversal import get_graph_traversal
from services.query_transform_service import get_query_transform_service
from services.context_compressor import get_context_compressor
from services.research_agent import get_research_agent
from services.cache_service import get_cache_service
from services.query_router import get_query_router
from services.toon_formatter import ToonFormatter
from services.response_formatter import ResponseFormatter
from utils.logger import setup_logger

logger = setup_logger()


# ─────────────────────────────────────────────────────────────
#  🛡️ System Prompt - Knowledge-Bound Guardrail
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are Cosmic AI, an intelligent and professional assistant.

**Your Knowledge Boundary:**
- You EXCLUSIVELY answer based on the provided CONTEXT from uploaded documents
- If information is not in the context, politely state: "I couldn't find that information in your documents."

**Response Guidelines:**
1. **Be Clear & Structured**: Use headings, lists, and proper formatting
2. **Provide Evidence**: Quote relevant parts from the context when helpful
3. **Be Comprehensive**: Cover all aspects of the question that are in the context
4. **Use Markdown**: Format your responses with proper markdown for readability
   - Use **bold** for emphasis
   - Use bullet points for lists
   - Use code blocks for technical content
   - Use > for important quotes
5. **Be Professional**: Maintain a helpful, knowledgeable tone
6. **Be Concise**: Provide thorough answers without unnecessary verbosity

**Important:** Never use your general training knowledge to answer document-specific questions. Only use the provided CONTEXT.
"""


class ChatService:
    """
    ┌─────────────────────────────────────────────┐
    │  💬 Chat Service with RAG Integration       │
    │  Streaming responses with context           │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_API_BASE
        )
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        
        logger.info(f"💬 ChatService initialized")
        logger.info(f"   └─ Deployment: {self.deployment}")
    
    async def stream_chat_response(
        self,
        query: str,
        history: List[Dict] = None,
        current_summary: str = "",
        use_rag: bool = True,
        file_ids: List[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        ┌─────────────────────────────────────────────┐
        │  🌊 Stream chat response with RAG           │
        └─────────────────────────────────────────────┘
        """
        
        history = history or []
        context_chunks = []
        
        logger.info("─" * 60)
        logger.info(f"💬 Processing query: {query[:50]}...")
        
        # ─────────────────────────────────────
        # SMART QUERY ROUTING
        # ─────────────────────────────────────
        router = get_query_router()
        route, route_metadata = router.route_query(query)
        
        # Check if we can skip RAG entirely
        if route_metadata.get('skip_rag', False):
            logger.info(f"⚡ Skipping RAG - Route: {route}")
            
            # Generate quick response
            quick_response = router.format_quick_response(route, query)
            if quick_response:
                # Stream the quick response
                yield f"data: {json.dumps({'content': quick_response})}\\n\\n"
                yield f"data: {json.dumps({'done': True})}\\n\\n"
                logger.info(f"✅ Quick response sent (no RAG needed)")
                return
        
        # ─────────────────────────────────────
        # RAG Retrieval (Threaded to avoid blocking)
        # ─────────────────────────────────────
        if use_rag:
            try:
                # Run heavy retrieval in a separate thread
                import asyncio
                context_chunks = await asyncio.to_thread(
                    self._retrieve_rag_context,
                    query=query,
                    file_ids=file_ids,
                    route_metadata=route_metadata
                )
            except Exception as e:
                logger.error(f"❌ RAG retrieval error in thread: {e}")
                
        # ─────────────────────────────────────
        # Step 2: Context Compression (Local LLM)
        # ─────────────────────────────────────
        context_text = ""
        if context_chunks:
            # Save to cache if new
            if use_rag:
                # We can't easily check 'cached_context' here since we moved logic
                # But we can cache the result
                pass 
                
            try:
                compressor = get_context_compressor()
                # Returns compressed text OR full formatted text if compression disabled
                context_text = compressor.compress(context_chunks, query)
            except Exception as e:
                logger.error(f"⚠️ Context compression failed: {e}")
                context_text = ToonFormatter.format_full_context(context_chunks)

        # ─────────────────────────────────────
        # Step 3: Prepare Messages
        # ─────────────────────────────────────
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add Long-Term Memory (Recap) if available
        if current_summary:
            messages.append({
                "role": "system",
                "content": f"PREVIOUS_RECAP: {current_summary}"
            })
        
        # Build input payload (Combined for token efficiency)
        input_parts = []
        
        # Add recent history (last 10 messages)
        if history:
            recent_history = history[-10:]
            history_text = ToonFormatter.format_history(recent_history)
            if history_text:
                input_parts.append(f"HISTORY:\n{history_text}")
        
        # Add RAG context
        if context_text:
            input_parts.append(f"CONTEXT:\n{context_text}")
        
        # Add the query
        input_parts.append(f"QUERY: {query}")
        
        # Combine into single user message
        user_content = "\n\n".join(input_parts)
        messages.append({"role": "user", "content": user_content})
        
        logger.info(f"📤 Sending to Azure OpenAI...")
        logger.info(f"   └─ Messages: {len(messages)}")
        
        # ─────────────────────────────────────
        # Step 4: Stream Response
        # ─────────────────────────────────────
        try:
            stream = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                stream=True,
                temperature=settings.GPT_TEMPERATURE,
                max_tokens=settings.GPT_MAX_COMPLETION_TOKENS,
                top_p=settings.GPT_TOP_P,
                frequency_penalty=settings.GPT_FREQUENCY_PENALTY,
                presence_penalty=settings.GPT_PRESENCE_PENALTY
            )

            
            full_response = ""
            
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        content = delta.content
                        full_response += content
                        
                        # Yield SSE formatted data
                        yield f"data: {json.dumps({'content': content})}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'done': True})}\n\n"
            
            logger.info(f"✅ Response completed: {len(full_response)} chars")
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    def _retrieve_rag_context(self, query: str, file_ids: List[str], route_metadata: Dict = None) -> List[Dict]:
        """Synchronous method for heavy RAG retrieval"""
        context_chunks = []
        route_metadata = route_metadata or {}
        
        # ─────────────────────────────────────
        # Cache Check
        # ─────────────────────────────────────
        cache = get_cache_service()
        cache_key = cache.generate_key("rag_context", query)
        cached_context = cache.get(cache_key)
        
        if cached_context:
            logger.info("⚡ Cache Hit: Using cached retrieval results")
            return cached_context

        # ─────────────────────────────────────
        # Agentic RAG Check
        # ─────────────────────────────────────
        if route_metadata.get('use_agent', False):
            logger.info(f"🤖 Agentic RAG Triggered: '{query}'")
            try:
                agent = get_research_agent()
                context_chunks = agent.research(query)
                if context_chunks:
                    cache.set(cache_key, context_chunks)
                    return context_chunks
            except Exception as e:
                logger.error(f"❌ Agent failed: {e}")

        # ─────────────────────────────────────
        # Step 0: Query Transformation
        # ─────────────────────────────────────
        search_query = query
        search_weights = [0.35, 0.35, 0.30]
        
        # Check if we should skip HyDE (for simple queries)
        use_hyde = not route_metadata.get('skip_hyde', False)
        
        try:
            qt_service = get_query_transform_service()
            
            # A. Analysis (always run for weight optimization)
            analysis = qt_service.analyze_query(query)
            weights = analysis.get('weights', {})
            search_weights = [
                weights.get('vector', 0.35),
                weights.get('bm25', 0.35),
                weights.get('graph', 0.30)
            ]
            
            # B. HyDE (conditionally based on route)
            # B. HyDE (conditionally based on route)
            if use_hyde:
                logger.info("🧠 Using HyDE for query enhancement")
                hyde_doc = qt_service.generate_hyde_doc(query)
                
                # C. Self-Critique & Weight Adjustment
                critique = qt_service.critique_hyde(query, hyde_doc)
                adjusted_weights_dict = qt_service.adjust_weights(weights, critique)
                
                # Update search weights list [vector, bm25, graph]
                search_weights = [
                    adjusted_weights_dict.get('vector', 0.35),
                    adjusted_weights_dict.get('bm25', 0.35),
                    adjusted_weights_dict.get('graph', 0.30)
                ]
                
                # Handle Low Confidence / Fallback
                if critique.get('recommendation') == 'trust_low':
                    logger.info("⚠️ Low Confidence HyDE: Generating fallback from alternative causes")
                    alts = critique.get('alternative_causes', [])
                    if alts:
                         fallback_text = f"Alternative causes: {', '.join(alts)}"
                         search_query = f"{query}\n{fallback_text}"
                    else:
                         search_query = query # Revert to original if no alternatives
                else:
                    search_query = hyde_doc

            else:
                logger.info("⚡ Skipping HyDE (simple query - exact matching preferred)")
                search_query = query
            
        except Exception as e:
            logger.error(f"⚠️ Query transformation failed: {e}")
            
        # ─────────────────────────────────────
        # Step 1: Ultimate Hybrid RAG Retrieval
        # ─────────────────────────────────────
        logger.info("🔍 Ultimate Hybrid Retrieval Pipeline Starting...")
        
        try:
            embedding_service = get_embedding_service()
            vector_store = get_vector_store()
            bm25_service = get_bm25_service()
            hybrid_retriever = get_hybrid_retriever()
            reranker = get_reranker_service()
            
            # 1A. Vector
            query_embedding = embedding_service.embed_query(search_query)
            vector_results = vector_store.search(query_embedding, top_k=10, file_ids=file_ids)
            vector_results_formatted = [
                ({
                    "id": f"vector_{i}",
                    "content": result["content"],
                    "file_id": result["file_id"],
                    "chunk_index": result["chunk_index"]
                }, result["score"])
                for i, result in enumerate(vector_results)
            ]
            
            # 1B. BM25
            bm25_results = bm25_service.search(query, top_k=10)
            
            # 1C. Graph
            graph_traversal = get_graph_traversal()
            graph_results = graph_traversal.search_by_query(query)
            
            # 2. Fusion
            if vector_results_formatted or bm25_results or graph_results:
                fused_results = hybrid_retriever.fuse(
                    result_sets=[vector_results_formatted, bm25_results, graph_results],
                    weights=search_weights,
                    method_names=['Vector', 'BM25', 'Graph']
                )
                
                # 3. Rerank
                if fused_results:
                    reranked_results = reranker.rerank(
                        query=query,
                        candidates=fused_results[:20],
                        top_k=settings.TOP_K_RESULTS,
                        threshold=0.0
                    )
                    
                    context_chunks = [
                        {
                            "content": chunk["content"],
                            "score": score,
                            "file_id": chunk.get("file_id", "unknown"),
                            "chunk_index": chunk.get("chunk_index", 0),
                            "appeared_in": chunk.get("appeared_in", []),
                            "reranker_score": chunk.get("reranker_score", score),
                            "graph_path": chunk.get("graph_path", None)
                        }
                        for chunk, score in reranked_results
                    ]
                    
                    cache.set(cache_key, context_chunks)
                    return context_chunks
                    
        except Exception as e:
            logger.error(f"❌ Retrieval logic error: {e}")
            
        return []

    async def get_chat_response(
        self,
        query: str,
        history: List[Dict] = None,
        use_rag: bool = True,
        file_ids: List[str] = None
    ) -> Dict:
        """
        Get non-streaming chat response
        """
        
        history = history or []
        context_chunks = []
        
        # RAG Retrieval
        if use_rag:
            try:
                embedding_service = get_embedding_service()
                vector_store = get_vector_store()
                
                query_embedding = embedding_service.embed_query(query)
                context_chunks = vector_store.search(
                    query_embedding,
                    top_k=settings.TOP_K_RESULTS,
                    file_ids=file_ids
                )
            except Exception as e:
                logger.error(f"❌ RAG retrieval error: {e}")
        
        # Prepare messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add context
        input_parts = []
        
        if history:
            recent_history = history[-10:]
            history_text = ToonFormatter.format_history(recent_history)
            if history_text:
                input_parts.append(f"HISTORY:\n{history_text}")
        
        if context_chunks:
            context_text = ToonFormatter.format_full_context(context_chunks)
            input_parts.append(f"CONTEXT:\n{context_text}")
        
        input_parts.append(f"QUERY: {query}")
        
        user_content = "\n\n".join(input_parts)
        messages.append({"role": "user", "content": user_content})
        
        # Get response
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=settings.GPT_TEMPERATURE,
                max_tokens=settings.GPT_MAX_COMPLETION_TOKENS,
                top_p=settings.GPT_TOP_P,
                frequency_penalty=settings.GPT_FREQUENCY_PENALTY,
                presence_penalty=settings.GPT_PRESENCE_PENALTY
            )

            
            return {
                "response": response.choices[0].message.content,
                "retrieved_chunks": context_chunks,
                "model": self.deployment
            }
            
        except Exception as e:
            logger.error(f"❌ Chat error: {e}")
            raise


# Global chat service instance
_chat_service = None


def get_chat_service() -> ChatService:
    """Get or create chat service singleton"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
