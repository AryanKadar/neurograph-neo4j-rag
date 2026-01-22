"""
═══════════════════════════════════════════════════════════════
  
   ██████╗ ██████╗ ███████╗███╗   ███╗██╗ ██████╗
  ██╔════╝██╔═══██╗██╔════╝████╗ ████║██║██╔════╝
  ██║     ██║   ██║███████╗██╔████╔██║██║██║     
  ██║     ██║   ██║╚════██║██║╚██╔╝██║██║██║     
  ╚██████╗╚██████╔╝███████║██║ ╚═╝ ██║██║╚██████╗
   ╚═════╝ ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝ ╚═════╝
  
          🚀 AI BACKEND - FastAPI Application
  
═══════════════════════════════════════════════════════════════
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from api.routes import health, documents, chat
from utils.logger import print_banner, print_section, print_success, print_info, setup_logger

logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    ┌─────────────────────────────────────────────┐
    │  🚀 Application Startup & Shutdown          │
    └─────────────────────────────────────────────┘
    """
    
    # ─────────────────────────────────────
    # Startup
    # ─────────────────────────────────────
    print_banner()
    
    print_section("INITIALIZING SERVICES")
    
    # Initialize vector store
    print_info("Loading Vector Store...")
    from services.vector_store import get_vector_store
    vs = get_vector_store()
    print_success(f"Vector Store ready ({vs.index.ntotal} vectors)")
    
    # Check Azure OpenAI connection
    print_info("Testing Azure OpenAI connection...")
    try:
        from services.embeddings import test_azure_connection
        is_connected = await test_azure_connection()
        if is_connected:
            print_success("Azure OpenAI connected")
        else:
            print_info("Azure OpenAI not configured (will fail on first request)")
    except Exception as e:
        print_info(f"Azure OpenAI test skipped: {e}")
    
    print_section("SERVER READY")
    print_success("🌟 Cosmic AI Backend is running!")
    print_info(f"📡 API: http://localhost:8000")
    print_info(f"📚 API Documentation: http://localhost:8000/docs")
    print_info(f"🔌 WebSocket Progress: ws://localhost:8000/api/ws/progress/{{file_id}}")
    print_info(f"🔧 CORS Origins: {settings.CORS_ORIGINS}")
    print("")
    print_success("✅ All systems operational - Ready to process documents!")
    print
    
    yield
    
    # ─────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────
    logger.info("\n🌙 Shutting down Cosmic AI...")


# ─────────────────────────────────────────────────────────────
#  🚀 Create FastAPI Application
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="🌌 Cosmic AI Backend",
    description="RAG-powered chatbot with document processing",
    version="1.0.0",
    lifespan=lifespan
)


# ─────────────────────────────────────────────────────────────
#  🔧 Configure CORS
# ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
#  📡 Register Routes
# ─────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(chat.router)


# ─────────────────────────────────────────────────────────────
#  🏠 Root Endpoint
# ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "service": "🌌 Cosmic AI Backend",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "azure_health": "/api/health/azure",
            "upload": "/api/upload",
            "chat": "/api/chat",
            "chat_stream": "/api/chat/stream"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
