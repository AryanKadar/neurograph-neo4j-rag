"""
═══════════════════════════════════════════════════════════════
 🌌 COSMIC AI - Configuration Settings
═══════════════════════════════════════════════════════════════
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # ─────────────────────────────────────────────────────────
    #  🔐 Azure OpenAI Configuration
    # ─────────────────────────────────────────────────────────
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_API_BASE: str = os.getenv("AZURE_OPENAI_API_BASE", "")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-chat")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
    
    # ─────────────────────────────────────────────────────────
    #  🤖 GPT-5 Model Configuration
    # ─────────────────────────────────────────────────────────
    GPT_MAX_COMPLETION_TOKENS: int = int(os.getenv("GPT_MAX_COMPLETION_TOKENS", "4000"))
    GPT_MAX_CONTEXT_TOKENS: int = int(os.getenv("GPT_MAX_CONTEXT_TOKENS", "120000"))
    GPT_RESERVED_TOKENS: int = int(os.getenv("GPT_RESERVED_TOKENS", "2000"))
    
    # Temperature & Creativity Settings
    GPT_TEMPERATURE: float = float(os.getenv("GPT_TEMPERATURE", "0.7"))
    GPT_TOP_P: float = float(os.getenv("GPT_TOP_P", "0.95"))
    GPT_FREQUENCY_PENALTY: float = float(os.getenv("GPT_FREQUENCY_PENALTY", "0.0"))
    GPT_PRESENCE_PENALTY: float = float(os.getenv("GPT_PRESENCE_PENALTY", "0.0"))
    
    # Response Settings
    GPT_STREAM_ENABLED: bool = os.getenv("GPT_STREAM_ENABLED", "true").lower() == "true"
    GPT_STREAMING_CHUNK_SIZE: int = int(os.getenv("GPT_STREAMING_CHUNK_SIZE", "5"))
    
    # ─────────────────────────────────────────────────────────
    #  📁 File Storage Configuration
    # ─────────────────────────────────────────────────────────
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    VECTOR_DB_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vector_db")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "25"))
    MAX_FILES_PER_UPLOAD: int = int(os.getenv("MAX_FILES_PER_UPLOAD", "5"))
    ALLOWED_FILE_TYPES: str = os.getenv("ALLOWED_FILE_TYPES", "pdf,docx,txt,md")
    
    @property
    def MAX_FILE_SIZE(self) -> int:
        """Convert MB to bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def ALLOWED_FILE_TYPES_LIST(self) -> List[str]:
        """Parse allowed file types from comma-separated string"""
        return [ft.strip() for ft in self.ALLOWED_FILE_TYPES.split(",")]

    
    # ─────────────────────────────────────────────────────────
    #  🖼️ Multimodal Configuration
    # ─────────────────────────────────────────────────────────
    ENABLE_MULTIMODAL: bool = os.getenv("ENABLE_MULTIMODAL", "true").lower() == "true"
    OLLAMA_VISION_MODEL: str = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")

    # ─────────────────────────────────────────────────────────
    #  🧠 RAG Configuration
    # ─────────────────────────────────────────────────────────
    # Chunking Settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    MIN_CHUNK_SIZE: int = int(os.getenv("MIN_CHUNK_SIZE", "100"))
    
    # Retrieval Settings
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
    MAX_CONTEXT_CHUNKS: int = int(os.getenv("MAX_CONTEXT_CHUNKS", "8"))
    
    # Chunking Strategy
    CHUNKING_STRATEGY: str = os.getenv("CHUNKING_STRATEGY", "recursive").lower()
    AGENTIC_WINDOW_SIZE: int = int(os.getenv("AGENTIC_WINDOW_SIZE", "20"))
    
    # ─────────────────────────────────────────────────────────
    #  🔍 HNSW Configuration
    # ─────────────────────────────────────────────────────────
    HNSW_M: int = int(os.getenv("HNSW_M", "32"))
    HNSW_EF_CONSTRUCTION: int = int(os.getenv("HNSW_EF_CONSTRUCTION", "200"))
    HNSW_EF_SEARCH: int = int(os.getenv("HNSW_EF_SEARCH", "100"))
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    
    # ─────────────────────────────────────────────────────────
    #  🌐 Server Configuration
    # ─────────────────────────────────────────────────────────
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    CORS_ORIGINS_STR: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",")]

    
    # ─────────────────────────────────────────────────────────
    #  📊 Logging & Monitoring
    # ─────────────────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_DEBUG_LOGGING: bool = os.getenv("ENABLE_DEBUG_LOGGING", "false").lower() == "true"
    LOG_API_CALLS: bool = os.getenv("LOG_API_CALLS", "true").lower() == "true"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = Settings()

# Create directories if they don't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)

