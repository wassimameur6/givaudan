# Givaudan Knowledge Portal

A RAG (Retrieval-Augmented Generation) system for accessing Givaudan's knowledge base on perfumes, aromas, laboratories, and products.

## Overview

This is a **RAG system** featuring:
- **Weaviate Vector Database**: Distributed, persistent storage
- **Hybrid Search**: BM25 (40%) + Dense vectors (60%) for optimal retrieval
- **Cross-Encoder Reranking**: ms-marco-MiniLM for precision improvement
- **ReAct Agent Pattern**: Autonomous reasoning with 2 specialized tools
- **Semantic Caching**: 90% faster responses on cache hits
- **Conversation Memory**: Context-aware multi-turn conversations

## Key Features

### Core Capabilities
- **Advanced Retrieval**: Hybrid search (BM25 + Dense) with cross-encoder reranking
- **ReAct Agent**: 2 specialized tools (Vector Database Search, Web Search)
- **Rich Metadata**: Document metadata for source tracking and context
- **Performance Optimized**: Semantic caching, conversation memory
- **Infrastructure**: Docker containerization, persistent storage, FastAPI backend
- **Modern UI**: Clean, responsive frontend with dark mode and conversation history

### Performance Metrics
```
Query Time (cached):    < 2s    (90% faster than uncached)
Query Time (uncached):  10-15s  (ReAct agent reasoning + retrieval)
Semantic Caching:       Similarity threshold 0.88
Hybrid Search:          60% Dense vectors + 40% BM25
Retrieval:              Top 10 candidates → Rerank → Top 3 final
LLM Model:              gpt-4o-mini (consistent for all queries)
```

## Architecture

```
User Query
    ↓
[Conversational Check] → Greeting? Return instant response
    ↓
[Semantic Cache] → Cache Hit? Return in < 2s
    ↓ Cache Miss
[Model Router] → Select model based on query complexity
    ↓
[ReAct Agent - LangChain]
    ↓
[Reasoning + Tool Selection]
    ├─→ [Vector Database Tool] → Weaviate Hybrid Search
    │   ↓
    │   BM25 (40%) + Dense (60%) → Top 10 candidates
    │   ↓
    │   [Cross-Encoder Reranking] → Top 3 results
    │
    └─→ [Web Search Tool] → SerpAPI (for recent info)
    ↓
[LLM Generation with Context + Conversation History]
    ↓
[Cache Result] → Store for future similar queries
    ↓
Final Answer (with metadata)
```

## Quick Start

### Prerequisites
- Python 3.9+
- Docker (for Weaviate)
- OpenAI API key
- (Optional) SerpAPI key for web search

### Installation

1. **Clone and setup environment**
```bash
cd gigi
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
# or using poetry:
poetry install
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your API keys:
# OPENAI_API_KEY=sk-...
# SERPAPI_API_KEY=... (optional, for web search)
```

4. **Start Weaviate (Docker)**
```bash
docker run -d \
  --name weaviate-givaudan \
  -p 8090:8080 \
  -p 50051:50051 \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -e QUERY_DEFAULTS_LIMIT=25 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e DEFAULT_VECTORIZER_MODULE=none \
  -e ENABLE_MODULES='' \
  -e CLUSTER_HOSTNAME='node1' \
  semitechnologies/weaviate:1.27.1
```

5. **Start the API**
```bash
# Development
python -m uvicorn api.main:app --reload --port 8001

# Deployment
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

6. **Access the frontend**
```bash
# Open frontend/index.html in your browser
# or serve it with a simple HTTP server:
cd frontend
python -m http.server 3000
# Then visit: http://localhost:3000
```

## API Usage

### Endpoints

#### GET `/` - API homepage
```bash
curl http://localhost:8001/
```

#### GET `/health` - Health check
```bash
curl http://localhost:8001/health
```

#### GET `/system` - System information
```bash
curl http://localhost:8001/system
```

#### POST `/chat` - Ask a question
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Où se trouvent les laboratoires Givaudan ?",
    "chat_history": []
  }'
```

