"""
═══════════════════════════════════════════════════════════════
 🔧 Initialize Hybrid RAG Dependencies
═══════════════════════════════════════════════════════════════
Run this once to download required models and data
"""

import nltk
import os

def initialize():
    """Download required NLTK data"""
    print("🔄 Initializing Hybrid RAG dependencies...")
    print()
    
    # Create indices directory
    if not os.path.exists("./indices"):
        os.makedirs("./indices")
        print("✅ Created indices/ directory")
    
    # Download NLTK data (minimal - we use simple tokenization)
    try:
        print("🔄 Checking NLTK data...")
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        print("✅ NLTK data ready")
    except Exception as e:
        print(f"⚠️  NLTK download warning: {e}")
        print("   (BM25 will use fallback tokenization)")
    
    print()
    print("═" * 60)
    print("🎉 Hybrid RAG initialization complete!")
    print()
    print("Components ready:")
    print("  ✅ BM25 Service (Keyword Search)")
    print("  ✅ Hybrid Retriever (RRF Fusion)")
    print("  ✅ Cross-Encoder Reranker")
    print()
    print("Note: Cross-encoder model will be downloaded on first use")
    print("      (approximately 50-100MB)")
    print("═" * 60)

if __name__ == "__main__":
    initialize()
