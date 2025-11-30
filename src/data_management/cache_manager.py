import json
import time
import logging
from typing import Any, Optional
from pathlib import Path
from config.settings import CACHE_DIR, CACHE_TTL_HOURS

logger = logging.getLogger(__name__)

def save_to_cache(key: str, data: Any):
    """Save data to JSON cache."""
    try:
        cache_file = CACHE_DIR / f"{key}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save to cache {key}: {e}")

def load_from_cache(key: str, ttl_hours: int = CACHE_TTL_HOURS) -> Optional[Any]:
    """Load data from JSON cache if not expired."""
    try:
        cache_file = CACHE_DIR / f"{key}.json"
        if not cache_file.exists():
            return None
            
        # Check TTL
        mtime = cache_file.stat().st_mtime
        if (time.time() - mtime) > (ttl_hours * 3600):
            return None
            
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load from cache {key}: {e}")
        return None

def clear_old_cache(days_old: int = 7):
    """Clear cache files older than X days."""
    try:
        now = time.time()
        cutoff = now - (days_old * 86400)
        
        count = 0
        for cache_file in CACHE_DIR.glob("*.json"):
            if cache_file.stat().st_mtime < cutoff:
                cache_file.unlink()
                count += 1
        
        logger.info(f"Cleared {count} old cache files.")
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
