"""
═══════════════════════════════════════════════════════════════
 📉 Context Compressor Service
═══════════════════════════════════════════════════════════════
"""

import json
import requests
from typing import List, Dict
from config import compression_config
from services.toon_formatter import ToonFormatter
from utils.logger import setup_logger

logger = setup_logger()

class ContextCompressor:
    """
    Compresses retrieved context using Local LLM (Ollama) to reduce token usage.
    """
    
    def __init__(self):
        self.provider = compression_config.COMPRESSION_PROVIDER
        self.enabled = compression_config.ENABLE_COMPRESSION
        logger.info(f"📉 ContextCompressor initialized (Provider: {self.provider}, Enabled: {self.enabled})")

    def compress(self, chunks: List[Dict], query: str) -> str:
        """
        Compress context chunks based on the query.
        Returns compressed string (TOON format or narrative).
        """
        if not self.enabled or not chunks:
            return ToonFormatter.format_full_context(chunks)

        # 1. format input context (Raw)
        raw_context = "\n\n".join([c.get('content', '') for c in chunks])
        
        # Check if compression is needed (if too short, just return)
        if len(raw_context) < compression_config.MAX_CONTEXT_TOKENS:
             logger.info(f"📉 Context small enough ({len(raw_context)} chars), skipping compression.")
             return raw_context

        # 2. Compress via Provider
        if self.provider == "ollama":
            return self._compress_with_ollama(raw_context, query)
        else:
            return self._compress_with_openai(raw_context, query)

    def _compress_with_ollama(self, context: str, query: str) -> str:
        """
        Call Ollama API to compress context.
        """
        prompt = f"""
        You are a Context Compressor. Your goal is to exact ONLY the information relevant to the user's query from the context below.
        Remove all irrelevant details, boilerplate, and redundancy.
        Keep specific IDs, error codes, and steps.
        
        QUERY: {query}
        
        CONTEXT:
        {context}
        
        COMPRESSED RELEVANT INFO:
        """
        
        try:
            payload = {
                "model": compression_config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": compression_config.TARGET_OUTPUT_TOKENS
                }
            }
            
            logger.info(f"📉 Sending to Ollama ({compression_config.OLLAMA_MODEL})...")
            response = requests.post(
                compression_config.OLLAMA_BASE_URL,
                json=payload,
                timeout=compression_config.OLLAMA_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                compressed_text = result.get('response', '').strip()
                
                reduction = 100 * (1 - (len(compressed_text) / len(context)))
                logger.info(f"📉 Compressed: {len(context)} -> {len(compressed_text)} chars ({reduction:.1f}% reduction)")
                
                return compressed_text
            else:
                logger.warning(f"⚠️ Ollama error {response.status_code}: {response.text}")
                return context
                
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Could not connect to Ollama at {compression_config.OLLAMA_BASE_URL}. Is it running?")
            return context
        except Exception as e:
            logger.error(f"❌ Compression failed: {e}")
            return context

    def _compress_with_openai(self, context: str, query: str) -> str:
        """
        Fallback to OpenAI (mock implementation - passthrough for now to avoid accidental costs)
        """
        logger.warning(f"⚠️ OpenAI compression not fully implemented to save costs. Returning raw context.")
        return context


# Global instance
_compressor = None

def get_context_compressor() -> ContextCompressor:
    global _compressor
    if _compressor is None:
        _compressor = ContextCompressor()
    return _compressor
