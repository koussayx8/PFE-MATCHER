import json
import time
import hashlib
from typing import List, Dict, Any
from pathlib import Path

from src.ai_engine.gemini_client import GeminiClient
from src.ai_engine.embeddings import EmbeddingEngine
from config.prompts import MATCHING_PROMPT
from config.settings import (
    USE_HYBRID_MATCHING, EMBEDDING_TOP_K, MIN_SIMILARITY_THRESHOLD
)
from src.data_management.database import get_cached_match, save_cached_match
from src.utils.logging_config import setup_logging
from src.analytics.comet_tracker import CometTracker

logger = setup_logging(__name__)
tracker = CometTracker()

def match_project_to_cv(cv_data: Dict[str, Any], project: Dict[str, Any], cv_hash: str = None) -> Dict[str, Any]:
    """
    Match a single project to a CV using Gemini, with DB caching.
    """
    # Create hash if not provided
    if not cv_hash:
        cv_str = json.dumps(cv_data, sort_keys=True)
        cv_hash = hashlib.sha256(cv_str.encode('utf-8')).hexdigest()
        
    project_id = str(project.get("id", ""))
    
    # 1. Check DB Cache
    cached_result = get_cached_match(cv_hash, project_id)
    if cached_result:
        # logger.info(f"Match cache hit for {project_id}") # Too verbose
        cached_result["was_cached"] = True
        return cached_result

    # 2. Call Gemini
    client = GeminiClient()
    prompt = MATCHING_PROMPT.format(
        cv_data=json.dumps(cv_data, indent=2),
        project_data=json.dumps(project, indent=2)
    )
    
    result = None
    used_fallback = False
    
    try:
        result = client.generate_structured_response(prompt)
    except Exception as e:
        logger.warning(f"Gemini API failed for project {project_id}: {e}. Attempting fallback...")
        
    # Fallback to Perplexity if Gemini failed
    if not result:
        try:
            from src.ai_engine.perplexity_enricher import chat_completion
            logger.info(f"Falling back to Perplexity for project {project_id}")
            
            messages = [
                {"role": "system", "content": "You are an expert HR AI. Analyze the match between a CV and a Project. Return ONLY a JSON object with keys: overall_score (0-100), matching_points (list), gaps (list), recommendation (string)."},
                {"role": "user", "content": prompt}
            ]
            
            fallback_content = chat_completion(messages, model="sonar-reasoning")
            if fallback_content:
                # Clean up markdown if present
                if "```json" in fallback_content:
                    fallback_content = fallback_content.split("```json")[1].split("```")[0]
                elif "```" in fallback_content:
                    fallback_content = fallback_content.split("```")[1].split("```")[0]
                    
                result = json.loads(fallback_content.strip())
                used_fallback = True
        except Exception as e:
            logger.error(f"Perplexity fallback also failed: {e}")
    
    if result:
        # Add metadata
        result["project_id"] = project.get("id")
        result["project_title"] = project.get("title")
        result["company"] = project.get("company")
        result["reference_id"] = project.get("reference_id", "")
        result["email"] = project.get("email", "")
        result["application_method"] = project.get("application_method", "")
        result["application_link"] = project.get("application_link", "")
        result["was_cached"] = False
        result["source"] = "perplexity" if used_fallback else "gemini"
        
        # Log to Comet
        tracker.log_match(project, result)
        
        # Save to DB Cache
        save_cached_match(cv_hash, project_id, result)
            
        return result
    else:
        return {
            "overall_score": 0, 
            "error": "Failed to generate match (Both Gemini and Fallback failed)", 
            "was_cached": False,
            "project_id": project.get("id"),
            "project_title": project.get("title"),
            "company": project.get("company")
        }

def batch_match_projects(cv_data: Dict[str, Any], projects: List[Dict[str, Any]], min_score: int = 0) -> List[Dict[str, Any]]:
    """
    Hybrid matching flow:
    1. Pre-filter using Embeddings (if enabled)
    2. Detailed scoring using Gemini (with caching)
    """
    start_time = time.time()
    
    # Generate CV Hash for caching
    cv_str = json.dumps(cv_data, sort_keys=True)
    cv_hash = hashlib.sha256(cv_str.encode('utf-8')).hexdigest()
    
    # 1. Pre-filtering (Hybrid Mode)
    candidates = projects
    if USE_HYBRID_MATCHING:
        logger.info(f"Hybrid Matching Enabled. Pre-filtering {len(projects)} projects...")
        
        # Construct CV text for embedding (richer representation)
        cv_text = f"{cv_data.get('skills', '')} {cv_data.get('experience', '')} {cv_data.get('education', '')}"
        
        engine = EmbeddingEngine()
        candidates = engine.prefilter_projects(
            cv_text, 
            projects, 
            top_k=EMBEDDING_TOP_K, 
            min_threshold=MIN_SIMILARITY_THRESHOLD
        )
        logger.info(f"Pre-filtering complete. Selected {len(candidates)} candidates from {len(projects)} projects.")
    
    # 2. Detailed Matching
    matches = []
    api_calls = 0
    cache_hits = 0
    
    logger.info(f"Starting detailed matching for {len(candidates)} candidates...")
    
    for i, project in enumerate(candidates):
        match_result = match_project_to_cv(cv_data, project, cv_hash)
        
        if match_result.get("was_cached"):
            cache_hits += 1
        else:
            api_calls += 1
            # Rate limiting only for actual API calls
            if api_calls % 10 == 0:
                time.sleep(2)
        
        score = match_result.get("overall_score", 0)
        score = match_result.get("overall_score", 0)
        if score >= min_score or "error" in match_result:
            matches.append(match_result)
            
    # Sort by score descending
    matches.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    
    elapsed = time.time() - start_time
    logger.info(f"Matching completed in {elapsed:.2f}s. API Calls: {api_calls}, Cache Hits: {cache_hits}. Found {len(matches)} matches.")
    
    # Attach metrics to the first match for UI display (hacky but effective for now)
    if matches:
        matches[0]["_metrics"] = {
            "total_projects": len(projects),
            "candidates": len(candidates),
            "api_calls": api_calls,
            "cache_hits": cache_hits,
            "elapsed": elapsed
        }
        
    return matches
