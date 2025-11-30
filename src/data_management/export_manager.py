import pandas as pd
import logging
from typing import List, Dict, Any
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from config.settings import EXPORTS_DIR

logger = logging.getLogger(__name__)

def export_to_csv(matches: List[Dict[str, Any]], filename: str = "matches.csv") -> str:
    """Export matches to CSV."""
    try:
        if not matches:
            return ""
            
        # Flatten data for CSV
        flat_data = []
        for m in matches:
            flat_data.append({
                "Project Title": m.get("project_title"),
                "Company": m.get("company"),
                "Score": m.get("overall_score"),
                "Recommendation": m.get("recommendation"),
                "Matching Points": ", ".join(m.get("matching_points", [])),
                "Gaps": ", ".join(m.get("gaps", []))
            })
            
        df = pd.DataFrame(flat_data)
        path = EXPORTS_DIR / filename
        df.to_csv(path, index=False, encoding='utf-8-sig')
        logger.info(f"Exported CSV to {path}")
        return str(path)
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        return ""

def generate_match_report_pdf(matches: List[Dict[str, Any]], cv_name: str, filename: str = "match_report.pdf") -> str:
    """Generate a PDF report of matches."""
    try:
        path = EXPORTS_DIR / filename
        doc = SimpleDocTemplate(str(path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        story.append(Paragraph(f"PFE Match Report for {cv_name}", styles['Title']))
        story.append(Spacer(1, 12))
        
        # Summary
        story.append(Paragraph(f"Total Matches Found: {len(matches)}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Table of Top Matches
        if matches:
            data = [["Project", "Company", "Score", "Recommendation"]]
            for m in matches[:20]: # Top 20
                data.append([
                    m.get("project_title", "")[:40] + "...",
                    m.get("company", "")[:20],
                    str(m.get("overall_score", 0)),
                    m.get("recommendation", "")
                ])
                
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
            
        doc.build(story)
        logger.info(f"Generated PDF report at {path}")
        return str(path)
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        return ""
