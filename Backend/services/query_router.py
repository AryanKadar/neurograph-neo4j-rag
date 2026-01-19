"""
═══════════════════════════════════════════════════════════════
 🧭 Smart Query Router
 Routes queries to appropriate processing pipelines
═══════════════════════════════════════════════════════════════
"""

import re
from typing import Dict, Tuple
from config import agent_config
from utils.logger import setup_logger

logger = setup_logger()

# ─────────────────────────────────────────────────────────────
# QUERY PATTERNS
# ─────────────────────────────────────────────────────────────

GREETING_PATTERNS = [
    r'\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b',
    r'\bhow are you\b',
    r'\bwhat\'?s up\b',
    r'\bhowdy\b',
    r'\byo\b'
]

CHITCHAT_PATTERNS = [
    r'\b(thank you|thanks|thx|ty|appreciate it?)\b',
    r'\b(ok|okay|got it|understood|i see|alright|cool|nice)\b',
    r'\b(bye|goodbye|see you|cya|later)\b',
    r'\byou\'?re welcome\b',
    r'\bno problem\b'
]

SIMPLE_FACTUAL_INDICATORS = [
    r'\bwhat is\b',
    r'\bwho is\b',
    r'\bwhen (was|is|did)\b',
    r'\bwhere (is|was)\b',
    r'\bdefine\b',
    r'\bmeaning of\b'
]


class QueryRouter:
    """
    Smart query router that categorizes queries and determines
    the appropriate processing pipeline.
    
    Routes:
    - greeting: "hi", "hello" → Skip RAG, quick response
    - chitchat: "thanks", "ok" → Skip RAG, acknowledgment
    - simple: Short factual queries → RAG without HyDE
    - complex: Long queries → Full RAG with HyDE
    - agentic: Research queries → Multi-step agentic RAG
    """
    
    def __init__(self):
        self.greeting_regex = re.compile('|'.join(GREETING_PATTERNS), re.IGNORECASE)
        self.chitchat_regex = re.compile('|'.join(CHITCHAT_PATTERNS), re.IGNORECASE)
        self.simple_regex = re.compile('|'.join(SIMPLE_FACTUAL_INDICATORS), re.IGNORECASE)
        
        logger.info("🧭 QueryRouter initialized")
    
    def route_query(self, query: str) -> Tuple[str, Dict]:
        """
        Classify query and return route + metadata.
        
        Returns:
            Tuple[str, Dict]: (route_type, metadata)
            
        Routes:
            - 'greeting': Greeting/small talk
            - 'chitchat': Thanks/acknowledgment
            - 'simple': Simple factual query
            - 'complex': Complex query
            - 'agentic': Research/comparison query
        """
        query_lower = query.lower().strip()
        word_count = len(query.split())
        
        # 1. GREETING DETECTION
        if self.greeting_regex.search(query_lower):
            logger.info(f"🧭 Route: GREETING (query: '{query[:30]}...')")
            return 'greeting', {
                'skip_rag': True,
                'skip_hyde': True,
                'use_cache': False,
                'reasoning': 'Detected greeting pattern'
            }
        
        # 2. CHITCHAT DETECTION
        if self.chitchat_regex.search(query_lower):
            logger.info(f"🧭 Route: CHITCHAT (query: '{query[:30]}...')")
            return 'chitchat', {
                'skip_rag': True,
                'skip_hyde': True,
                'use_cache': False,
                'reasoning': 'Detected chitchat/acknowledgment'
            }
        
        # 3. AGENTIC DETECTION (Complex research queries)
        if agent_config.ENABLE_AGENTIC_RAG and any(
            kw in query_lower for kw in agent_config.AUTO_TRIGGER_KEYWORDS
        ):
            logger.info(f"🧭 Route: AGENTIC (query: '{query[:30]}...')")
            return 'agentic', {
                'skip_rag': False,
                'skip_hyde': False,
                'use_cache': True,
                'use_agent': True,
                'reasoning': 'Complex research/comparison query detected'
            }
        
        # 4. SIMPLE FACTUAL QUERY
        # Short queries with factual indicators (what is, who is, etc.)
        if (word_count <= 6 and self.simple_regex.search(query_lower)) or \
           (word_count <= 3):
            logger.info(f"🧭 Route: SIMPLE (query: '{query[:30]}...')")
            return 'simple', {
                'skip_rag': False,
                'skip_hyde': True,  # Skip HyDE for simple lookups
                'use_cache': True,
                'reasoning': 'Short factual query - exact matching preferred'
            }
        
        # 5. DEFAULT: COMPLEX QUERY
        logger.info(f"🧭 Route: COMPLEX (query: '{query[:30]}...')")
        return 'complex', {
            'skip_rag': False,
            'skip_hyde': False,  # Use HyDE for semantic enhancement
            'use_cache': True,
            'reasoning': 'Standard complex query'
        }
    
    def should_use_rag(self, route: str) -> bool:
        """Determine if RAG retrieval should be used."""
        return route not in ['greeting', 'chitchat']
    
    def should_use_hyde(self, route: str) -> bool:
        """Determine if HyDE query transformation should be used."""
        return route in ['complex', 'agentic']
    
    def should_use_agent(self, route: str) -> bool:
        """Determine if agentic RAG should be used."""
        return route == 'agentic'
    
    def get_search_weights(self, route: str) -> Dict[str, float]:
        """
        Get recommended search weights based on query route.
        
        Returns weights for: vector, bm25, graph
        """
        weight_profiles = {
            'simple': {
                'vector': 0.20,  # Less semantic, more exact
                'bm25': 0.60,    # BM25 excels at factual lookups
                'graph': 0.20
            },
            'complex': {
                'vector': 0.35,  # Balanced
                'bm25': 0.35,
                'graph': 0.30
            },
            'agentic': {
                'vector': 0.30,  # More graph for relationships
                'bm25': 0.30,
                'graph': 0.40
            }
        }
        
        return weight_profiles.get(route, weight_profiles['complex'])
    
    def format_quick_response(self, route: str, query: str) -> str:
        """
        Generate quick response for  non-RAG queries.
        
        Args:
            route: Route type ('greeting' or 'chitchat')
            query: User query
            
        Returns:
            Quick response message
        """
        if route == 'greeting':
            return """Hello! I'm Cosmic AI, your intelligent assistant. 

I can help you find information from your uploaded documents. Feel free to ask me:
- Questions about specific topics
- Requests to explain concepts
- Questions about relationships between entities
- Searches for error codes or specific IDs

What would you like to know?"""
        
        elif route == 'chitchat':
            # Detect thank you vs other chitchat
            if any(word in query.lower() for word in ['thank', 'thanks', 'appreciate']):
                return "You're welcome! Feel free to ask if you have any other questions."
            else:
                return "Is there anything else I can help you with?"
        
        return None


# Global instance
_query_router = None


def get_query_router() -> QueryRouter:
    """Get or create query router singleton."""
    global _query_router
    if _query_router is None:
        _query_router = QueryRouter()
    return _query_router
