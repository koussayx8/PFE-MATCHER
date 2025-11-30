import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Any
from src.utils.logging_config import setup_logging

logger = setup_logging(__name__)

def parse_excel_to_projects(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse an Excel file into a list of standardized project dictionaries.
    
    Args:
        file_path (str): Path to the Excel file.
        
    Returns:
        List[Dict[str, Any]]: List of project dictionaries.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return []

    try:
        # Read Excel file
        # engine='openpyxl' for xlsx, default for others
        df = pd.read_excel(file_path)
        
        # Normalize column names
        df.columns = [str(col).lower().strip() for col in df.columns]
        
        # Define column mappings
        column_mappings = {
            "title": ["titre", "title", "projet", "sujet", "project title"],
            "description": ["description", "details", "résumé", "summary", "context"],
            "company": ["entreprise", "company", "société", "organization", "organisme"],
            "email": ["email", "contact", "mail", "address", "coordonnées"],
            "technologies": ["technologies", "tech stack", "outils", "tools", "mots clés", "keywords"],
            "location": ["lieu", "location", "ville", "city", "pays"]
        }
        
        # Map columns
        mapped_columns = {}
        for target, aliases in column_mappings.items():
            for alias in aliases:
                matches = [col for col in df.columns if alias in col]
                if matches:
                    mapped_columns[target] = matches[0] # Take first match
                    break
        
        if "title" not in mapped_columns:
            logger.error("Could not find a 'title' column in the Excel file.")
            return []

        projects = []
        for _, row in df.iterrows():
            # Skip empty rows (based on title)
            if pd.isna(row[mapped_columns["title"]]):
                continue
                
            project = {}
            for target, source_col in mapped_columns.items():
                val = row[source_col]
                project[target] = str(val).strip() if pd.notna(val) else ""
            
            # Add raw data for other columns
            # (Optional: could add all other columns to a 'metadata' field)
            
            projects.append(project)
            
        logger.info(f"Extracted {len(projects)} projects from {file_path.name}")
        return projects

    except Exception as e:
        logger.error(f"Failed to parse Excel file: {e}")
        return []
