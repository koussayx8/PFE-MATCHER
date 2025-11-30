import json
from typing import Dict, Any
from src.ai_engine.gemini_client import GeminiClient
from src.ai_engine.perplexity_enricher import research_company
from config.prompts import EMAIL_GENERATION_PROMPT
from src.utils.logging_config import setup_logging

logger = setup_logging(__name__)

def generate_email(
    cv_data: Dict[str, Any], 
    project: Dict[str, Any], 
    match_data: Dict[str, Any], 
    tone: str = "Formal", 
    language: str = "English"
) -> Dict[str, str]:
    """
    Generate a personalized application email.
    
    Args:
        cv_data: CV data.
        project: Project data.
        match_data: Match analysis data.
        tone: Desired tone.
        language: Desired language.
        
    Returns:
        Dict: {subject, body}
    """
    
    # 1. Enrich with company research (optional but recommended)
    company_name = project.get("company", "")
    company_research = {}
    if company_name:
        logger.info(f"Researching company: {company_name}")
        company_research = research_company(company_name)
    
    # 2. Prepare context
    student_name = cv_data.get("personal_info", {}).get("name", "Student")
    project_title = project.get("title", "")
    
    # 3. Construct prompt
    prompt = EMAIL_GENERATION_PROMPT.format(
        student_name=student_name,
        project_title=project_title,
        company_name=company_name,
        tone=tone,
        language=language,
        match_data=json.dumps(match_data, indent=2),
        company_research=json.dumps(company_research, indent=2)
    )
    
    # 4. Call Gemini
    client = GeminiClient()
    logger.info("Generating email...")
    result = client.generate_structured_response(prompt)
    
    if result:
        return result
    else:
        # Fallback template if AI fails
        return {
            "subject": f"Application for PFE: {project_title}",
            "body": f"Dear Hiring Manager,\n\nI am writing to express my interest in the {project_title} project at {company_name}.\n\nSincerely,\n{student_name}"
        }

def preview_email_html(email_data: Dict[str, str]) -> str:
    """
    Format email for preview in Streamlit.
    """
    subject = email_data.get("subject", "")
    body = email_data.get("body", "").replace("\n", "<br>")
    
    return f"""
    <div style="border:1px solid #ddd; padding:20px; border-radius:10px; background-color:#f9f9f9; color:#000000;">
        <p><strong>Subject:</strong> {subject}</p>
        <hr>
        <div style="font-family:sans-serif;">{body}</div>
    </div>
    """
