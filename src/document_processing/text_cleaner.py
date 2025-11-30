import re
import unicodedata

def clean_text(text: str) -> str:
    """
    Clean and normalize text extracted from documents.
    
    Args:
        text (str): Raw text.
        
    Returns:
        str: Cleaned text.
    """
    if not text:
        return ""

    # Normalize unicode characters (e.g., decompose accents)
    text = unicodedata.normalize('NFKC', text)
    
    # Remove non-printable characters (except newlines and tabs)
    text = "".join(ch for ch in text if ch.isprintable() or ch in ['\n', '\t'])
    
    # Fix common PDF artifacts
    # Ligatures (fi, fl, etc.) are usually handled by NFKC, but explicit check:
    text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    
    # Remove multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Remove multiple newlines (more than 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove page numbers (simple heuristic: standalone numbers at start/end of lines)
    # This is risky without context, but common for footers
    # text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    
    return text.strip()
