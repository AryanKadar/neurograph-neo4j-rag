# Plan Part 1: Strategy & Setup

## 1. Objective
Replace the current "Recursive Character" chunking with "Agentic Semantic" chunking.
- **Current**: Blindly splits text every N characters.
- **Goal**: Use GPT-5 (via Azure) to read the text and decide where to cut based on topic shifts.

## 2. The Strategy: "Proposition-Based Semantic Boundary Detection"
We will not just use a pre-made library function because we want control over the cost and the prompt. We will implement a custom `AgenticTextChunker` class.

### How it works:
1.  **Pre-segmentation**: We first split the document into "atomic units" (sentences) using a cheap rule-based splitter.
2.  **Context Window**: We feed a window of these sentences (e.g., 20 at a time) to the LLM.
3.  **The "Agent"**: We ask the LLM: *"Here are 20 sentences. Identify the range of sentences that belong to the same topic. Return the start and end indices."*
4.  **Aggregation**: We merge the sentences based on the LLM's boundaries to form the final chunks.

## 3. Configuration Changes
We need to update `.env` and `settings.py` to control this feature, as it is slower and costs money (unlike recursive).

### New Environment Variables (.env)
```ini
# Chunking Strategy: 'recursive' (default) or 'agentic'
CHUNKING_STRATEGY=agentic

# Agentic Settings
# How many "surrounding" sentences to give the LLM for context
AGENTIC_WINDOW_SIZE=20 
```

### Updates to `settings.py`
We will add these fields to the `Settings` class to make them accessible throughout the specific services.

## 4. Dependencies
We will use:
-   `langchain_text_splitters`: Already installed. We will use it for the initial sentence splitting (the "atomic" step).
-   `openai`: Already installed. Used for the agentic reasoning.

## 5. Pros & Cons to Accept
| Feature | Recursive (Current) | Agentic (New) |
| :--- | :--- | :--- |
| **Speed** | < 1 second | ~5-10 seconds per page |
| **Cost** | $0 | Azure Token Costs (Input + Output) |
| **Accuracy** | Splinters context | **Preserves complete ideas** |
