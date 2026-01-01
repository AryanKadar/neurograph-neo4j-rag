"""
═══════════════════════════════════════════════════════════════
 🌌 COSMIC AI - Text Chunker (Recursive & Agentic)
═══════════════════════════════════════════════════════════════
"""

import json
import re
from typing import List, Dict
from openai import AzureOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger()


class RecursiveTextChunker:
    """
    ┌─────────────────────────────────────────────┐
    │  ✂️ Recursive text chunking                 │
    │  Preserves semantic boundaries              │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self):
        # Approximate tokens per character (rough estimate)
        chunk_size_chars = settings.CHUNK_SIZE * 4
        chunk_overlap_chars = settings.CHUNK_OVERLAP * 4
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size_chars,
            chunk_overlap=chunk_overlap_chars,
            length_function=len,
            separators=["\n\n", "\n", ". ", ", ", " ", ""],
            keep_separator=True
        )
        
        logger.info(f"✂️ RecursiveTextChunker initialized")
    
    def chunk_text(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        
        logger.info(f"✂️ Recursive chunking: {len(text)} chars")
        chunks = self.splitter.split_text(text)
        
        # Post-process
        processed_chunks = []
        min_chunk_chars = settings.MIN_CHUNK_SIZE * 4
        
        for chunk in chunks:
            chunk = " ".join(chunk.split())
            if len(chunk) < min_chunk_chars:
                continue
            processed_chunks.append(chunk)
            
        return processed_chunks


class AgenticTextChunker:
    """
    ┌─────────────────────────────────────────────┐
    │  🧠 Agentic Semantic Chunking               │
    │  Uses LLM to find topic boundaries          │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_API_BASE
        )
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        
        # Helper splitter for "atomic" sentences (step 1)
        self.sentence_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, # Large enough to hold a few sentences if needed, but we rely on separators
            chunk_overlap=0,
            separators=["\n\n", "\n", ". ", "? ", "! "],
            keep_separator=True
        )
        
        logger.info(f"🧠 AgenticTextChunker initialized")

    def _format_sentences_to_toon(self, sentences: List[str], start_index: int) -> str:
        """
        Convert sentence list to TOON format for the prompt
        {index, content}
        [N]
        0   First sentence...
        """
        toon = "{index, content}\n"
        toon += f"[{len(sentences)}]\n"
        
        for i, sent in enumerate(sentences):
            # Clean content for strict tab separation
            clean_sent = sent.replace("\n", " ").replace("\t", " ").strip()
            # Truncate slightly if massive to save tokens in prompt input
            if len(clean_sent) > 200:
                clean_sent = clean_sent[:200] + "..."
            
            global_index = start_index + i
            toon += f"{global_index}\t{clean_sent}\n"
            
        return toon

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into atomic units (roughly sentences)"""
        # We use LangChain's splitter but tuned for sentences
        # This keeps the punctuation attached
        raw_splits = self.sentence_splitter.split_text(text)
        
        # Clean up
        sentences = [s.strip() for s in raw_splits if s.strip()]
        return sentences

    def _find_breakpoints(self, sentences: List[str]) -> List[int]:
        """
        Ask LLM to identify start indices of new topics using Sliding Window
        """
        breakpoints = {0} # Always start at 0
        window_size = settings.AGENTIC_WINDOW_SIZE
        
        total_sentences = len(sentences)
        logger.info(f"   └─ Identifying topics in {total_sentences} sentences...")
        
        # Process in batches
        for i in range(0, total_sentences, window_size):
            batch = sentences[i : i + window_size]
            if not batch:
                continue
                
            # Prepare TOON input
            toon_input = self._format_sentences_to_toon(batch, start_index=i)
            
            system_prompt = (
                "You are an expert Document Segmenter. "
                "Identify logical breakpoints where a NEW topic or distinct sub-topic begins.\n"
                "Output ONLY a JSON list of indices (e.g. [0, 5, 12])."
            )
            
            user_prompt = (
                f"Analyze these sentences provided in TOON format:\n\n"
                f"{toon_input}\n\n"
                f"Return valid start indices for new chunks. "
                f"Always include the first index {i} if it starts a thought."
            )
            
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    max_tokens=100
                )
                
                content = response.choices[0].message.content.strip()
                
                # Extract JSON from potential markdown wrappers
                match = re.search(r"\[.*\]", content, re.DOTALL)
                if match:
                    indices = json.loads(match.group())
                    # Validate indices are within this batch's range
                    valid_indices = [idx for idx in indices if i <= idx < i + window_size]
                    breakpoints.update(valid_indices)
                    logger.info(f"      └─ Batch {i}-{i+window_size}: Found breaks at {valid_indices}")
                
            except Exception as e:
                logger.error(f"⚠️ Agentic chunking error on batch {i}: {e}")
                # Fallback: Just add the batch start as a breakpoint to keep things safe
                breakpoints.add(i)
        
        return sorted(list(breakpoints))

    def _merge_sentences(self, sentences: List[str], breakpoints: List[int]) -> List[str]:
        """Reconstruct chunks from breakpoints"""
        chunks = []
        breakpoints = sorted(list(set(breakpoints)))
        
        # Ensure 0 is the first start
        if 0 not in breakpoints:
            breakpoints.insert(0, 0)
            
        # Add the end sentinel
        breakpoints.append(len(sentences))
        
        for k in range(len(breakpoints) - 1):
            start = breakpoints[k]
            end = breakpoints[k+1]
            
            # Combine range [start, end)
            chunk_text = " ".join(sentences[start:end])
            
            # Filter huge chunks or tiny noise
            if len(chunk_text) > 50: # valid minimal size
                chunks.append(chunk_text)
                
        return chunks

    def chunk_text(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
            
        logger.info(f"🧠 Agentic chunking: {len(text)} chars")
        
        # 1. Atomic Split
        sentences = self._split_into_sentences(text)
        if not sentences:
            return []
            
        # 2. Find semantic breaks
        breakpoints = self._find_breakpoints(sentences)
        
        # 3. Merge
        final_chunks = self._merge_sentences(sentences, breakpoints)
        
        logger.info(f"   └─ Generated {len(final_chunks)} semantic chunks")
        return final_chunks


# Global chunker instance
_text_chunker = None

def get_text_chunker():
    """Get or create text chunker singleton based on config"""
    global _text_chunker
    
    # Reset if strategy changed (simple way to handle dynamic config if needed, though usually static)
    # But for a singleton pattern, we usually instantiate once.
    # To support switching strategies via restart, this is fine.
    
    if _text_chunker is None:
        strategy = settings.CHUNKING_STRATEGY
        if strategy == "agentic":
            _text_chunker = AgenticTextChunker()
        else:
            _text_chunker = RecursiveTextChunker()
            
    return _text_chunker
