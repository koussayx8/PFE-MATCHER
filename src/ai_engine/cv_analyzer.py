import json
import hashlib
from pathlib import Path
from typing import Dict, Any
from src.ai_engine.gemini_client import GeminiClient
from config.prompts import CV_ANALYSIS_PROMPT
from config.settings import CACHE_DIR
from src.utils.logging_config import setup_logging

logger = setup_logging(__name__)

def analyze_cv(cv_text: str) -> Dict[str, Any]:
    """
    Analyze CV text using Gemini to extract structured information.
    
    Args:
        cv_text (str): The raw text of the CV.
        
    Returns:
        Dict[str, Any]: Structured CV data.
    """
    if not cv_text:
        return {}

    # Check cache
    cv_hash = hashlib.md5(cv_text.encode('utf-8')).hexdigest()
    cache_file = CACHE_DIR / f"cv_{cv_hash}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                logger.info(f"Loaded CV analysis from cache: {cv_hash}")
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

    # Call Gemini
    client = GeminiClient()
    prompt = CV_ANALYSIS_PROMPT.format(cv_text=cv_text[:30000]) # Truncate if too long
    
    logger.info("Sending CV to Gemini for analysis...")
    result = client.generate_structured_response(prompt)
    
    if result:
        # Save to cache
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
            
        return result
    else:
        logger.error("Failed to analyze CV.")
        return {}
