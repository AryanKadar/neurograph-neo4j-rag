"""
═══════════════════════════════════════════════════════════════
 🧠 Entity & Relationship Extraction Service
═══════════════════════════════════════════════════════════════
"""

import json
import os
from typing import Dict, List
from openai import AzureOpenAI
from config.settings import settings
from config import graph_config
from utils.logger import setup_logger

logger = setup_logger()

# Entity extraction prompt (embedded since .txt files are gitignored)
ENTITY_EXTRACTION_PROMPT = """You are an expert knowledge graph extractor. Extract entities and relationships from the text.

ENTITY TYPES: PERSON, ORGANIZATION, SYSTEM, CONCEPT, ERROR_CODE, FEATURE, LOCATION, EVENT, DOCUMENT, TECHNOLOGY, DATABASE, API

RELATIONSHIP TYPES: CREATED_BY, DEPENDS_ON, USES, PART_OF, CAUSED_BY, RETURNS, CONNECTS_TO, MANAGES, IMPLEMENTS, RELATES_TO, MENTIONED_IN, DEPLOYED_ON, COMMUNICATES_WITH

CONFIDENCE SCORES:
- 0.9-1.0: Explicitly stated
- 0.7-0.9: Strongly implied  
- 0.5-0.7: Reasonably implied
- 0.3-0.5: Weakly implied
- Below 0.3: Do not include

Return ONLY valid JSON (no markdown, no additional text):
{{
  "entities": [{{"id": "...", "type": "...", "name": "...", "description": "..."}}],
  "relationships": [{{"from_id": "...", "to_id": "...", "type": "...", "confidence": 0.95, "description": "..."}}]
}}

TEXT: {text}

JSON RESULT:"""

class EntityExtractor:
    """
    ┌─────────────────────────────────────────────┐
    │  🧠 Entity & Relationship Extractor         │
    │                                             │
    │  Uses GPT-5 to extract:                    │
    │  • Entities (people, systems, concepts)    │
    │  • Relationships (how entities connect)    │
    │  • Confidence scores                       │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_API_BASE
        )
        
        logger.info("🧠 EntityExtractor initialized")
    
    def extract(self, text: str, chunk_id: str) -> Dict:
        """
        Extract entities and relationships from text
        
        Args:
            text: Text to analyze (typically a parent chunk)
            chunk_id: ID of the source chunk
        
        Returns:
            {
                "entities": [...],
                "relationships": [...],
                "chunk_id": chunk_id
            }
        """
        logger.info(f"🧠 Extracting entities from chunk {chunk_id}...")
        
        # Prepare prompt (Escape braces in text to prevent format errors)
        safe_text = text[:4000].replace("{", "{{").replace("}", "}}")
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=safe_text)
        
        try:
            # Call GPT-5
            response = self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a knowledge graph extraction expert. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=graph_config.EXTRACTION_TEMPERATURE,
                max_tokens=2000,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # Parse response
            result_text = response.choices[0].message.content
            
            # Clean JSON (remove markdown if present)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text.strip())
            
            # Add metadata
            result['chunk_id'] = chunk_id
            result['source_text_length'] = len(text)
            
            # Add unique prefixes to IDs to avoid collisions across chunks
            for entity in result.get('entities', []):
                if not entity['id'].startswith(f"{chunk_id}_"):
                    entity['id'] = f"{chunk_id}_{entity['id']}"
            
            for rel in result.get('relationships', []):
                if not rel['from_id'].startswith(f"{chunk_id}_"):
                    rel['from_id'] = f"{chunk_id}_{rel['from_id']}"
                if not rel['to_id'].startswith(f"{chunk_id}_"):
                    rel['to_id'] = f"{chunk_id}_{rel['to_id']}"
            
            # Limit entities/relationships
            if len(result.get('entities', [])) > graph_config.MAX_ENTITIES_PER_CHUNK:
                logger.warning(f"⚠️  Truncating {len(result['entities'])} entities to {graph_config.MAX_ENTITIES_PER_CHUNK}")
                result['entities'] = result['entities'][:graph_config.MAX_ENTITIES_PER_CHUNK]
            
            if len(result.get('relationships', [])) > graph_config.MAX_RELATIONSHIPS_PER_CHUNK:
                logger.warning(f"⚠️  Truncating {len(result['relationships'])} relationships to {graph_config.MAX_RELATIONSHIPS_PER_CHUNK}")
                result['relationships'] = result['relationships'][:graph_config.MAX_RELATIONSHIPS_PER_CHUNK]
            
            logger.info(
                f"   └─ Found: {len(result.get('entities', []))} entities, "
                f"{len(result.get('relationships', []))} relationships"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Entity extraction failed: {e}")
            return {
                "entities": [],
                "relationships": [],
                "chunk_id": chunk_id,
                "error": str(e)
            }


# Global instance
_entity_extractor = None

def get_entity_extractor() -> EntityExtractor:
    """Get or create entity extractor singleton"""
    global _entity_extractor
    if _entity_extractor is None:
        _entity_extractor = EntityExtractor()
    return _entity_extractor