### Response Format
```json
{
  "question": "Où se trouvent les laboratoires Givaudan ?",
  "answer": "Givaudan possède des laboratoires...",
  "cache_hit": false,
  "processing_time": 12.5,
  "model_used": "gpt-4o-mini",
  "chat_history": [...]
}
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Vector DB** | Weaviate 1.27.1 | Vector storage |
| **Embeddings** | BGE-large-en-v1.5 | Retrieval embeddings (1024-dim) |
| **LLM** | GPT-4o-mini | Generation model (all queries) |
| **Retrieval** | Hybrid (BM25 + Dense) | Keyword + semantic search (60/40 split) |
| **Reranking** | ms-marco-MiniLM-L-6-v2 | Cross-encoder precision boost |
| **Agent** | ReAct (LangChain) | Reasoning + tool selection |
| **Caching** | SQLite + Embeddings | Semantic similarity caching (0.88 threshold) |
| **Web Search** | SerpAPI | Real-time web information |
| **API** | FastAPI | Async REST API (port 8001) |
| **Frontend** | Vanilla JS + CSS | Modern responsive UI with dark mode |

## Project Structure

```
gigi/
├── api/
│   ├── __init__.py
│   └── main.py                    # FastAPI backend (port 8001)
├── data/
│   ├── raw/                       # Knowledge base documents
│   └── semantic_cache.db          # Query cache (SQLite)
├── frontend/
│   ├── app.js                     # Frontend logic + API calls
│   ├── index.html                 # Main UI
│   ├── styles.css                 # Styling + dark mode
│   └── givaudan-logo.png          # Branding
├── src/
│   ├── __init__.py
│   ├── react_agent.py              # ReAct agent (2 tools)
│   ├── weaviate_rag_pipeline.py   # Hybrid search + reranking
│   ├── semantic_cache.py          # Semantic caching (0.88 threshold)
│   ├── web_agent.py               # SerpAPI web search
│   ├── document_loader.py         # Multi-format loader (TXT/PDF/DOCX/MD)
│   ├── optimizations.py           # Model routing + cascading
│   ├── config.py                  # Configuration settings
│   └── utils.py                   # Logging + utilities
├── outputs/                       # Generated comparison reports
├── .env                           # API keys (not in git)
├── .env.example                   # Environment template
├── .gitignore
├── pyproject.toml                 # Poetry dependencies
├── poetry.lock
├── requirements.txt               # Pip dependencies
└── README.md                      # This file
```

## Configuration

Edit `src/config.py` to customize:

```python
# LLM Model
LLM_MODEL = "gpt-4o-mini"          # Single model for all queries

# Weaviate Settings
WEAVIATE_URL = "http://localhost:8090"
WEAVIATE_TOP_K_RETRIEVE = 10       # Initial candidates
WEAVIATE_TOP_K_FINAL = 3           # After reranking
WEAVIATE_HYBRID_ALPHA = 0.6        # 60% dense vectors, 40% BM25

# Agent Settings
AGENT_MAX_ITERATIONS = 10          # Max ReAct reasoning steps
AGENT_MAX_EXECUTION_TIME = 60      # Timeout in seconds

