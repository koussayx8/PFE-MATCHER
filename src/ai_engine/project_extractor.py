import json
import hashlib
import uuid
import re
from difflib import SequenceMatcher
from typing import List, Dict, Any
from pathlib import Path

from src.ai_engine.gemini_client import GeminiClient
from config.prompts import PROJECT_EXTRACTION_PROMPT
from src.utils.logging_config import setup_logging
from src.data_management.database import get_cached_projects, save_cached_projects

logger = setup_logging(__name__)

def extract_projects_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract projects from text using Gemini.
    """
    if not text:
        return []

    # Check cache
    text_hash = hashlib.md5((text[:1000] + str(len(text))).encode('utf-8')).hexdigest()
    
    cached_projects = get_cached_projects(text_hash)
    if cached_projects:
        logger.info(f"Loaded projects from DB cache: {text_hash}")
        return cached_projects

    client = GeminiClient()
    
    # Chunking logic
    CHUNK_SIZE = 15000
    chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    
    logger.info(f"Split text into {len(chunks)} chunks for extraction.")
    
    all_projects = []
    
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
    
    # --- Global Context Scan (Full Text) ---
    # Scan the entire text for global application methods (Email/Link)
    
    # 1. Clean Text for OCR errors
    cleaned_text = clean_ocr_text(text)
    
    # 2. Find Global Email
    email_pattern = re.compile(r'(?:Email|Contact|mail)\s*[:\-]?\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', re.IGNORECASE)
    global_email_match = email_pattern.search(cleaned_text)
    global_email = global_email_match.group(1) if global_email_match else None
    
    # 3. Find Global Link
    global_link = None
    # Simple heuristic: Find URLs near "postuler"
    for match in re.finditer(r'(postuler|apply|candidature).{0,100}?(https?://[^\s<>"]+|www\.[^\s<>"]+)', cleaned_text, re.IGNORECASE | re.DOTALL):
        potential_link = match.group(2)
        potential_link = clean_ocr_url(potential_link)
        if "mobelite" in potential_link or "forms" in potential_link or "bit.ly" in potential_link:
            global_link = potential_link
            break
    
    if not global_link:
        mobelite_match = re.search(r'https?://sta[gq]es\.mobelite\.fr', cleaned_text, re.IGNORECASE)
        if mobelite_match:
            global_link = "https://stages.mobelite.fr"

    if global_email:
        logger.info(f"Found Global Email: {global_email}")
    if global_link:
        logger.info(f"Found Global Link: {global_link}")

    # Inject Global Context into Projects if missing
    for p in projects:
        if not p.get("application_link") and global_link:
            p["application_link"] = global_link
            p["application_method"] = "link"
            p["_note"] = "Inferred from global text scan"
            
        if not p.get("email") and global_email:
            p["email"] = global_email
            if not p.get("application_method"):
                p["application_method"] = "email"
        
    if projects:
        save_cached_projects(text_hash, projects)

    return projects

def normalize_projects(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize, deduplicate, and validate projects.
    """
    cleaned_projects = []
    seen_titles = []
    
    # Regex for finding URLs (case insensitive)
    url_pattern = re.compile(r'(https?://[^\s<>"]+|www\.[^\s<>"]+|bit\.ly/[^\s<>"]+|forms\.gle/[^\s<>"]+)', re.IGNORECASE)
    
    print(f"DEBUG: Input projects count: {len(projects)}")
    
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
import json
import hashlib
import uuid
import re
from difflib import SequenceMatcher
from typing import List, Dict, Any
from pathlib import Path

from src.ai_engine.gemini_client import GeminiClient
from config.prompts import PROJECT_EXTRACTION_PROMPT
from src.utils.logging_config import setup_logging
from src.data_management.database import get_cached_projects, save_cached_projects

logger = setup_logging(__name__)

def extract_projects_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract projects from text using Gemini.
    """
    if not text:
        return []

    # Check cache
    text_hash = hashlib.md5((text[:1000] + str(len(text))).encode('utf-8')).hexdigest()
    
    cached_projects = get_cached_projects(text_hash)
    if cached_projects:
        logger.info(f"Loaded projects from DB cache: {text_hash}")
        return cached_projects

    client = GeminiClient()
    
    # Chunking logic
    CHUNK_SIZE = 15000
    chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    
    logger.info(f"Split text into {len(chunks)} chunks for extraction.")
    
    all_projects = []
    
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
        
    if projects:
        save_cached_projects(text_hash, projects)

    return projects

def normalize_projects(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize, deduplicate, and validate projects.
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
    
    

    # Second Pass: Propagate Global Links
    all_links = [p.get("application_link") for p in cleaned_projects if p.get("application_link")]
    
    portal_link = None
    if all_links:
        # Find a link containing "stages" / "recrutement" / "careers" / "forms"
        for link in all_links:
            if any(k in link.lower() for k in ["stages", "recrutement", "forms", "career", "apply"]):
                portal_link = link
                break
    
    if portal_link:
        logger.info(f"Found global portal link: {portal_link}. Applying to missing projects.")
        for p in cleaned_projects:
            if not p.get("application_link") or p.get("application_link") == "":
                p["application_link"] = portal_link
                p["application_method"] = "link"
                p["_note"] = "Inferred from global context"

    logger.info(f"Normalized {len(projects)} projects to {len(cleaned_projects)} unique projects.")
    return cleaned_projects

def clean_ocr_text(text: str) -> str:
    """
    Clean common OCR errors in text, especially for emails.
    """
    if not text:
        return ""
    
    # Fix email artifacts
    text = text.replace("(ö", "@").replace("(at)", "@").replace("[at]", "@").replace(" at ", "@")
    text = text.replace(" .com", ".com").replace(" .fr", ".fr").replace(" .tn", ".tn")
    
    return text

def clean_ocr_url(url: str) -> str:
    """
    Clean common OCR errors in URLs.
    """
    if not url:
        return ""
        
    # Fix "staqes" -> "stages"
    url = url.replace("staqes", "stages")
    
    # Fix "htt ps" -> "https"
    url = url.replace("htt ps", "https").replace("http s", "https")
    
    return url
