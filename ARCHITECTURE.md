# 🏗️ Architecture Documentation

## Table of Contents
- [System Overview](#system-overview)
- [Modular Design](#modular-design)
- [Chunking Strategies](#chunking-strategies)
- [Vector Search Architecture](#vector-search-architecture)
- [RAG Pipeline](#rag-pipeline)
- [Data Flow](#data-flow)
- [API Design](#api-design)

---

## System Overview

This is an **Advanced Modular RAG (Retrieval-Augmented Generation)** system that combines modern AI techniques to deliver context-aware conversational responses.

```
┌─────────────────────────────────────────────────────────────────┐
│                  Advanced Modular RAG Chatbot                   │
└─────────────────────────────────────────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               │                               │
       ┌───────▼────────┐           ┌─────────▼─────────┐
       │   Frontend      │           │     Backend       │
       │   (React +      │◄─────────►│   (FastAPI +      │
       │   TypeScript)   │   REST    │    Python)        │
       └────────────────┘   API      └──────────┬────────┘
                                                │
                     ┌──────────────────────────┼─────────────────┐
                     │                          │                 │
            ┌────────▼────────┐       ┌────────▼────────┐  ┌────▼──────┐
            │  Azure OpenAI   │       │  FAISS Vector   │  │  Document │
            │   GPT-5 API     │       │     Store       │  │  Processor│
            │  (Chat + Embed) │       │   (HNSW Index)  │  │  (Chunker)│
            └─────────────────┘       └─────────────────┘  └───────────┘
```

### Key Components
1. **Frontend**: React-based UI with real-time streaming
2. **Backend**: FastAPI async server with modular services
3. **LLM**: Azure OpenAI GPT-5 for chat and embeddings
4. **Vector DB**: FAISS with HNSW indexing
5. **Document Processing**: Multi-strategy chunking pipeline

---

## Modular Design

### Design Principles
The system follows the **Strategy Pattern** and **Dependency Injection** to enable:
- ✅ **Pluggability**: Swap components without changing core logic
- ✅ **Testability**: Mock services for unit testing
- ✅ **Scalability**: Add new strategies without breaking existing code
- ✅ **Maintainability**: Clear separation of concerns

### Service Architecture

```
Backend/
├── services/
│   ├── chunking.py           # Text chunking strategies
│   │   ├── RecursiveTextChunker
│   │   ├── AgenticTextChunker
│   │   └── get_text_chunker()  # Factory function
│   │
│   ├── embeddings.py         # Embedding generation
│   │   └── EmbeddingService
│   │
│   ├── vector_store.py       # FAISS operations
│   │   └── VectorStore
│   │
│   ├── chat_service.py       # RAG chat logic
│   │   └── ChatService
│   │
│   └── response_formatter.py # Response post-processing
│       └── ResponseFormatter
│
├── api/
│   ├── chat.py              # Chat endpoints
│   └── upload.py            # Document upload
│
├── config/
│   └── settings.py          # Centralized configuration
│
└── utils/
    ├── logger.py            # Logging utilities
    └── file_handler.py      # File operations
```

---

## Chunking Strategies

The system implements **two distinct chunking strategies** that can be switched via configuration:

### Strategy 1: Recursive Character Chunking

**When to use**: 
- Large document volumes
- Speed is critical
- Consistent, predictable chunking needed

**How it works**:
```
1. Start with full document
2. Try splitting on paragraph breaks (\n\n)
3. If chunks still too large, split on sentences (. )
4. If still too large, split on words ( )
5. Apply overlap between chunks
```

**Parameters**:
```python
CHUNK_SIZE = 1000        # Target tokens per chunk
CHUNK_OVERLAP = 200      # Overlap in tokens
MIN_CHUNK_SIZE = 100     # Discard smaller chunks
```

**Advantages**:
- ⚡ Fast processing
- 📏 Consistent chunk sizes
- 🎯 Preserves context with overlap
- 💰 No API costs

**Code Flow**:
```python
RecursiveTextSplitter(
    separators=["\n\n", "\n", ". ", ", ", " ", ""],
    chunk_size=4000,    # chars (approx 1000 tokens)
    chunk_overlap=800   # chars (approx 200 tokens)
)
```

---

### Strategy 2: Agentic Chunking (LLM-Powered)

**When to use**:
- Quality over speed
- Complex, multi-topic documents
- Need semantic coherence

**How it works**:
```
1. Split text into atomic sentences
2. Format sentences in TOON (Token-Oriented Object Notation)
3. Pass batches to GPT-5 for topic boundary detection
4. LLM returns indices where new topics start
5. Merge sentences between breakpoints into chunks
```

**TOON Format Example**:
```
{index, content}
[5]
0   The Earth orbits the Sun.
1   This takes approximately 365 days.
2   Mars is the next planet out.
3   It has two moons named Phobos and Deimos.
4   The asteroid belt lies between Mars and Jupiter.
```

**Parameters**:
```python
AGENTIC_WINDOW_SIZE = 20  # Sentences per batch
```

**LLM Prompt**:
```
System: You are an expert Document Segmenter. 
        Identify logical breakpoints where a NEW topic 
        or distinct sub-topic begins.
        Output ONLY a JSON list of indices (e.g. [0, 5, 12]).

User: Analyze these sentences provided in TOON format:
      <TOON formatted text>
      Return valid start indices for new chunks.
```

**Advantages**:
- 🧠 Semantic awareness
- 🎯 Topic coherence
- 📚 Better for complex documents
- 🔍 Improves retrieval quality

**Trade-offs**:
- 💰 API costs (GPT calls per window)
- ⏱️ Slower processing
- 🔌 Requires internet connection

**Code Flow**:
```python
1. _split_into_sentences(text)
   └─> LangChain RecursiveCharacterTextSplitter
       with sentence separators

2. _find_breakpoints(sentences)
   └─> Batch sentences into windows
       └─> For each window:
           ├─> _format_sentences_to_toon()
           ├─> Call GPT-5 API
           └─> Extract breakpoint indices

3. _merge_sentences(sentences, breakpoints)
   └─> Combine sentences between breakpoints
   └─> Filter by minimum size
```

---

## Vector Search Architecture

### FAISS with HNSW

**FAISS** (Facebook AI Similarity Search) is a library for efficient similarity search and clustering of dense vectors.

**HNSW** (Hierarchical Navigable Small World) is a graph-based algorithm for approximate nearest neighbor search.

### How HNSW Works

```
Layer 2 (Top):    A ──────────────── B
                  │                   │
                  │                   │
Layer 1:          A ──── C ──── D ──── B
                  │      │      │      │
                  │      │      │      │
Layer 0 (Base):   A ── C ─ E ─ D ─ F ─ B ─ G
```

**Search Process**:
1. Start at top layer
2. Navigate to closest neighbor
3. Drop down a layer
4. Repeat until reaching base layer
5. Return nearest k neighbors

### Configuration Parameters

```python
HNSW_M = 32
# Number of bi-directional links per node
# Higher M = Better recall, more memory
# Recommended: 16-64

HNSW_EF_CONSTRUCTION = 200
# Dynamic candidate list size during INDEX BUILD
# Higher = Better quality index, slower build
# Recommended: 100-500

HNSW_EF_SEARCH = 100
# Dynamic candidate list size during SEARCH
# Higher = Better accuracy, slower search
# Recommended: 50-200
```

### Performance Characteristics

| Vectors | M | EF_Search | QPS | Recall@10 |
|---------|---|-----------|-----|-----------|
| 10K     | 32| 100       | 5000| 95%       |
| 100K    | 32| 100       | 3000| 93%       |
| 1M      | 48| 150       | 1500| 95%       |

### Embedding Dimensions

**Azure OpenAI `text-embedding-ada-002`**:
- Dimension: 1536
- Use case: Production, best quality
- Cost: $0.0001 / 1K tokens

**Local `all-mpnet-base-v2`**:
- Dimension: 768
- Use case: Development, cost-sensitive
- Cost: Free (runs locally)

---

## RAG Pipeline

### Full Document Processing Flow

```
┌─────────────┐
│ User Uploads│
│  Document   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Document Parser     │
│ (PDF/DOCX/TXT/MD)  │
└──────┬──────────────┘
       │ Raw Text
       ▼
┌─────────────────────┐
│  Text Chunker       │
│  ┌──────────────┐  │
│  │  Recursive   │  │
│  │     or       │  │◄── CHUNKING_STRATEGY
│  │   Agentic    │  │
│  └──────────────┘  │
└──────┬──────────────┘
       │ Chunks []
       ▼
┌─────────────────────┐
│ Embedding Service   │
│ (Azure OpenAI /     │
│  Sentence Trans.)   │
└──────┬──────────────┘
       │ Embeddings []
       ▼
┌─────────────────────┐
│ Vector Store        │
│ (FAISS HNSW)        │
│ - Add vectors       │
│ - Save index        │
└──────┬──────────────┘
       │ Stored
       ▼
   ✅ Ready for queries
```

### Query Processing Flow

```
┌─────────────┐
│ User Query  │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Embedding Service   │
│ (Embed query)       │
└──────┬──────────────┘
       │ Query Vector
       ▼
┌─────────────────────┐
│ Vector Store        │
│ HNSW Search         │
│ - Find top-k        │
│ - Filter by score   │
└──────┬──────────────┘
       │ Retrieved Chunks
       ▼
┌─────────────────────┐
│ Context Builder     │
│ - Combine chunks    │
│ - Format context    │
└──────┬──────────────┘
       │ Context String
       ▼
┌─────────────────────┐
│ Prompt Constructor  │
│ System + Context +  │
│ User Query          │
└──────┬──────────────┘
       │ Final Prompt
       ▼
┌─────────────────────┐
│ Azure OpenAI GPT-5  │
│ (Streaming)         │
└──────┬──────────────┘
       │ Tokens
       ▼
┌─────────────────────┐
│ Response Formatter  │
│ - Structure         │
│ - Markdown          │
└──────┬──────────────┘
       │
       ▼
┌─────────────┐
│   User UI   │
└─────────────┘
```

### Prompt Template

```python
SYSTEM_PROMPT = """
You are a helpful AI assistant with access to document context. 
Answer questions based on the provided context when available.
If the context doesn't contain relevant information, say so.
Format responses professionally with markdown.
"""

CONTEXT_INJECTION = """
### Relevant Context:
{retrieved_chunks}

---

### User Question:
{user_query}
"""
```

---

## Data Flow

### Document Upload API Flow

```python
POST /api/upload
├─> Validate file type
├─> Save to uploads/
├─> Parse document
│   ├─> PDF: PyPDF2
│   ├─> DOCX: python-docx
│   └─> TXT/MD: Direct read
├─> Chunk text (strategy-dependent)
├─> Generate embeddings (batch)
├─> Add to FAISS index
└─> Return success + chunk count
```

### Chat API Flow

```python
POST /api/chat/stream
├─> Receive user message
├─> Embed query
├─> Search FAISS (top-k=5)
├─> Build context from chunks
├─> Construct prompt
├─> Stream GPT-5 response
│   └─> Server-Sent Events (SSE)
└─> Format and send tokens
```

---

## API Design

### REST Endpoints

#### Chat Endpoints

**1. Standard Chat**
```http
POST /api/chat
Content-Type: application/json

{
  "message": "What is retrieval-augmented generation?",
  "conversation_id": "uuid-v4",
  "use_rag": true
}

Response:
{
  "response": "Retrieval-Augmented Generation (RAG) is...",
  "conversation_id": "uuid-v4",
  "sources": ["chunk_id_1", "chunk_id_2"],
  "metadata": {
    "model": "gpt-5-chat",
    "tokens_used": 234,
    "retrieval_time_ms": 45
  }
}
```

**2. Streaming Chat**
```http
POST /api/chat/stream
Content-Type: application/json

{
  "message": "Explain FAISS HNSW",
  "conversation_id": "uuid-v4"
}

Response: (Server-Sent Events)
data: {"type": "token", "content": "FAISS"}
data: {"type": "token", "content": " is"}
data: {"type": "token", "content": " a"}
...
data: {"type": "done"}
```

#### Upload Endpoints

```http
POST /api/upload
Content-Type: multipart/form-data

file: document.pdf

Response:
{
  "filename": "document.pdf",
  "chunks_created": 42,
  "embedding_dimension": 1536,
  "chunking_strategy": "agentic",
  "processing_time_ms": 3421,
  "status": "success"
}
```

#### Health Check

```http
GET /api/health

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "vector_store": {
    "total_vectors": 1234,
    "dimension": 1536
  },
  "services": {
    "azure_openai": "connected",
    "vector_store": "loaded"
  }
}
```

---

## Technology Stack

### Backend
- **FastAPI**: Modern async web framework
- **Uvicorn**: ASGI server with WebSocket support
- **Pydantic**: Data validation and settings
- **Azure OpenAI SDK**: LLM and embeddings
- **FAISS**: Vector similarity search
- **LangChain**: Text splitting utilities
- **Sentence Transformers**: Local embeddings (optional)

### Frontend
- **React 18**: UI library with hooks
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool with HMR
- **Axios**: HTTP client with streaming
- **CSS3**: Custom cosmic animations

### Infrastructure
- **Azure OpenAI**: Managed GPT-5 API
- **FAISS**: In-memory vector store with disk persistence
- **File System**: Local document and index storage

---

## Performance Optimization

### Async Operations
```python
# All I/O operations are async
async def process_document(file):
    text = await parse_document(file)
    chunks = await chunk_text(text)
    embeddings = await generate_embeddings(chunks)
    await store_vectors(embeddings)
```

### Batch Processing
```python
# Embed chunks in batches
BATCH_SIZE = 32
for i in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[i:i+BATCH_SIZE]
    embeddings = await embed_batch(batch)
```

### Caching
- FAISS index loaded once at startup
- Chunker instance singleton
- Embedding model loaded once

---

## Security Considerations

1. **API Key Management**: Environment variables only
2. **CORS**: Configured allowed origins
3. **File Upload**: Type and size validation
4. **Input Sanitization**: Pydantic models
5. **Rate Limiting**: (Future enhancement)

---

## Deployment Architecture

### Development
```
Local Machine
├── Backend: http://localhost:8000
└── Frontend: http://localhost:3000
```

### Production (Example)
```
┌─────────────────────┐
│   Frontend (Vercel) │
│   https://app.com   │
└──────────┬──────────┘
           │ HTTPS
           ▼
┌─────────────────────┐
│ Backend (Azure App) │
│ https://api.app.com │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Azure OpenAI API   │
└─────────────────────┘
```

---

## Monitoring & Logging

### Structured Logging
```python
logger.info(f"✂️ Recursive chunking: {len(text)} chars")
logger.info(f"🧠 Agentic chunking: Generated {len(chunks)} chunks")
logger.info(f"📊 Vector search: {top_k} results in {latency}ms")
```

### Metrics to Track
- Document processing time
- Chunking strategy performance
- Vector search latency
- API token usage
- Error rates

---

**Last Updated**: 2026-01-01  
**Version**: 1.0  
**Author**: Aryan Kadar
