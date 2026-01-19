"""
═══════════════════════════════════════════════════════════════
 🤖 Research Agent Service
═══════════════════════════════════════════════════════════════
"""

import json
from typing import List, Dict
from config import agent_config, settings
from services.vector_store import get_vector_store
from services.bm25_service import get_bm25_service
from services.graph_traversal import get_graph_traversal
from services.hybrid_retriever import get_hybrid_retriever
from services.embeddings import get_embedding_service
from utils.logger import setup_logger
from openai import AzureOpenAI

logger = setup_logger()

class ResearchAgent:
    """
    Performs multi-step research to gather comprehensive context.
    """
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_API_BASE
        )
        self.vector_store = get_vector_store()
        self.bm25 = get_bm25_service()
        self.graph = get_graph_traversal()
        self.hybrid = get_hybrid_retriever()
        self.embedding_service = get_embedding_service()
        
    def research(self, query: str) -> List[Dict]:
        """
        Main Loop: Search -> Evaluate -> Loop
        Returns: List of accumulated unique chunks
        """
        logger.info(f"🤖 Agent starting research on: '{query}'")
        
        accumulated_chunks = []
        seen_ids = set()
        current_query = query
        
        for step in range(agent_config.MAX_LOOPS):
            logger.info(f"🤖 Step {step+1}/{agent_config.MAX_LOOPS}: Searching for '{current_query}'")
            
            # 1. Execute Search (Re-using Hybrid Logic inline for now)
            step_chunks = self._execute_hybrid_search(current_query)
            
            # 2. Add New Chunks
            new_count = 0
            for chunk in step_chunks:
                # Use chunk_id or content hash
                c_id = chunk.get('id', hash(chunk.get('content', '')))
                if c_id not in seen_ids:
                    seen_ids.add(c_id)
                    accumulated_chunks.append(chunk)
                    new_count += 1
            
            logger.info(f"   └─ Found {len(step_chunks)} results, {new_count} new.")
            
            # 3. Evaluate Sufficiency
            if step == agent_config.MAX_LOOPS - 1:
                break # Max steps reached
                
            next_move = self._evaluate_and_plan(query, accumulated_chunks)
            if next_move.get("status") == "COMPLETE":
                logger.info("🤖 Agent decided context is sufficient.")
                break
            else:
                current_query = next_move.get("next_query", current_query)
                logger.info(f"🤖 Agent planned next step: {next_move.get('reasoning')}")
        
        return accumulated_chunks

    def _execute_hybrid_search(self, query: str) -> List[Dict]:
        """Performs 3-way hybrid search"""
        try:
            # Vector
            emb = self.embedding_service.embed_query(query)
            vector_results = self.vector_store.search(emb, top_k=5)
            
            # BM25
            bm25_results = self.bm25.search(query, top_k=5)
            
            # Graph
            graph_results = self.graph.search_by_query(query)
            
            # Fuse
            fused = self.hybrid.fuse(
                [vector_results, bm25_results, graph_results],
                weights=[1.0, 1.0, 1.0], # Equal weights for agent exploration
                method_names=["Vector", "BM25", "Graph"]
            )
            
            return [chunk for chunk, score in fused[:7]] # Top 7 per step
        except Exception as e:
            logger.error(f"❌ Agent search failed: {e}")
            return []

    def _evaluate_and_plan(self, original_query: str, chunks: List[Dict]) -> Dict:
        """Decide if we need more info"""
        context_text = "\n".join([c.get('content', '')[:200] for c in chunks])
        
        prompt = f"""
        You are a Research Planner.
        User Query: "{original_query}"
        
        Current Knowledge:
        {context_text}
        
        Do you represent a COMPLETE answer to the query?
        If NO, what precise specific ONE query should we search next?
        
        Return JSON:
        {{
            "status": "COMPLETE" or "CONTINUE",
            "reasoning": "Missing X...",
            "next_query": "specific query"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=agent_config.AGENT_MODEL,
                messages=[{"role": "system", "content": "Return valid JSON."}, {"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except:
            return {"status": "COMPLETE"} # Fallback

_research_agent = None

def get_research_agent():
    global _research_agent
    if _research_agent is None:
        _research_agent = ResearchAgent()
    return _research_agent
