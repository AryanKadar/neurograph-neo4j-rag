# Plan Part 2: Agentic Chunker Implementation

## 1. The Class Structure
We will create a new class `AgenticTextChunker` in `Backend/services/chunking.py`.

```python
class AgenticTextChunker:
    def __init__(self):
        self.client = AzureOpenAI(...) # Use existing settings
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME

    def chunk_text(self, text: str) -> List[str]:
        # 1. Split into atomic sentences
        sentences = self._split_into_sentences(text)
        
        # 2. Identify breakpoints via LLM
        breakpoints = self._find_breakpoints(sentences)
        
        # 3. Merge sentences into chunks based on breakpoints
        return self._merge_sentences(sentences, breakpoints)
```

## 2. The Prompt Engineering (The "Agent")
This is the most critical part. We need a prompt that is robust but uses minimal tokens.

**System Prompt:**
> "You are an expert Document Segmenter. Your job is to identify logical topic breaks in a sequence of sentences."

**User Prompt:**
> "Here are {N} sentences from a document, labeled by index:
> [0] First sentence...
> [1] Second sentence...
> ...
> Identify the indices where a NEW distinct topic or sub-topic begins.
> Return ONLY a JSON list of indices, e.g., [0, 5, 12]. Always include 0."

## 3. Detailed Logic Flow

### A. Sentence Splitting
We will use `RecursiveCharacterTextSplitter` with `chunk_size=100` (very small) and separators `["\n", ". ", "? ", "! "]` to get rough sentence-like objects. This is safer than regex and doesn't require downloading heavy NLTK models.

### B. The Sliding Window Problem
If a document has 500 sentences, we can't fit them all in one context window (or it might be too confusing).
**Solution:** We process in batches of 20-30 sentences.
- Batch 1: Sentences 0-29. LLM finds breaks.
- We might need a small overlap (e.g., provide sentences 25-30 as context for the next batch) to ensure we don't miss a break right at the edge, but for simplicity, we will start with strict batching first.

### C. Reconstruction
- If LLM returns breaks at `[0, 5, 12]`:
    - Chunk 1 = Sentences 0 to 4 joined.
    - Chunk 2 = Sentences 5 to 11 joined.
    - Chunk 3 = Sentences 12 to end.

## 4. Error Handling
- **Fallback**: If the LLM returns invalid JSON or times out, we must fall back to the standard `RecursiveCharacterTextSplitter` for that specific document to prevent the pipeline from crashing.
