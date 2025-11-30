import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

import pdfplumber
import PyPDF2
import pytesseract
from pdf2image import convert_from_path

from src.utils.logging_config import setup_logging

logger = setup_logging(__name__)

def extract_text_from_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extract text from a PDF file using multiple methods with fallback.
    
    Args:
        file_path (str): Path to the PDF file.
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - text: The extracted text
            - method_used: The method that succeeded ('pdfplumber', 'pypdf2', 'ocr')
            - confidence: A confidence score (0.0-1.0)
            - page_count: Number of pages
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return {"text": "", "method_used": "error", "confidence": 0.0, "page_count": 0}

    # Method 1: pdfplumber (Best for text-based PDFs)
    try:
        logger.info(f"Attempting extraction with pdfplumber for {file_path.name}")
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            if len(text.strip()) > 50:  # heuristic: if we got meaningful text
                return {
                    "text": text,
                    "method_used": "pdfplumber",
                    "confidence": 0.9,
                    "page_count": len(pdf.pages)
                }
            logger.warning("pdfplumber extracted little to no text. Trying fallback.")
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    # Method 2: PyPDF2 (Fallback for text-based)
    try:
        logger.info(f"Attempting extraction with PyPDF2 for {file_path.name}")
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            if len(text.strip()) > 50:
                return {
                    "text": text,
                    "method_used": "pypdf2",
                    "confidence": 0.8,
                    "page_count": len(reader.pages)
                }
            logger.warning("PyPDF2 extracted little to no text. Trying OCR.")
    except Exception as e:
        logger.warning(f"PyPDF2 failed: {e}")

    # Method 3: OCR with pytesseract (For scanned PDFs)
    try:
        logger.info(f"Attempting OCR extraction for {file_path.name}")
        # Note: This requires poppler to be installed on the system
        images = convert_from_path(str(file_path))
        text = ""
        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            text += page_text + "\n"
        
        if len(text.strip()) > 0:
            return {
                "text": text,
                "method_used": "ocr",
                "confidence": 0.7,
                "page_count": len(images)
            }
    except Exception as e:
        logger.error(f"OCR failed: {e}")

    logger.error("All extraction methods failed.")
    return {"text": "", "method_used": "failed", "confidence": 0.0, "page_count": 0}
