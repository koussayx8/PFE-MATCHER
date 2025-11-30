import json
import time
import hashlib
from typing import List, Dict, Any
from pathlib import Path

from src.ai_engine.gemini_client import GeminiClient
from config.prompts import MATCHING_PROMPT
from config.settings import CACHE_DIR
from src.utils.logging_config import setup_logging
from src.analytics.comet_tracker import CometTracker

logger = setup_logging(__name__)
tracker = CometTracker()

def match_project_to_cv(cv_data: Dict[str, Any], project: Dict[str, Any]) -> Dict[str, Any]:
    """
    Match a single project to a CV using Gemini.
    
    Args:
        cv_data (Dict): CV data.
        project (Dict): Project data.
        
    Returns:
        Dict: Match analysis.
    """
    # Create a unique key for cache
    cv_str = json.dumps(cv_data, sort_keys=True)
    proj_str = json.dumps(project, sort_keys=True)
    match_hash = hashlib.md5((cv_str + proj_str).encode('utf-8')).hexdigest()
    
    cache_file = CACHE_DIR / f"match_{match_hash}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    client = GeminiClient()
    prompt = MATCHING_PROMPT.format(
        cv_data=json.dumps(cv_data, indent=2),
        project_data=json.dumps(project, indent=2)
    )
    
    result = client.generate_structured_response(prompt)
    
    if result:
        # Add metadata
        result["project_id"] = project.get("id")
        result["project_title"] = project.get("title")
        result["company"] = project.get("company")
        
        # Log to Comet
        tracker.log_match(project, result)
        
        # Save to cache
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save match cache: {e}")
            
        return result
    else:
        return {"overall_score": 0, "error": "Failed to generate match"}

def batch_match_projects(cv_data: Dict[str, Any], projects: List[Dict[str, Any]], min_score: int = 0) -> List[Dict[str, Any]]:
    """
    Match a CV against a list of projects.
    
    Args:
        cv_data (Dict): CV data.
        projects (List[Dict]): List of projects.
        min_score (int): Minimum score to include in results.
        
    Returns:
        List[Dict]: Sorted list of matches.
    """
    matches = []
    logger.info(f"Starting batch match for {len(projects)} projects...")
    
    for i, project in enumerate(projects):
        match_result = match_project_to_cv(cv_data, project)
        
        score = match_result.get("overall_score", 0)
        if score >= min_score:
            matches.append(match_result)
            
        # Rate limiting delay (if not cached)
        # We can't easily know if it was cached inside the function without modifying return
        # But GeminiClient handles 429s. We add a small delay to be safe if we are processing many.
        if (i + 1) % 10 == 0:
            time.sleep(2)
            
    # Sort by score descending
    matches.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    
    logger.info(f"Completed matching. Found {len(matches)} matches above score {min_score}.")
    return matches
