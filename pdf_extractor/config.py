"""Configuration settings for the PDF extractor"""
import os
from dotenv import load_dotenv

load_dotenv()

# Thresholds for decision engine
T_HIGH = 0.85  # High confidence threshold - accept directly
T_LOW = 0.60   # Low confidence threshold - use mini-model/normalization

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = "gpt-5-mini"  # Supported model; JSON responses enabled via response_format

# Semantic search configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Lightweight model
TOP_K_CANDIDATES = 5  # Number of top candidates to consider per field

# Cache configuration
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".pdf_extractor_cache")

