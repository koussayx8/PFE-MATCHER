import json
import hashlib
import uuid
from difflib import SequenceMatcher
from typing import List, Dict, Any
from pathlib import Path

from src.ai_engine.gemini_client import GeminiClient
from config.prompts import PROJECT_EXTRACTION_PROMPT
from config.prompts import PROJECT_EXTRACTION_PROMPT
from src.utils.logging_config import setup_logging
from src.data_management.database import get_cached_projects, save_cached_projects

logger = setup_logging(__name__)

def extract_projects_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract projects from text using Gemini.
    
    Args:
        text (str): The raw text from the PFE book.
        
    Returns:
        List[Dict[str, Any]]: List of extracted projects.
    """
    if not text:
        return []

    # Check cache (hash of the first 1000 chars + length to avoid huge hash calc on full text if unnecessary)
    text_hash = hashlib.md5((text[:1000] + str(len(text))).encode('utf-8')).hexdigest()
    
    cached_projects = get_cached_projects(text_hash)
    if cached_projects:
        logger.info(f"Loaded projects from DB cache: {text_hash}")
        return cached_projects

    client = GeminiClient()
    
    # Chunking logic to avoid timeouts
    CHUNK_SIZE = 15000
    chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    
    logger.info(f"Split text into {len(chunks)} chunks for extraction.")
    
    all_projects = []
    
    # Process chunks
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
        prompt = PROJECT_EXTRACTION_PROMPT.format(text=chunk)
        
        result = client.generate_structured_response(prompt)
        
        if result and "projects" in result:
            chunk_projects = result["projects"]
            logger.info(f"Found {len(chunk_projects)} projects in chunk {i+1}")
            all_projects.extend(chunk_projects)
        else:
            logger.warning(f"Failed to extract projects from chunk {i+1}")
            
    projects = all_projects
        
    # Save to cache
    if projects:
        save_cached_projects(text_hash, projects)

    return projects

import re

def normalize_projects(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize, deduplicate, and validate projects.
    
    Args:
        projects (List[Dict[str, Any]]): Raw projects list.
        
    Returns:
        List[Dict[str, Any]]: Cleaned list.
    """
    cleaned_projects = []
    seen_titles = []
    
    # Regex for finding URLs (case insensitive)
    url_pattern = re.compile(r'(https?://[^\s<>"]+|www\.[^\s<>"]+|bit\.ly/[^\s<>"]+|forms\.gle/[^\s<>"]+)', re.IGNORECASE)
    
    for p in projects:
        # Basic validation
        if not p.get("title") or not p.get("description"):
            continue
            
        # Clean fields
        p["title"] = p["title"].strip()
        p["description"] = p["description"].strip()
        
        # Regex Fallback for Link
        if not p.get("application_link"):
            # Search in description
            match = url_pattern.search(p["description"])
            if match:
                p["application_link"] = match.group(0)
                p["application_method"] = "link"
                logger.info(f"Regex found link for {p['title']}: {p['application_link']}")
        
        if p.get("application_link"):
            p["application_link"] = p["application_link"].strip()
            
        if p.get("reference_id"):
            p["reference_id"] = p["reference_id"].strip()
            
        p["id"] = str(uuid.uuid4())
        
        # Deduplication
        is_duplicate = False
        for seen_title in seen_titles:
            similarity = SequenceMatcher(None, p["title"].lower(), seen_title.lower()).ratio()
            if similarity > 0.85:
                is_duplicate = True
                break
        
        if not is_duplicate:
            cleaned_projects.append(p)
            seen_titles.append(p["title"])
            
    logger.info(f"Normalized {len(projects)} projects to {len(cleaned_projects)} unique projects.")
    return cleaned_projects
