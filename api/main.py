"""FastAPI Backend for Givaudan RAG System"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
import time
from datetime import datetime

from src.react_agent import ReActAgent
from src.utils import logger

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[ChatMessage]] = []
    thread_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    answer: str
    metadata: Dict
    chat_history: List[ChatMessage]
    processing_time: float

class SystemInfo(BaseModel):
    name: str
    description: str
    speed: str
    cost: str
    quality: str
    features: List[str]

react_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global react_agent

    # Startup
    logger.info(" Initializing Givaudan RAG API...")
    try:
        logger.info("Loading ReAct Agent (Weaviate + Hybrid Search)...")
        react_agent = ReActAgent()
        react_agent.setup_rag()
        logger.info(" ReAct Agent ready!")
    except Exception as e:
        logger.error(f" Initialization error: {e}")
        raise

    yield

    # Shutdown (cleanup if needed)
    logger.info("Shutting down...")

app = FastAPI(
    title="Givaudan RAG API",
    description="RAG system with Weaviate, Hybrid Search, and ReAct Agent",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Givaudan RAG API",
        "version": "2.0.0",
        "system": "ReAct Agent (Weaviate + Hybrid Search)",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if react_agent is not None else "unavailable",
        "timestamp": datetime.now().isoformat(),
        "react_agent_ready": react_agent is not None
    }

@app.get("/system", response_model=SystemInfo)
async def get_system_info():
    return SystemInfo(
        name="react_agent",
        description="ReAct Agent with Weaviate, Hybrid Search",
        speed=" < 2s (cached) / 10-15s (uncached)",
        cost=" Low cost (gpt-4o-mini + semantic caching)",
        quality=" Excellent",
        features=[
            "Weaviate vector database",
            "Hybrid Search (BM25 30% + Dense 70%)",
            "Cross-encoder reranking (ms-marco-MiniLM)",
            "ReAct pattern with 2 tools (VectorDB, Web)",
            "Semantic caching (0.88 threshold)",
            "Conversation memory (last 6 messages)",
            "Web search fallback (SerpAPI)"
        ]
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    start_time = time.time()

    try:
        if not react_agent:
            raise HTTPException(status_code=503, detail="ReAct Agent not initialized")

        # Convert chat history
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.chat_history
        ] if request.chat_history else []

        # Use async version with caching support (pass chat_history!)
        result = await react_agent.ask_async(
            question=request.question,
            chat_history=chat_history
        )

        metadata = {
            "cache_hit": result.get("cache_hit", False),
            "processing_time": result.get("processing_time", 0),
            "model_used": result.get("model_used", "gpt-4o-mini"),
            "question": request.question
        }
        answer = result.get("answer", "")

        # Calculate total processing time
        processing_time = time.time() - start_time

        # Add to chat history
        updated_history = chat_history + [
            {"role": "user", "content": request.question, "timestamp": datetime.now().isoformat()},
            {"role": "assistant", "content": answer, "timestamp": datetime.now().isoformat()}
        ]

        return ChatResponse(
            answer=answer,
            metadata=metadata,
            chat_history=[
                ChatMessage(role=msg["role"], content=msg["content"], timestamp=msg.get("timestamp"))
                for msg in updated_history
            ],
            processing_time=processing_time
        )

    except Exception as e:
        logger.error(f"Error in /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
