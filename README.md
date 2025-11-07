# Givaudan Knowledge Portal

A RAG (Retrieval-Augmented Generation) system for accessing Givaudan's knowledge base on perfumes, aromas, laboratories, and products.

## Features

- **Weaviate Vector Database**: Hybrid search (BM25 + Dense vectors) with cross-encoder reranking
- **ReAct Agent**: Autonomous reasoning with 2 tools (Vector Database, Web Search)
- **Semantic Caching**: 90% faster responses on cache hits
- **Conversation Memory**: Context-aware multi-turn conversations
- **FastAPI Backend**: Async REST API
- **Modern Frontend**: Responsive UI with dark mode

## Architecture Flow

```
User Query
    ↓
[Conversational Check] → Greeting? Return instant response
    ↓
[Semantic Cache] → Cache Hit? Return in < 2s
    ↓ Cache Miss
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

### Installation

1. **Clone and setup**
```bash
git clone https://github.com/wassimameur6/givaudan.git
cd givaudan
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Start Weaviate**
```bash
docker run -d \
  --name weaviate-givaudan \
  -p 8090:8080 \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e DEFAULT_VECTORIZER_MODULE=none \
  semitechnologies/weaviate:1.27.1
```

4. **Start API**
```bash
python -m uvicorn api.main:app --reload --port 8001
```

5. **Open frontend**
```bash
cd frontend
python -m http.server 3000
# Visit: http://localhost:3000
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Vector DB | Weaviate 1.27.1 |
| Embeddings | BGE-large-en-v1.5 |
| LLM | GPT-4o-mini |
| Retrieval | Hybrid (BM25 + Dense) |
| Reranking | ms-marco-MiniLM-L-6-v2 |
| Agent | ReAct (LangChain) |
| Caching | SQLite + Embeddings |
| Web Search | SerpAPI |
| API | FastAPI |
| Frontend | Vanilla JS + CSS |

## API Usage

```bash
# Health check
curl http://localhost:8001/health

# Ask a question
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Où se trouvent les laboratoires Givaudan ?"}'
```

## Project Structure

```
givaudan/
├── api/                    # FastAPI backend
├── data/raw/               # Knowledge base documents
├── frontend/               # Web UI
├── src/                    # Core modules
│   ├── react_agent.py     # ReAct agent
│   ├── weaviate_rag_pipeline.py  # Hybrid search + reranking
│   ├── semantic_cache.py  # Semantic caching
│   ├── web_agent.py       # Web search
│   └── ...
├── scripts/                # Utility scripts
└── requirements.txt
```

## Configuration

Edit `src/config.py` or `.env`:

```python
LLM_MODEL = "gpt-4o-mini"
WEAVIATE_URL = "http://localhost:8090"
WEAVIATE_HYBRID_ALPHA = 0.6  # 60% dense, 40% BM25
AGENT_MAX_ITERATIONS = 5
CACHE_SIMILARITY_THRESHOLD = 0.88
```

## License

MIT
