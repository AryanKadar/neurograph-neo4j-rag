"""
═══════════════════════════════════════════════════════════════
 🧠 Query Transformation Configuration
═══════════════════════════════════════════════════════════════
"""

# HyDE Settings
ENABLE_HYDE = True
HYDE_MODEL = "gpt-5-chat"        # Deployment name for Azure OpenAI
HYDE_TEMPERATURE = 0.7           # Higher creativity for hallucinating answers
HYDE_MAX_TOKENS = 500            # Limit hypothetical document length

# Query Analysis Settings
ENABLE_QUERY_ANALYSIS = True
ANALYSIS_MODEL = "gpt-5-chat"
ANALYSIS_TEMPERATURE = 0.1       # Low temperature for classification

# Adaptive Search Weight Profiles
# Weights must sum to ~1.0 ideally, but normalization handles it
WEIGHT_PROFILES = {
    'factual': {
        'vector': 0.30, 
        'bm25': 0.50, 
        'graph': 0.20,
        'description': 'Fact lookup/Specific Entity'
    },
    'conceptual': {
        'vector': 0.60, 
        'bm25': 0.20, 
        'graph': 0.20,
        'description': 'Abstract concept/Explanation'
    },
    'relational': {
        'vector': 0.20, 
        'bm25': 0.20, 
        'graph': 0.60,
        'description': 'Relationship/Connection query'
    },
    'code_error': {
        'vector': 0.10, 
        'bm25': 0.80, 
        'graph': 0.10,
        'description': 'Error code/Log snippet'
    },
    'balanced': {
        'vector': 0.35, 
        'bm25': 0.35, 
        'graph': 0.30,
        'description': 'General/Unclassified query'
    }
}
