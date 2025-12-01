import hashlib
import json
import logging
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_BATCH_SIZE

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingEngine, cls).__new__(cls)
        return cls._instance

    def _get_model(self):
        if self._model is None:
            logger.info("Loading SentenceTransformer model...")
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Model loaded.")
        return self._model

    def embed_cv(self, cv_text: str) -> Tuple[np.ndarray, str]:
        """Generate embedding for CV text with caching."""
        from src.data_management.database import get_cv_embedding, save_cv_embedding
        
        cv_hash = hashlib.sha256(cv_text.encode('utf-8')).hexdigest()
        
        # Check cache
        cached_emb = get_cv_embedding(cv_hash)
        if cached_emb is not None:
            return cached_emb, cv_hash
            
        # Generate
        model = self._get_model()
        embedding = model.encode(cv_text)
        
        # Save cache
        save_cv_embedding(cv_hash, embedding)
        
        return embedding, cv_hash

    def embed_projects_batch(self, projects: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
        """Generate embeddings for a batch of projects with caching."""
        from src.data_management.database import get_project_embeddings, save_project_embeddings
        
        project_embeddings = {}
        to_embed = []
        to_embed_ids = []
        to_embed_hashes = []
        
        # 1. Check Cache
        project_ids = [str(p.get('id', '')) for p in projects if p.get('id')]
        cached_map = get_project_embeddings(project_ids)
        
        for project in projects:
            pid = str(project.get('id', ''))
            if not pid:
                continue
                
            # Create a hash of the project content to detect changes
            content = f"{project.get('title', '')} {project.get('description', '')} {project.get('technologies', '')}"
            text_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # If cached and hash matches, use it
            # Note: Current DB schema stores text_hash but get_project_embeddings returns just embedding.
            # Ideally we should verify hash, but for now we assume ID uniqueness + immutable projects for this session.
            # To be robust, we'll assume if it exists it's good, or we could fetch hash too.
            # For this implementation, we'll trust the ID cache for speed.
            if pid in cached_map:
                project_embeddings[pid] = cached_map[pid]
            else:
                to_embed.append(content)
                to_embed_ids.append(pid)
                to_embed_hashes.append(text_hash)
        
        # 2. Generate missing embeddings
        if to_embed:
            logger.info(f"Generating embeddings for {len(to_embed)} new projects...")
            model = self._get_model()
            
            # Process in batches
            for i in range(0, len(to_embed), EMBEDDING_BATCH_SIZE):
                batch_texts = to_embed[i:i+EMBEDDING_BATCH_SIZE]
                batch_ids = to_embed_ids[i:i+EMBEDDING_BATCH_SIZE]
                batch_hashes = to_embed_hashes[i:i+EMBEDDING_BATCH_SIZE]
                
                embeddings = model.encode(batch_texts)
                
                # Update result and prepare for save
                save_map = {}
                for j, emb in enumerate(embeddings):
                    pid = batch_ids[j]
                    project_embeddings[pid] = emb
                    save_map[pid] = (emb, batch_hashes[j])
                
                # Save to DB
                save_project_embeddings(save_map)
                
        return project_embeddings

    def compute_similarities(self, cv_embedding: np.ndarray, project_embeddings: Dict[str, np.ndarray]) -> List[Tuple[str, float]]:
        """Compute cosine similarities between CV and projects."""
        scores = []
        for pid, p_emb in project_embeddings.items():
            # Cosine similarity
            similarity = np.dot(cv_embedding, p_emb) / (np.linalg.norm(cv_embedding) * np.linalg.norm(p_emb))
            scores.append((pid, float(similarity)))
        
        # Sort descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def prefilter_projects(self, cv_text: str, projects: List[Dict[str, Any]], top_k: int, min_threshold: float) -> List[Dict[str, Any]]:
        """Filter projects using embeddings."""
        try:
            cv_emb, _ = self.embed_cv(cv_text)
            proj_embs = self.embed_projects_batch(projects)
            
            scores = self.compute_similarities(cv_emb, proj_embs)
            
            # Filter and map back to project objects
            filtered_projects = []
            project_map = {str(p.get('id')): p for p in projects}
            
            for pid, score in scores:
                if score < min_threshold:
                    continue
                
                if pid in project_map:
                    project = project_map[pid]
                    project['similarity_score'] = score # Attach score for debugging/UI
                    filtered_projects.append(project)
                    
                if len(filtered_projects) >= top_k:
                    break
            
            return filtered_projects
            
        except Exception as e:
            logger.error(f"Embedding pre-filter failed: {e}")
            return projects # Fallback to all projects
