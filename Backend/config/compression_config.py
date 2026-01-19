"""
═══════════════════════════════════════════════════════════════
 📉 Context Compression Configuration
═══════════════════════════════════════════════════════════════
"""

# Master Switch
ENABLE_COMPRESSION = True

# Provider Settings
# Options: 'ollama' (Local, Free) or 'openai' (Cloud, Paid)
COMPRESSION_PROVIDER = "ollama"

# Ollama Settings (Local)
OLLAMA_BASE_URL = "http://localhost:11434/api/generate"
# Common models: llama3, phi3, mistral, gemma
OLLAMA_MODEL = "llama3" 
OLLAMA_TIMEOUT = 30  # seconds

# OpenAI Settings (Fallback)
OPENAI_COMPRESSION_MODEL = "gpt-35-turbo"  # Cheaper model for compression

# Compression Parameters
MAX_CONTEXT_TOKENS = 6000     # Trigger compression if context exceeds this (chars approx)
TARGET_OUTPUT_TOKENS = 1000   # Aim for this size
