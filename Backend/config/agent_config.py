"""
═══════════════════════════════════════════════════════════════
 🤖 Agent Configuration
═══════════════════════════════════════════════════════════════
"""

# Master Switch
ENABLE_AGENTIC_RAG = True

# Agent Settings
MAX_LOOPS = 3                # Maximum number of search iterations
AGENT_MODEL = "gpt-5-chat"  # Deployment name for the agent
ENABLE_VERBOSE_LOGGING = True

# Trigger Conditions
# If query length > X or contains "compare", "research", "deep", trigger agent?
# For now, we might trigger manually or via a keyword classifier.
AUTO_TRIGGER_KEYWORDS = ["compare", "difference", "research", "deep dive", "comprehensive", "history"]
