import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any
import logging
from src.document_processing.pdf_parser import extract_text_from_pdf

logger = logging.getLogger(__name__)

def process_pdfs_parallel(file_paths: List[Path], max_workers: int = 5) -> List[Dict[str, Any]]:
    """
    Process multiple PDF files in parallel to extract text.
    
    Args:
        file_paths (List[Path]): List of paths to PDF files.
        max_workers (int): Maximum number of concurrent workers.
        
    Returns:
        List[Dict[str, Any]]: List of results from extract_text_from_pdf.
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a dictionary to map future to file path for error handling context
        future_to_path = {executor.submit(extract_text_from_pdf, path): path for path in file_paths}
        
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                data = future.result()
                # Add source filename to the result
                data["source_file"] = path.name
                results.append(data)
            except Exception as e:
                logger.error(f"Error processing {path.name}: {e}")
                results.append({
                    "text": "", 
                    "method_used": "error", 
                    "confidence": 0.0, 
                    "page_count": 0,
                    "source_file": path.name,
                    "error": str(e)
                })
                
    return results
