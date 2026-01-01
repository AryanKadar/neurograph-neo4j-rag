# Plan Part 3: Integration & Migration

## 1. Modifying `chunking.py`
We will keep the existing `TextChunker` (recursive) class but rename it to `RecursiveChunker` for clarity, or just keep it as is.
We will add a factory function:

```python
def get_text_chunker():
    """Factory to return the correct chunker based on settings"""
    if settings.CHUNKING_STRATEGY == "agentic":
        return AgenticTextChunker()
    else:
        return RecursiveTextChunker()
```

This ensures that `document_processor.py` doesn't need to change its Logic, only its dependency.

## 2. Modifying `document_processor.py`
No major logic changes needed here if we use the Factory pattern above! The `process_document` function calls `get_text_chunker()`. It will automatically receive the Agentic one if config is set.

## 3. Migration (Re-indexing)
Since "chunks" are the fundamental unit of your Vector DB, you cannot "convert" old chunks to new ones. You must re-create them.

**Action Plan for User:**
1.  **Clear Vector DB**: Delete `chunks.json` (or rename it to `chunks_backup.json`).
2.  **Re-upload**: Re-upload your documents. The new pipeline will process them using the Agentic Chunker.

## 4. Testing Plan
1.  **Unit Test**: Create `test_agentic_chunking.py`.
    -   Feed it a dummy text: "Apples are red. They grow on trees. \n\n Cars are fast. They have engines."
    -   Assert that it creates exactly 2 chunks (one for Apples, one for Cars).
2.  **Integration Test**: Upload a real PDF and check the logs to see:
    -   `Combining sentences 0-5 into Chunk 1`
    -   `Combining sentences 6-10 into Chunk 2`
