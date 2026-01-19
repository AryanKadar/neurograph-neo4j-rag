"""
═══════════════════════════════════════════════════════════════
 🧠 Query Transformation Service
═══════════════════════════════════════════════════════════════
"""

import json
from openai import AzureOpenAI
from config.settings import settings
from config import query_config
from utils.logger import setup_logger

logger = setup_logger()

# ─────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────

HYDE_PROMPT_TEMPLATE = """You are an expert documentation writer. 
Please write a short, high-quality passage that answers the user's question. 
It should look like it comes from a technical documentation page.
DO NOT answer the question directly. Write the DOCUMENT PASSAGE that would contain the answer.
Include hypothetical technical details, steps, or explanations.

Question: {query}

Passage:"""

ANALYSIS_PROMPT_TEMPLATE = """Analyze the following user query to determine its intent and type.

QUERY: "{query}"

Determine the Query Type from these options:
1. factual: Asking for a specific fact, ID, date, or entity definition. (e.g., "who created X?", "id for Y")
2. conceptual: Asking for an explanation, how something works, or "why". (e.g., "how does auth work?")
3. relational: Asking about connections, dependencies, or relationships. (e.g., "how is X connected to Y?", "what depends on Z?")
4. code_error: Contains specific error codes, log snippets, or "fix error". (e.g., "error 503", "NullReferenceException")

Return JSON ONLY:
  "keywords": ["key", "words"]
}}"""

CRITIQUE_PROMPT_TEMPLATE = """You are a critical technical reviewer.

Original Query: "{query}"

Generated HyDE Answer:
"{hyde_doc}"

Critically evaluate this hypothetical answer:
1. Confidence (0-100): How likely is this correct?
2. Technical accuracy: Is it factually sound?
3. Alternative causes: What else could be the answer?
4. Recommendation: trust_high, trust_medium, or trust_low?

Return JSON ONLY:
{{
  "confidence": <int>,
  "technical_accuracy": "<string>",
  "issues": ["<string>"],
  "alternative_causes": ["<string>"],
  "recommendation": "trust_high" | "trust_medium" | "trust_low"
}}"""

# ─────────────────────────────────────────────────────────────
# SERVICE CLASS
# ─────────────────────────────────────────────────────────────

class QueryTransformService:
    """
    Handles Advanced Query Processing:
    1. Query Analysis (Intent detection)
    2. HyDE (Hypothetical Document Generation)
    """
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_API_BASE
        )
        logger.info("🧠 QueryTransformService initialized")

    def analyze_query(self, query: str) -> dict:
        """
        Analyze query to detect intent and return optimal weights.
        """
        if not query_config.ENABLE_QUERY_ANALYSIS:
            return {'weights': query_config.WEIGHT_PROFILES['balanced'], 'type': 'balanced'}
            
        logger.info(f"🧠 Analyzing query intent: '{query[:50]}...'")
        
        try:
            response = self.client.chat.completions.create(
                model=query_config.ANALYSIS_MODEL,
                messages=[
                    {"role": "system", "content": "You are a query intent analyzer. Output JSON only."},
                    {"role": "user", "content": ANALYSIS_PROMPT_TEMPLATE.format(query=query)}
                ],
                temperature=query_config.ANALYSIS_TEMPERATURE,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            query_type = result.get('query_type', 'balanced')
            weights = query_config.WEIGHT_PROFILES.get(query_type, query_config.WEIGHT_PROFILES['balanced'])
            
            logger.info(f"   └─ Type: {query_type}")
            logger.info(f"   └─ Recommended Weights: Vector={weights['vector']}, BM25={weights['bm25']}, Graph={weights['graph']}")
            
            return {
                'type': query_type,
                'weights': weights,
                'analysis': result
            }
            
        except Exception as e:
            logger.error(f"❌ Query analysis failed: {e}. Using default weights.")
            return {'weights': query_config.WEIGHT_PROFILES['balanced'], 'type': 'balanced'}

    def generate_hyde_doc(self, query: str) -> str:
        """
        Generate a hypothetical document passage for the query.
        Returns the hypothetical text.
        """
        if not query_config.ENABLE_HYDE:
            return query
            
        logger.info("🧠 Generating HyDE document...")
        
        try:
            response = self.client.chat.completions.create(
                model=query_config.HYDE_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that generates hypothetical content."},
                    {"role": "user", "content": HYDE_PROMPT_TEMPLATE.format(query=query)}
                ],
                temperature=query_config.HYDE_TEMPERATURE,
                max_tokens=query_config.HYDE_MAX_TOKENS
            )
            
            hypothetical_doc = response.choices[0].message.content.strip()
            
            # Log preview
            preview = hypothetical_doc[:100].replace('\n', ' ') + "..."
            logger.info(f"   └─ Generated: {preview}")
            
            return hypothetical_doc
            
        except Exception as e:
            return query

    def critique_hyde(self, query: str, hyde_doc: str) -> dict:
        """
        Critique the generated HyDE document to assess confidence.
        Returns validation metadata.
        """
        logger.info("🧠 Critiquing HyDE document...")
        
        try:
            response = self.client.chat.completions.create(
                model=query_config.ANALYSIS_MODEL, # Use a smart model for critique
                messages=[
                    {"role": "system", "content": "You are a critical technical reviewer. Output JSON only."},
                    {"role": "user", "content": CRITIQUE_PROMPT_TEMPLATE.format(query=query, hyde_doc=hyde_doc)}
                ],
                temperature=0.1, # Low temperature for objective analysis
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            confidence = result.get('confidence', 50)
            recommendation = result.get('recommendation', 'trust_medium')
            
            logger.info(f"   └─ Confidence: {confidence}/100 ({recommendation})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ HyDE critique failed: {e}. Assuming medium trust.")
            return {
                'confidence': 50, 
                'recommendation': 'trust_medium',
                'alternative_causes': []
            }

    def adjust_weights(self, current_weights: dict, critique_result: dict) -> dict:
        """
        Dynamically adjust weights based on critique confidence.
        """
        confidence = critique_result.get('confidence', 50)
        
        # Default starting point
        new_weights = current_weights.copy()
        
        # Logic from reference doc
        if confidence >= 70:
            # High Confidence (trust_high)
            # Trust HyDE (Vector)
            new_weights = {'vector': 0.50, 'bm25': 0.30, 'graph': 0.20}
            logger.info("⚖️  Weights Adjusted (High Confidence): Vector boosted")
            
        elif confidence >= 40:
            # Medium Confidence (trust_medium)
            # Balanced
            new_weights = {'vector': 0.35, 'bm25': 0.40, 'graph': 0.25}
            logger.info("⚖️  Weights Adjusted (Medium Confidence): Balanced")
            
        else:
            # Low Confidence (trust_low)
            # Distrust HyDE, boost BM25 and Graph
            new_weights = {'vector': 0.20, 'bm25': 0.50, 'graph': 0.30}
            logger.info("⚖️  Weights Adjusted (Low Confidence): BM25/Graph boosted")
            
        return new_weights


# Global instance
_query_transform_service = None

def get_query_transform_service() -> QueryTransformService:
    global _query_transform_service
    if _query_transform_service is None:
        _query_transform_service = QueryTransformService()
    return _query_transform_service
