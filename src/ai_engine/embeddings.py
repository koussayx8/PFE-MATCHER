import logging
import hashlib
import json
import pickle
from typing import List, Dict, Any
from pathlib import Path
from config.settings import CACHE_DIR, EMBEDDING_MODEL_NAME
from src.utils.logging_config import setup_logging

logger = setup_logging(__name__)

class EmbeddingEngine:
    def __init__(self):
        self.model = None
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except ImportError:
            logger.warning("sentence-transformers not installed. Embeddings fallback unavailable.")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")

    def generate_embeddings(self, texts: List[str]) -> Any:
        """
        Generate embeddings for a list of texts.
        """
        if not self.model:
            return None
            
        # Check cache (simple hash of all texts joined)
        # For large lists, this might be inefficient, but okay for now.
        # Better: cache per text.
        
        return self.model.encode(texts, convert_to_tensor=True)

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts.
        Returns score 0-100.
        """
        if not self.model:
            return 0.0
            
        try:
            from sentence_transformers import util
            emb1 = self.model.encode(text1, convert_to_tensor=True)
            emb2 = self.model.encode(text2, convert_to_tensor=True)
            
            score = util.cos_sim(emb1, emb2).item()
            return score * 100
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
