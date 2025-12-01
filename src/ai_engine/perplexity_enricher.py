import requests
import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from config.settings import PERPLEXITY_API_KEY, CACHE_DIR
from src.utils.logging_config import setup_logging

logger = setup_logging(__name__)

def chat_completion(messages: List[Dict[str, str]], model: str = "sonar") -> Optional[str]:
    """
    Generic function to call Perplexity API for chat completions.
    
    Args:
        messages (List[Dict[str, str]]): List of message dicts with 'role' and 'content'.
        model (str): Model to use.
        
    Returns:
        Optional[str]: The content of the response, or None if failed.
    """
    if not PERPLEXITY_API_KEY:
        logger.warning("PERPLEXITY_API_KEY missing. Cannot perform chat completion.")
        return None
        
    url = "https://api.perplexity.ai/chat/completions"
    
    payload = {
        "model": model,
        "messages": messages
    }
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if not response.ok:
            logger.error(f"Perplexity API Error: {response.status_code} - {response.text}")
            
        response.raise_for_status()
        
        return response.json()['choices'][0]['message']['content']
        
    except Exception as e:
        logger.error(f"Perplexity API failed: {e}")
        return None

def research_company(company_name: str) -> Dict[str, Any]:
    """
    Research a company using Perplexity API to get recent news and values.
    
    Args:
        company_name (str): Name of the company.
        
    Returns:
        Dict[str, Any]: Research results.
    """
    if not company_name:
        return {}
        
    # Check cache (24h TTL handled by caller or simple file check)
    safe_name = "".join(c for c in company_name if c.isalnum())
    cache_file = CACHE_DIR / f"company_{safe_name}.json"
    
    if cache_file.exists():
        # Check if older than 24h
        if (time.time() - cache_file.stat().st_mtime) < 86400:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass

    messages = [
        {
            "role": "system",
            "content": "You are a helpful research assistant. Return a JSON object with keys: description, recent_news, values."
        },
        {
            "role": "user",
            "content": f"Research the company '{company_name}'. Provide a brief description, their core values, and any recent news or projects relevant to engineering/tech."
        }
    ]
    
    content = chat_completion(messages)
    
    if not content:
        return {}
        
    try:
        # Parse JSON from content (Perplexity might return markdown)
        # Simple cleanup
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        data = json.loads(content.strip())
        
        # Save to cache
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save company cache: {e}")
            
        return data
        
    except Exception as e:
        logger.error(f"Failed to parse Perplexity response: {e}")
        return {}
