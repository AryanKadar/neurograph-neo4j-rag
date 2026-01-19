"""
═══════════════════════════════════════════════════════════════
 🌌 COSMIC AI - Enhanced Chat Service with Professional Responses
═══════════════════════════════════════════════════════════════
"""

import json
import time
from typing import List, Dict, Optional, AsyncGenerator
from openai import AzureOpenAI, APIError, APIConnectionError
from config.settings import settings
from services.vector_store import get_vector_store
from services.embeddings import get_embedding_service
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
        # Step 1: RAG Retrieval (if enabled)
        # ─────────────────────────────────────
        # ─────────────────────────────────────
        # Step 1: Smart Routing & Query Analysis
        # ─────────────────────────────────────
        from services.query_router import get_query_router
        from services.query_transform_service import get_query_transform_service
        from services.hybrid_retriever import get_hybrid_retriever
        from services.bm25_service import get_bm25_service
        from services.graph_traversal import get_graph_traversal
        
        router = get_query_router()
        transform_service = get_query_transform_service()
        hybrid_retriever = get_hybrid_retriever()
        
        # 1. Route the query
        route_type, route_metadata = router.route_query(query)
        logger.info(f"🧭 Route classified as: {route_type.upper()}")
        
        # Handle non-RAG routes immediately
        if not router.should_use_rag(route_type):
            quick_response = router.format_quick_response(route_type, query)
            yield f"data: {json.dumps({'content': quick_response})}\\n\\n"
            yield f"data: {json.dumps({'done': True, 'response_time_ms': 0, 'chunks_used': 0})}\\n\\n"
            return

        # 2. Analyze Intent & Get Initial Weights
        analysis_result = transform_service.analyze_query(query)
        search_weights = analysis_result['weights']
        
        # 3. HyDE Generation & Self-Critique (if needed)
        hyde_doc = None
        if router.should_use_hyde(route_type):
            hyde_doc = transform_service.generate_hyde_doc(query)
            if hyde_doc and hyde_doc != query:
                # Critique the HyDE document
                critique = transform_service.critique_hyde(query, hyde_doc)
                # Adjust weights based on confidence
                search_weights = transform_service.adjust_weights(search_weights, critique)

        # ─────────────────────────────────────
        # Step 2: Parallel Search & Fusion
        # ─────────────────────────────────────
        if use_rag:
            logger.info("🔍 executing parallel hybrid search strategies...")
            
            try:
                # A. Vector Search
                embedding_service = get_embedding_service()
                vector_store = get_vector_store()
                
                # Use HyDE doc for vector search if available, else original query
                search_text = hyde_doc if hyde_doc else query
                query_embedding = embedding_service.embed_query(search_text)
                
                vector_results = vector_store.search(
                    query_embedding,
                    top_k=settings.TOP_K_RESULTS * 2, # Fetch more for fusion
                    file_ids=file_ids
                )
                
                # B. BM25 Search
                bm25_service = get_bm25_service()
                bm25_results = bm25_service.search(query, top_k=settings.TOP_K_RESULTS * 2)
                
                # C. Graph Search
                graph_traversal = get_graph_traversal()
                graph_results = graph_traversal.search_by_query(query)
                
                # D. RRF Fusion
                logger.info(f"⚖️  Fusing results with weights: {search_weights}")
                fused_results = hybrid_retriever.fuse(
                    result_sets=[vector_results, bm25_results, graph_results],
                    weights=[search_weights['vector'], search_weights['bm25'], search_weights['graph']],
                    method_names=['Vector', 'BM25', 'Graph']
                )
                
                # Take top K from fused list
                context_chunks = [item[0] for item in fused_results[:settings.MAX_CONTEXT_CHUNKS]]
                
                if context_chunks:
                    logger.info(f"   └─ Selected {len(context_chunks)} optimal chunks after fusion")
                else:
                    logger.info("   └─ No relevant chunks found after fusion")
                    
            except Exception as e:
                logger.error(f"❌ Hybrid RAG retrieval error: {e}")
                # Fallback to simple vector search
                try:
                    logger.warning("⚠️ Falling back to simple vector search...")
                    query_embedding = embedding_service.embed_query(query)
                    context_chunks = vector_store.search(query_embedding, top_k=settings.TOP_K_RESULTS)
                except Exception as ve:
                     logger.error(f"❌ Fallback failed: {ve}")
        
        # ─────────────────────────────────────
        # Step 2: Prepare Messages
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
                input_parts.append(f"HISTORY:\\n{history_text}")
        
        # Add RAG context
        if context_chunks:
            context_text = ToonFormatter.format_full_context(context_chunks)
            input_parts.append(f"CONTEXT:\\n{context_text}")
        
        # Add the query
        input_parts.append(f"QUERY: {query}")
        
        # Combine into single user message
        user_content = "\\n\\n".join(input_parts)
        messages.append({"role": "user", "content": user_content})
        
        logger.info(f"📤 Sending to Azure OpenAI...")
        logger.info(f"   └─ Messages: {len(messages)}")
        
        # ─────────────────────────────────────
        # Step 3: Stream Response with Retry Logic
        # ─────────────────────────────────────
        max_retries = 3
        retry_count = 0
        start_time = time.time()
        
        while retry_count < max_retries:
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
                chunk_count = 0
                
                for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            content = delta.content
                            full_response += content
                            chunk_count += 1
                            
                            # Yield SSE formatted data
                            yield f"data: {json.dumps({'content': content})}\\n\\n"
                
                # Calculate response time
                response_time_ms = int((time.time() - start_time) * 1000)
                
                # Send metadata with completion signal
                metadata = {
                    'done': True,
                    'chunks_used': len(context_chunks),
                    'response_time_ms': response_time_ms,
                    'model': self.deployment
                }
                yield f"data: {json.dumps(metadata)}\\n\\n"
                
                logger.info(f"✅ Response completed:")
                logger.info(f"   └─ Length: {len(full_response)} chars")
                logger.info(f"   └─ Time: {response_time_ms}ms")
                logger.info(f"   └─ Chunks: {chunk_count}")
                
                break  # Success, exit retry loop
                
            except APIConnectionError as e:
                retry_count += 1
                logger.warning(f"⚠️  Connection error (attempt {retry_count}/{max_retries})")
                
                if retry_count < max_retries:
                    # Wait before retry (exponential backoff)
                    wait_time = 2 ** retry_count
                    logger.info(f"   └─ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Max retries reached
                    error_msg = "Connection to Azure OpenAI failed. Please check your network and try again."
                    formatted_error = ResponseFormatter.format_error_response(error_msg, query)
                    yield f"data: {json.dumps({'error': error_msg, 'formatted_error': formatted_error})}\\n\\n"
                    logger.error(f"❌ Max retries reached for connection error")
                    
            except APIError as e:
                logger.error(f"❌ Azure API error (truncated)")
                error_msg = f"Azure OpenAI API error: {str(e)[:100]}"
                formatted_error = ResponseFormatter.format_error_response(error_msg, query)
                yield f"data: {json.dumps({'error': error_msg, 'formatted_error': formatted_error})}\\n\\n"
                break
                
            except Exception as e:
                logger.error(f"❌ Unexpected streaming error")
                error_msg = f"An unexpected error occurred"
                formatted_error = ResponseFormatter.format_error_response(error_msg, query)
                yield f"data: {json.dumps({'error': error_msg, 'formatted_error': formatted_error})}\\n\\n"
                break
    
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
        
        # 1. Routing
        from services.query_router import get_query_router
        router = get_query_router()
        route_type, _ = router.route_query(query)
        
        # Handle quick responses
        if not router.should_use_rag(route_type):
            return {
                "response": router.format_quick_response(route_type, query),
                "retrieved_chunks": [],
                "model": "rule-based"
            }

        # 2. RAG Retrieval (Hybrid)
        if use_rag:
            try:
                # Import services
                from services.query_transform_service import get_query_transform_service
                from services.hybrid_retriever import get_hybrid_retriever
                from services.bm25_service import get_bm25_service
                from services.graph_traversal import get_graph_traversal
                from services.vector_store import get_vector_store
                from services.embeddings import get_embedding_service
                
                # Setup
                transform_service = get_query_transform_service()
                hybrid_retriever = get_hybrid_retriever()
                
                # Analysis & HyDE
                weights = transform_service.analyze_query(query)['weights']
                hyde_doc = None
                if router.should_use_hyde(route_type):
                    hyde_doc = transform_service.generate_hyde_doc(query)
                    if hyde_doc:
                        critique = transform_service.critique_hyde(query, hyde_doc)
                        weights = transform_service.adjust_weights(weights, critique)
                
                # Parallel Search
                # A. Vector
                search_text = hyde_doc if hyde_doc else query
                emb_service = get_embedding_service()
                q_emb = emb_service.embed_query(search_text)
                vec_results = get_vector_store().search(q_emb, top_k=settings.TOP_K_RESULTS*2, file_ids=file_ids)
                
                # B. BM25
                bm25_results = get_bm25_service().search(query, top_k=settings.TOP_K_RESULTS*2)
                
                # C. Graph
                graph_results = get_graph_traversal().search_by_query(query)
                
                # Fusion
                fused = hybrid_retriever.fuse(
                    [vec_results, bm25_results, graph_results],
                    weights=[weights['vector'], weights['bm25'], weights['graph']]
                )
                
                # Top K
                context_chunks = [x[0] for x in fused[:settings.MAX_CONTEXT_CHUNKS]]
                
            except Exception as e:
                logger.error(f"❌ Hybrid RAG error: {e}")
                # Fallback
                try: 
                    emb = get_embedding_service().embed_query(query)
                    context_chunks = get_vector_store().search(emb, top_k=5)
                except:
                    context_chunks = []
        
        # Prepare messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add context (Formatted)
        input_parts = []
        
        if history:
            recent_history = history[-10:]
            history_text = ToonFormatter.format_history(recent_history)
            if history_text:
                input_parts.append(f"HISTORY:\\n{history_text}")
        
        if context_chunks:
            context_text = ToonFormatter.format_full_context(context_chunks)
            input_parts.append(f"CONTEXT:\\n{context_text}")
        
        input_parts.append(f"QUERY: {query}")
        
        user_content = "\\n\\n".join(input_parts)
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