# Semantic Cache Settings
CACHE_SIMILARITY_THRESHOLD = 0.88  # Min similarity for cache hit
CACHE_ENABLED = True               # Enable/disable caching
```

## System Components

### 2 Specialized Tools

1. **VectorSearchTool** (`search_vector_database`)
   - Searches Weaviate for Givaudan knowledge
   - Hybrid search: BM25 + Dense vectors
   - Returns top 3 documents after reranking
   - Used for: Product info, laboratory locations, technical data

2. **WebSearchTool** (`search_web`)
   - SerpAPI integration for real-time web search
   - Used for: Recent news, current events only
   - Fallback when vector DB has no results

### Agent Flow

The ReAct agent follows this pattern:
1. **Reasoning**: Analyze the question
2. **Action**: Select appropriate tool (VectorDB or Web)
3. **Observation**: Process tool results
4. **Decision**: Answer or iterate (max 10 iterations)

### Conversation Memory

- Keeps last 6 messages (3 exchanges) for context
- Enables follow-up questions and references
- Minimal token overhead (~200-400 tokens)
- Stored in chat_history array per conversation

## Key Features Implemented

### Weaviate Integration
- Vector database with automatic persistence
- No manual indexing needed after first setup
- Hybrid search combining keyword (BM25) and semantic (dense vectors)

### Cross-Encoder Reranking
- Initial retrieval: 10 candidates from hybrid search
- Reranking: ms-marco-MiniLM cross-encoder
- Final output: Top 3 most relevant documents

### Semantic Caching
- SQLite-based cache with embedding similarity
- Threshold: 0.88 similarity for cache hit
- Returns cached results in < 2s vs 10-15s for fresh queries


### Conversation Memory
- Maintains last 6 messages for context
- Enables natural follow-up questions
- Format: "Conversation précédente: User: ... Assistant: ..."

### Modern UI
- Clean, responsive design with dark mode
- Conversation history in sidebar
- Real-time loading indicators
- Givaudan branding throughout

## Testing

### Check Weaviate Status
```bash
# Check if container is running
docker ps --filter "name=weaviate-givaudan"

# Check Weaviate health
curl http://localhost:8090/v1/meta
```

### Test API
```bash
# Health check
curl http://localhost:8001/health

# Test query
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Où sont les laboratoires Givaudan ?"}'

# Check cache
sqlite3 data/semantic_cache.db "SELECT COUNT(*) FROM cache;"
```

### Example Questions
- "Où se trouvent les laboratoires Givaudan ?"
- "Qu'est-ce que Myrissi ?"
- "Explique la pyramide olfactive"
- "Quels sont les principaux métiers de Givaudan ?"

## Troubleshooting

### Weaviate not running
```bash
docker start weaviate-givaudan
# or create new container:
# see installation step 4
```

### Port already in use
```bash
# Find process using port 8001
lsof -i :8001
# Kill if needed
kill -9 <PID>
```

### Clear cache
```bash
rm data/semantic_cache.db
```

### Re-index documents
Delete Weaviate container and recreate:
```bash
docker stop weaviate-givaudan
docker rm weaviate-givaudan
# Then recreate (see installation step 4)
```

## Additional Resources

- **API Documentation** - Visit `http://localhost:8001/docs` (FastAPI auto-docs)
- **Frontend** - Access at `http://localhost:3000`
- **Weaviate Console** - `http://localhost:8090/v1/meta` (health check)

## Technical Design Decisions

### Why Weaviate?
- Vector database with Docker deployment
- Native hybrid search (BM25 + Dense vectors)
- Automatic persistence (no manual saves needed)
- CRUD operations built-in
- Scalable architecture

### Why Hybrid Search (60% Dense / 40% BM25)?
- Dense vectors: Semantic understanding
- BM25: Exact keyword matching
- Combined: Best of both worlds
- Alpha=0.6 balances semantic and lexical retrieval

### Why Cross-Encoder Reranking?
- Bi-encoders (BGE): Fast initial retrieval
- Cross-encoders: Accurate re-scoring
- Pipeline: Retrieve 10 candidates → Rerank → Keep top 3
- Improves precision without sacrificing speed

### Why Semantic Caching?
- Recognizes similar questions (not just exact matches)
- Threshold 0.88 balances recall and precision
- Cache hits < 2s vs uncached 10-15s
- Significant user experience improvement

### Why ReAct Agent?
- Autonomous tool selection (Vector DB vs Web)
- Reasoning traces for debugging
- Handles complex multi-step queries
- LangChain integration for maintainability


## Summary

This RAG system implements:
- **Weaviate** for vector storage
- **Hybrid Search** (BM25 + Dense) for better retrieval
- **Cross-Encoder Reranking** for precision
- **ReAct Agent** with 2 tools (VectorDB, Web)
- **Semantic Caching** for speed optimization
- **Conversation Memory** for multi-turn dialogs
- **Modern UI** with Givaudan branding
- **Single LLM** (gpt-4o-mini) for consistent quality

**Stack**: Python + FastAPI + Weaviate + LangChain + Vanilla JS
